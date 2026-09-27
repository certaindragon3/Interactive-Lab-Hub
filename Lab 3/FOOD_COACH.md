# Part 2 food coach: implementation and verification

The current prototype uses GPT-Live for English conversation and the existing OpenAI Python SDK's Responses delegation for food tools. The application schedules a background backend pass after about 1.2 seconds without new user transcript fragments; it does not rely on the voice character to remember to delegate. A pause is only a scheduling cue, not proof of a complete utterance. Later fragments and corrections are reconciled using the same entry IDs. `food_coach.py` owns the record and score; the voice and backend models do not choose a numeric score. No Agents SDK, MCP server, camera, or nutrition database is required.

## Interaction

1. Press the upper **A button (GPIO23)** to start. A beep acknowledges the press; the screen moves from CONNECTING to LISTENING.
2. The coach always speaks English, including when your first utterance or later food reports use another language. Report a food and portion. The backend uses `get_food_log` to establish or recover authoritative IDs, then calls `log_food`; it reuses known IDs instead of rereading the log before every add. Unknown portions are saved as pending and the coach asks for clarification. You can interrupt a joke, correct a food or portion, remove an entry, or ask for a gentler tone.
3. Press A again to finish. Repeated end presses are ignored. Microphone EOF requests final reconciliation, rather than closing the API connection. The application checks the last reports, freezes and saves the ledger, and creates the recap text.
4. The recap is rendered through `gpt-4o-mini-tts` and sent to the same speaker stream. Closing the PCM pipe lets `aplay` drain the entire output. Only after the controller acknowledges `aplay` exit 0 does the client send `session.close`. This verifies the audio process completed; a listener still needs to verify audibility and wording.
5. The controller returns to a saved-result screen, ready for another check-in. A new check-in creates a separate record. **This is not a persistent daily total across sessions.**

The check-in automatically ends after 180 seconds, with additional bounded time for reconciliation, synthesis and playback. Ctrl+C requests the same graceful ending and then exits the controller. If shutdown fails, the saved recap remains available and the UI shows CHECK LOG; it must not be described as a delivered summary.

## Demonstration scoring rubric: `menu-game-v1`

This is a fictional menu game, not a validated nutrition, calorie, weight, or health score. The weights are design choices for testing the interaction, not dietary advice.

| Category | Points per entry with a stated portion |
| --- | ---: |
| Vegetable | +10 |
| Fruit | +10 |
| Protein | +5 |
| Staple | +5 |
| Dessert | −5 |
| Fried food | −10 |
| Other / mixed or unclear dish | 0 |

Start at 50, cap each category's total contribution to −20…+20, then clamp the final score to 0…100. If no entry has a stated portion, return no score rather than 50. Pending portions contribute nothing. An explicitly stated amount and unit (such as one bowl, half a slice or two pieces) is sufficient for this game. A bare size adjective like “large steak” is rejected as a known portion and must remain pending; the stated amounts are retained and **do not scale the points or imply measured serving sizes**. Fried chicken uses the fried category, not both fried and protein. The model classifies the reported food; users can correct that interpretation.

Example: one bowl of broccoli (+10), half a slice of cake (−5), and two pieces of fried chicken (−10) produce **45**. Cake without a portion is pending, so broccoli alone produces a provisional 60. Clarifying cake as half a slice changes this to 55 without adding a second cake entry.

Each food has a stable entry ID. An identical add with that ID is idempotent; an altered add is rejected and requires `correct`. The same food/portion under a new ID is rejected unless it is explicitly an additional serving. Replayed function call IDs return their saved result; reusing an ID with different arguments is rejected. Corrections recompute the score; removals delete an entry. These checks prevent transport retries and ordinary recap duplicates, but semantic recognition still depends on the model and speech transcription.

## Screen and humor

The colored face conveys the coach's theatrical reaction: green smile, yellow raised eyebrow, red glare. It follows the most recently saved food category, not the numerical total. A separate neutral label/cue shows listening, saving, speaking and recap phases. Recent output transcript activity drives SPEAKING; the display is an activity cue, not an exact phoneme animation. The score appears at the ending. The screen implements the state cue; no separate LED wiring or driver is added.

