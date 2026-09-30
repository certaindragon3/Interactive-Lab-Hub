#!/usr/bin/env python3
"""GPT-Live PCM transport with application-owned food tools and a drained ending."""
import argparse
import asyncio
import base64
import json
import errno
import os
import signal
import sys
import time
from pathlib import Path
from uuid import uuid4

from food_coach import BACKEND_PROMPT, TOOLS, Ledger, atomic_json
from coach_backend import Backend, TranscriptSync
from coach_language import localize_recap
from coach_cues import ProcessingCue, processing_tone
from coach_runtime import Metrics, PCMOutput, SerialWorker, StatusWriter, off_thread

LAB_DIR = Path(__file__).resolve().parent.parent
PROMPT = """LANGUAGE RULE (takes precedence over the language of these instructions and examples): Always speak English, from the very first response through praise, roasts, questions and the goodbye. The conversation language is fixed to English for every check-in. Understand user input in other languages, but do not switch your output language, even when the first utterance is not English. Translate the character/style guidance below into English; Chinese examples do NOT prescribe Chinese output.
你是 Orange，用户请来的毒舌饮食教练。像一个嘴很损、站在用户这边、有强烈个人态度的真人。你不是客服，不是记账员，更不是每句都端水的营养播音员。
你的两面都要鲜明：supportive 和 judgemental。用户报出值得肯定的选择时，真诚、具体、有劲地夸；主动补充或纠正记录、愿意如实说完菜单时，也认可他的坦诚。别每句后面都转成批评。遇到蛋糕、炸鸡这种喜剧情节时，态度骤变，反讽要狠、具体、出其不意，不用“偶尔吃一点也没关系”马上把包袱收回。
吐槽的是这次菜单如何发展，不是人的身体、体重、长相、人格或价值；不要羞辱人，不鼓励挨饿、补偿性运动、极端节食。吃了某种食物不等于这个人失败。用户真在沮丧时先接住情绪；要求温柔或停下时立即照做。
你会记住前面说过什么，让整段对话发展，而不是每报一道菜就重启一次点评。可以先夸西兰花，蛋糕来了语气一拐，再来炸鸡就用前面的西兰花做回扣。节奏、停顿、难以置信的短反问都是你的表演，不靠长篇说教。
语气参考，不照抄：夸奖可以是“这口西兰花可以，今天这张菜单终于有个认真上班的。”；蛋糕加炸鸡可以是“好家伙，西兰花刚来上班，你就给它安排了两位拆台的领导。”要写比固定模板更贴合当场的回应。每轮选择一种明确态度，不机械地先夸再骂再鼓励。
先接人的话，不要说“收到”“已记录”“已更正”“我记一下”，不复读整句话，不给每道菜盖口头收据。通常一两句，把话头交还；追问要有动机，不要每轮问“还有吗”。份量问题穿插在对话中，一次问一个，已经答过的不再问。用户说蛋糕，可挑眉问“多大块？一口解馋还是给它办了个登基大典？”但绝不替他猜份量。
这是菜单游戏，不是营养或热量评估。数字只能来自后端，日常不念分数、不报工作进度。后端处理时你可以自然回应或开玩笑，不用沉默等待；但没成功前不能声称已保存。结束按钮的短总结由应用负责。
Backchannel policy: 听清用户在说什么。只在自然处短促应声，别固定嗯嗯，更别抢走没说完的话。
Interruption policy: 用户插话就停，关注他新加的食物或更正，把它变成下一句的素材；不要从头重念上一句。让用户完成更正，再继续包袱。
Delegation policy: 应用会在用户语音停顿后主动安排后端更新食物记录，你专心与用户对话，无需为每道菜主动委派或口头宣告工具流程。后端结果是事实依据，不是让你朗读的台词。用户查询或纠正但尚无后端结果时可以委派核实。闲聊、假设、你的玩笑都不要当成实际吃过的食物。"""


def load_key():
    if os.environ.get("OPENAI_API_KEY"):
        return
    env_path = Path(os.environ.get("COACH_ENV_FILE", LAB_DIR / ".env"))
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENAI_API_KEY="):
                value = line.partition("=")[2].strip().strip('"').strip("'")
                if value:
                    os.environ["OPENAI_API_KEY"] = value
                break
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY in the Lab environment")


def close_pcm_output():
    # CPython's standard stream may own a wrapper with closefd=False.
    fd = sys.stdout.fileno()
    sys.stdout.close()
    try:
        os.close(fd)
    except OSError as exc:
        if exc.errno != errno.EBADF:
            raise


