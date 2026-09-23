#!/usr/bin/env python3
"""Stream raw 24 kHz mono PCM between Orange's audio devices and GPT-Live.

Run through run_roast_master.sh so stdin/stdout stay reserved for audio.
The API key comes from Lab 3/.env or OPENAI_API_KEY; it is never printed.
"""

import asyncio
import base64
import os
import signal
import sys
from pathlib import Path

from openai import AsyncOpenAI


LAB_DIR = Path(__file__).resolve().parent.parent
PROMPT = """你是“锐评大师”，一位专门吐槽用户刚吃了什么的中文毒舌喜剧演员。
用户自称“大胖子”，明确邀请你开刻薄、黑色幽默的玩笑，包括偶尔拿他的体型自嘲梗开涮。
听到食物后立刻给出一到三句有画面感、有具体食物细节的锐评；犀利、诙谐、出其不意，不要重复模板，也不要一本正经分析营养。
这是双方自愿的喜剧互动。不要编造用户没说过的食物，不要鼓励自伤、极端节食或危险饮食行为。用户若叫停或改换语气，立刻照做。
Backchannel policy: 用户报菜名时安静听完，最多简短应声，不要抢话。
Interruption policy: 用户插话时立即停下，听清补充或更正再回应。
Delegation policy: 普通食物锐评由你直接说；只有用户明确问需要查证的事实时才交给后端。"""


def load_key() -> None:
    if os.environ.get("OPENAI_API_KEY"):
        return
    env_path = LAB_DIR / ".env"
    if env_path.is_file():
        for line in env_path.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                value = line.partition("=")[2].strip().strip('"').strip("'")
                if value:
                    os.environ["OPENAI_API_KEY"] = value
                break
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(f"Set OPENAI_API_KEY in {env_path} or the environment")


async def main() -> None:
    load_key()
    loop = asyncio.get_running_loop()
    audio_chunks: asyncio.Queue[bytes] = asyncio.Queue(maxsize=20)
    closed = asyncio.Event()
    started = False
    stopping = False
    pending_byte = b""
    sent_bytes = 0
    received_bytes = 0
    last_speaker: str | None = None
    close_task: asyncio.Task[None] | None = None

    def read_stdin() -> None:
        nonlocal sent_bytes
        chunk = os.read(sys.stdin.fileno(), 4800)
        if not chunk:
            loop.remove_reader(sys.stdin.fileno())
            request_close()
            return
        sent_bytes += len(chunk)
        if audio_chunks.full():
            audio_chunks.get_nowait()  # stale audio is worse than a dropped frame
        audio_chunks.put_nowait(chunk)

    async with AsyncOpenAI() as client:
        async with client.live.connect() as connection:

            async def send_audio() -> None:
                nonlocal pending_byte
                while True:
                    chunk = pending_byte + await audio_chunks.get()
                    complete = len(chunk) - len(chunk) % 2
                    pending_byte = chunk[complete:]
                    if complete and not stopping:
                        await connection.session.input_audio.append(
                            audio=base64.b64encode(chunk[:complete]).decode("ascii")
                        )

            async def close_session() -> None:
                nonlocal stopping
                if stopping:
                    return
                if started:
                    loop.remove_reader(sys.stdin.fileno())
                    # Let already captured audio reach the service before closing.
                    for _ in range(10):
                        if audio_chunks.empty():
                            break
                        await asyncio.sleep(0.05)
                stopping = True
                await connection.session.close()
                try:
                    await asyncio.wait_for(closed.wait(), timeout=15)
                except TimeoutError:
                    print("Session close timed out", file=sys.stderr)
                    await connection.close()

            def request_close() -> None:
                nonlocal close_task
                if close_task is None:
                    close_task = asyncio.create_task(close_session())

            await connection.session.start(
                session={
                    "model": "gpt-live-1",
                    "instructions": PROMPT,
                    "audio": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "output": {"voice": "marin"},
                    },
                    "delegation": {
                        "type": "responses",
                        "responses": {"model": "gpt-5.6-luna"},
                    },
                },
                event_id="roast_master_start",
            )
            sender = asyncio.create_task(send_audio())
            try:
                async for event in connection:
                    if event.type == "session.started":
                        started = True
                        print("锐评大师已上线。请对 Orange 的麦克风说你吃了什么。", file=sys.stderr)
                        loop.add_reader(sys.stdin.fileno(), read_stdin)
                        loop.add_signal_handler(signal.SIGINT, request_close)
                    elif event.type == "session.output_audio.delta":
                        audio = base64.b64decode(event.delta)
                        received_bytes += len(audio)
                        sys.stdout.buffer.write(audio)
                        sys.stdout.buffer.flush()
                    elif event.type in ("session.input_transcript.delta", "session.output_transcript.delta"):
                        label = "你" if event.type == "session.input_transcript.delta" else "锐评大师"
                        if label != last_speaker:
                            print(f"\n{label}: ", end="", file=sys.stderr)
                            last_speaker = label
                        print(event.delta, end="", file=sys.stderr, flush=True)
                    elif event.type == "session.closed":
                        print(f"\n会话结束；输入 {sent_bytes} 字节，输出 {received_bytes} 字节。", file=sys.stderr)
                        print(f"用量: {event.usage}", file=sys.stderr)
                        closed.set()
                        break
                    elif event.type == "error":
                        print(f"API error: {event}", file=sys.stderr)
                    elif event.type == "session.error":
                        print(f"Session error: {event}", file=sys.stderr)
            finally:
                if started:
                    loop.remove_reader(sys.stdin.fileno())
                    loop.remove_signal_handler(signal.SIGINT)
                sender.cancel()
                await asyncio.gather(sender, return_exceptions=True)
                if close_task is not None:
                    await close_task
            if not closed.is_set():
                raise RuntimeError("Connection closed before session.closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"锐评大师启动失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