The first physical test felt too mechanical to the author. The next prompt explicitly restores both sides of the character: specific, sincere encouragement and strong, contextual judgment of the menu. It varies the attitude across turns, remembers earlier foods for callbacks, and lets the voice respond while bookkeeping happens in the background. Routine “received / saved / corrected” narration and repeated score announcements are discouraged. The ending uses a shorter application-written recap with a category-based comic closing, rendered with expressive TTS instructions.

The prompt targets food choices and combinations, never the user's body, weight or worth. It must soften or stop on request and respond supportively to genuine distress. Short jokes, interruption and a suggested pause preserve the comic intent. A precisely timed one-second stare and synchronized interruption animation are not implemented.

## Run on Orange

Use the existing Lab 2 hardware environment at the repository root and Lab 3's voice environment. The launch script stops the competing `piscreen.service` and restores it on exit if it was active before launch.

```bash
cd ~/Interactive-Lab-Hub
bash 'Lab 3/speech-scripts/run_roast_button.sh'
```

Every check-in is initialized with `language=en`; there is no first-utterance language detection call. Praise, roasts, clarification questions and the humorous recap all use English. Food names are stored in English for the spoken recap, while stated portions are preserved. Numeric values are still inserted by the application after placeholder validation.

The existing ignored `Lab 3/.env` supplies the API key. Do not put keys in source or logs. `COACH_PYTHON`, `COACH_HARDWARE_PYTHON` and `COACH_ENV_FILE` allow testing in an isolated deployment directory while reusing the existing environments and credential file. `COACH_BACKEND_MODEL` overrides the existing `gpt-5.6-luna` backend when explicitly testing another supported model.

Private records live in `Lab 3/.food-coach/<session-id>/record.json`, with status and playback acknowledgment files alongside them. Records are written atomically in UTF-8 with mode 0600, retain the rubric, computed snapshot, tool-call results, summary and delivery/finalization status, and are ignored by Git. Food tool output and transcript fragments are also printed to the local terminal; keep redirected logs private. Raw microphone recordings are not retained by this application.

## Verification commands

```bash
python3 -m unittest discover -s 'Lab 3/tests' -v
bash -n 'Lab 3/speech-scripts/run_roast_button.sh'
```

An optional paid API test generates synthetic Chinese speech, exercises the real Live/tools/recap path, and asserts the saved results after every report while the session is still open, as well as after finalization. `null` is silent; use `--device default` for actual ALSA speaker output. This is not a microphone, button, participant or usability test.

```bash
'Lab 3/.venv/bin/python' 'Lab 3/speech-scripts/smoke_food_coach.py' --device default
# English opening with a Chinese correction; output stays English:
'Lab 3/.venv/bin/python' 'Lab 3/speech-scripts/smoke_food_coach.py' --device null --language en
```

For a bounded physical controller test, run the launch script with `--run-seconds 240`. Then press A, report broccoli and cake, clarify or correct the cake portion, add fried chicken, and press A during or after a joke. Verify the recap, score, complete audio ending and visible states. After the controller exits, check `systemctl is-active piscreen.service`.

## API references

The implementation follows the [GPT-Live function-result continuation flow](https://developers.openai.com/api/docs/guides/live-delegation): collect function items from nested `response.output_item.done`, return all function outputs, then explicitly continue the response. The nested lifecycle event's empty `response.output` is not evidence that no tools ran. SDK 3.19.1 exposes the nested event as a dictionary.

[Managing GPT-Live sessions](https://developers.openai.com/api/docs/guides/live-conversations) documents the absence of a WebSocket output-audio-done event. The finite ending uses [text to speech](https://developers.openai.com/api/docs/guides/text-to-speech), PCM EOF and the local player's exit status instead of guessing completion from transcript silence.


The isolated Orange deployment used for this iteration can be started without replacing the existing device checkout:

```bash
ssh -t Orange 'bash /home/pi/food-coach-part2.8OiVJ8/run-coach.sh'
```