async def run(args):
    metrics = Metrics()
    screen = StatusWriter(args.status, metrics)
    audio = PCMOutput(sys.stdout.buffer, metrics)
    try:
        await run_session(args, metrics, screen, audio)
    finally:
        try:
            await audio.worker.stop()
        finally:
            await screen.close()


async def run_session(args, metrics, screen, pcm_output):
    from openai import AsyncOpenAI
    load_key()
    ledger = Ledger(args.record)
    loop = asyncio.get_running_loop()
    chunks = asyncio.Queue(maxsize=20)
    closed = asyncio.Event()
    ready = asyncio.Event()
    finish_requested = asyncio.Event()
    stopping = False
    ending = False
    reader_added = False
    pending_byte = b""
    language = "en"
    ledger.data["language"] = language
    ledger.save()
    backend_model = os.environ.get("COACH_BACKEND_MODEL", "gpt-5.6-luna")
    last_input = time.monotonic()
    input_bytes = output_bytes = 0
    publish = screen.publish
    publish(phase="connecting", mood="neutral", score=None, language=language, backend_busy=False)

    def read_audio():
        nonlocal reader_added, input_bytes
        chunk = os.read(sys.stdin.fileno(), 4800)
        if not chunk:
            loop.remove_reader(sys.stdin.fileno())
            reader_added = False
            finish_requested.set()
        else:
            input_bytes += len(chunk)
            if chunks.full():
                dropped = chunks.get_nowait()
                metrics.count("input_dropped_bytes", len(dropped))
            chunks.put_nowait(chunk)
            metrics.maximum("input_queued_chunks_max", chunks.qsize())

    def changed(result):
        if result.get("ok"):
            entries = result.get("entries", [])
            category = entries[-1]["category"] if entries else "other"
            mood = "glare" if category == "fried" else "wry" if category == "dessert" else "smile" if category in ("vegetable", "fruit") else "neutral"
            publish(mood=mood, score=result.get("score"), pending=result.get("pending_portions", 0))
        # Food details are already persisted in the private ledger. Avoid terminal I/O
        # in the receiver or tool callback; a slow terminal must not stall speech.

    publish()
    async with AsyncOpenAI(timeout=25, max_retries=1) as client:
        async with client.live.connect(max_retries=0) as connection:
            backend = Backend(connection, ledger, changed, metrics)

            async def handle_backend(event):
                await backend.handle(event)
                if not ending:
                    publish(backend_busy=backend.active)

            backend_worker = SerialWorker(handle_backend)

            def backend_busy():
                return backend.active or backend_worker.busy
            transcript_sync = TranscriptSync()

            async def send_audio():
                nonlocal pending_byte
                await ready.wait()
                # Live's timeline needs continuous PCM, including after microphone EOF.
                while not stopping:
                    try:
                        chunk = await asyncio.wait_for(chunks.get(), 0.1)
                    except asyncio.TimeoutError:
                        chunk = bytes(4800)
                    chunk = pending_byte + chunk
                    size = len(chunk) - len(chunk) % 2
                    pending_byte = chunk[size:]
                    if size:
                        metrics.interval("input_send_gap")
                        started = time.monotonic()
                        await connection.session.input_audio.append(audio=base64.b64encode(chunk[:size]).decode())
                        metrics.maximum("input_send_max_ms", (time.monotonic() - started) * 1000)

            async def activity_cues():
                await ready.wait()
                cue = ProcessingCue()
                tone = processing_tone()
                while not stopping:
                    playing = pcm_output.playing
                    publish(audio_playing=playing)
                    if not ending:
                        publish(phase="speaking" if playing else "listening")
                    state = dict(screen.state)
                    # No cue may follow PCM EOF or compete with the finite recap.
                    if state.get("phase") not in {"summary", "draining", "closing", "done", "error"}:
                        if cue.update(state, time.monotonic()):
                            pcm_output.offer(tone)
                            metrics.count("processing_cues")
                    await asyncio.sleep(0.1)

            async def sync_food_reports():
                await ready.wait()
                while not stopping:
                    await asyncio.sleep(0.1)
                    if transcript_sync.due(time.monotonic(), backend_busy(), ending or finish_requested.is_set()):
                        transcript_sync.dispatched()
                        backend.active = True
                        publish(backend_busy=True)
                        await connection.response.item.create(item={"type": "message", "role": "user", "content": [
                            {"type": "input_text", "text": "[APPLICATION BACKGROUND SYNC] Check recent USER speech in the conversation and maintain the food log now. A pause may be mid-sentence: do not invent missing details or treat jokes/hypotheticals as food. Reuse existing IDs; save new food once, apply corrections/removals, and keep unclear portions null. This is background bookkeeping, not a request to repeat a confirmation or score aloud. If nothing changed, finish without changing records."}]})
                        await connection.response.create()

            async def finish():
                nonlocal ending, stopping, reader_added
                await finish_requested.wait()
                await ready.wait()
                ending = True
                publish(phase="finalizing")
                if reader_added:
                    loop.remove_reader(sys.stdin.fileno())
                    reader_added = False
                reconciled = False
                try:
                    # Drain captured audio and let final transcript/delegation events arrive.
                    settle_started = time.monotonic()
                    deadline = settle_started + 8
                    while time.monotonic() < deadline:
                        if chunks.empty() and time.monotonic() - max(last_input, settle_started) > 1.5 and not backend_busy():
                            break
                        await asyncio.sleep(0.1)
                    async with asyncio.timeout(25):
                        while backend_busy():
                            await asyncio.sleep(0.1)
                        count = backend.completed
                        backend.failed = False
                        backend.active = True
                        await connection.response.item.create(item={"type": "message", "role": "user", "content": [
                            {"type": "input_text", "text": "[APPLICATION END BUTTON] Final reconciliation: use get_food_log and check all user food reports/portions/corrections in this conversation. Save any missing ones exactly once with log_food; do not ask more questions. Unknown portions stay null. Finish when the saved log matches the conversation."}]})
                        await connection.response.create()
                        while backend.completed == count and not backend.failed:
                            await asyncio.sleep(0.1)
                        reconciled = not backend.failed
                except (TimeoutError, OSError):
                    print("Final reconciliation incomplete; retaining saved entries", file=sys.stderr)
                # Drain queued tool events before freezing. The lock also protects against
                # a late delegated call while the ending is being prepared.
                async with asyncio.timeout(30):
                    await backend_worker.drain()
                async with backend.ledger_lock:
                    await off_thread(ledger.freeze, reconciled)
                summary = await localize_recap(client, backend_model, ledger, language, reconciled)
                ledger.data["summary"] = summary
                async with backend.ledger_lock:
                    await off_thread(ledger.save)
                publish(phase="synthesizing", backend_busy=False, score=ledger.snapshot()["score"], summary=summary)
                print("SUMMARY " + summary, file=sys.stderr, flush=True)
                try:
                    # Known text and finite PCM: unlike Live, this has an actual EOF.
                    async with asyncio.timeout(35):
                        speech = await client.audio.speech.create(model="gpt-4o-mini-tts", voice="marin",
                            input=summary, response_format="pcm", instructions=f"Speak only in {language}. Perform this as a witty, sharply sarcastic but supportive coach wrapping up with a friend. Conversational, not a report: brisk recap, dry comic emphasis and a short beat before the punchline. Warm when encouraging. Say only the supplied text.")
                        pcm = speech.content
                    if not pcm or len(pcm) % 2:
                        raise RuntimeError("Invalid summary PCM")
                    publish(phase="summary", summary_seconds=round(len(pcm) / 48000, 2))
                    await pcm_output.recap(pcm)
                    close_pcm_output()  # Actual pipe EOF, while the Live connection remains open.
                    publish(phase="draining")
                    async with asyncio.timeout(len(pcm) / 48000 + 20):
                        while not args.playback_ack.exists():
                            await asyncio.sleep(0.1)
                    ack = json.loads(args.playback_ack.read_text(encoding="utf-8"))
                    if ack.get("returncode") != 0:
                        raise RuntimeError("Audio player failed")
                    ledger.data["playback"] = "aplay_drained"
                    publish(phase="closing", audio_playing=False)
                except Exception as exc:
                    ledger.data["playback"] = "unconfirmed"
                    publish(phase="error", error="Summary playback unconfirmed; saved recap is available")
                    print(f"Summary failed ({type(exc).__name__}); saved recap retained", file=sys.stderr)
                finally:
                    async with backend.ledger_lock:
                        await off_thread(ledger.save)
                    stopping = True
                    await connection.session.close()
                    try:
                        await asyncio.wait_for(closed.wait(), 15)
                    except TimeoutError:
                        await connection.close()

            await connection.session.start(session={"model": "gpt-live-1", "instructions": PROMPT,
                "audio": {"format": {"type": "audio/pcm", "rate": 24000}, "output": {"voice": "marin"}},
                "delegation": {"type": "responses", "responses": {"model": backend_model,
                    "instructions": BACKEND_PROMPT, "tools": TOOLS, "parallel_tool_calls": False}}})
            sender = asyncio.create_task(send_audio())
            finisher = asyncio.create_task(finish())
            tasks = [sender, finisher, asyncio.create_task(sync_food_reports()), asyncio.create_task(activity_cues()), backend_worker.task]
            supervised = tasks + [pcm_output.worker.task, screen.task]
            # Background failure must not leave a charged, silent session open.
            def task_done(task):
                if not task.cancelled() and task.exception():
                    asyncio.create_task(connection.close())
            for task in supervised:
                task.add_done_callback(task_done)
            loop.add_signal_handler(signal.SIGINT, finish_requested.set)
            loop.add_signal_handler(signal.SIGUSR1, finish_requested.set)
            try:
                async with asyncio.timeout(args.max_seconds + 120):
                    async for event in connection:
                        kind = event.type
                        if kind == "session.started":
                            ready.set()
                            publish(phase="listening")
                            loop.add_reader(sys.stdin.fileno(), read_audio)
                            reader_added = True
                            loop.call_later(args.max_seconds, finish_requested.set)
                            print("教练已上线：说食物和份量；A 键结算。", file=sys.stderr, flush=True)
                        elif kind == "response.event":
                            if event.event["type"] in {"response.created", "response.output_item.done",
                                    "response.completed", "response.failed", "response.incomplete", "response.cancelled"}:
                                if event.event["type"] == "response.created":
                                    publish(backend_busy=True)
                                backend_worker.submit(event.event)
                        elif kind == "session.delegation.created":
                            backend.active = True
                            if not ending:
                                publish(backend_busy=True)
                        elif kind == "session.output_audio.delta" and not ending:
                            audio = base64.b64decode(event.delta)
                            output_bytes += len(audio)
                            metrics.interval("output_receive_gap")
                            metrics.count("output_chunks")
                            if backend_busy():
                                metrics.count("output_chunks_during_backend")
                            if pcm_output.offer(audio):
                                metrics.count("output_non_silent_chunks")
                                if backend_busy():
                                    metrics.count("output_non_silent_chunks_during_backend")
                        elif kind in ("session.input_transcript.delta", "session.output_transcript.delta"):
                            is_input = kind == "session.input_transcript.delta"
                            if is_input:
                                last_input = time.monotonic()
                                transcript_sync.heard(last_input)
                            if not ending:
                                publish(phase="listening" if is_input else "speaking")
                            metrics.count("input_transcript_fragments" if is_input else "output_transcript_fragments")
                        elif kind == "session.closed":
                            closed.set()
                            ledger.data["session_finalized"] = True
                            async with backend.ledger_lock:
                                await off_thread(ledger.save)
                            publish(phase="done" if ledger.data.get("playback") == "aplay_drained" else "error", audio_playing=False)
                            print(f"SESSION_CLOSED input={input_bytes} output={output_bytes}", file=sys.stderr, flush=True)
                            break
                        elif kind in ("error", "session.error"):
                            # Error payloads can contain user data; do not dump them or keys.
                            backend.failed = True
                            backend.active = False
                            publish(backend_busy=False)
                            print(f"API_ERROR {getattr(getattr(event, 'error', None), 'code', kind)}", file=sys.stderr, flush=True)
                            if not ready.is_set():
                                raise RuntimeError("Session startup rejected")
            finally:
                if reader_added:
                    loop.remove_reader(sys.stdin.fileno())
                for sig in (signal.SIGINT, signal.SIGUSR1):
                    loop.remove_signal_handler(sig)
                for task in tasks:
                    task.cancel()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        raise result
            if not closed.is_set():
                raise RuntimeError("Session finalization unconfirmed")
            if ledger.data.get("playback") != "aplay_drained":
                raise RuntimeError("Summary playback unconfirmed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    folder = LAB_DIR / ".food-coach" / uuid4().hex
    parser.add_argument("--record", type=Path, default=folder / "record.json")
    parser.add_argument("--status", type=Path, default=folder / "status.json")
    parser.add_argument("--playback-ack", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=180)
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except Exception as exc:
        try:
            state = json.loads(args.status.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        state.update(phase="error", error=type(exc).__name__, updated_at=time.time())
        atomic_json(args.status, state)
        print(f"Coach stopped: {type(exc).__name__}; saved records retained", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
