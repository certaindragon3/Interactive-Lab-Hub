# Orange v2 — from ripening to collection

Status: interaction design confirmed by Jiesen on September 16, 2026. This document describes intended behavior; it is not evidence of hardware testing.

## What changes and why

Mandy and Wenqing asked how to end a timer and prevent accidental restarts. Each routine now uses the same button to start and cancel: A for washing, B for drying. During a running timer, a short press leaves the timer unchanged; holding the initiating button for two seconds cancels it. A filling line makes that hold visible. This replaces the earlier proposal to press both buttons together.

Terence suggested extending the clock beyond the end of the wash. At the preset duration, Orange stops breathing and keeps displaying the fruit. The last fruit gradually develops brown spots while the clothes wait to be collected. Pressing the initiating button after collection ends the round. This replaces the repeating, inverted-color completion alert with a persistent representation of time since estimated completion.

Orange records time. It does not start or stop a laundry machine, detect when a machine finishes, or detect when clothes are removed. Washing and drying use the user's preset durations. Brown spots are a metaphor for elapsed waiting time, not a claim about garment damage or hygiene.

## Time and screen behavior

Only one routine is tracked at once. A is the upper button; B is the lower button in the storyboard's landscape orientation. Verify the physical mapping on Orange before calling it tested.

| Routine | Duration | Fruit blocks and ripening |
| --- | --- | --- |
| Wash | 38 minutes | Left: 0–20 min, teal to half orange. Right: 20–38 min, half orange to fully orange. |
| Dry | 60 minutes | Left: 0–20 min, teal to one-third orange. Middle: 20–40 min, one-third to two-thirds orange. Right: 40–60 min, two-thirds to fully orange. |

An unstarted fruit is a dim outline. Only the current fruit breathes, with a five-second dim–bright–dim period. A completed block holds its color and brightness. Brightness animation never resets ripening progress.

At the preset duration, the final fruit becomes fully orange and breathing stops. Earlier fruit keep their completed colors. Only the final fruit develops spots during the waiting phase. Initial configurable milestones are 10 minutes (a few brown spots), 20 minutes (more visible spots), and 30 minutes (dense spots). Spots may accumulate between milestones. After 30 minutes the visual density is capped, but elapsed waiting time continues internally. These milestones are initial design choices to evaluate, not empirically validated thresholds. There is no repeating inverted-color alert or numerical countdown in the normal display.

## Input contract

| State at press start | Initiating button: short press | Initiating button: hold for 2 seconds | Other button |
| --- | --- | --- | --- |
| Idle | A starts wash; B starts dry | Does not start a routine | Either button can start its routine with a short press |
| Running | No change; no restart | Cancel the timer, return to idle | No switching or starting |
| Waiting for collection | Confirm collection, finish the round | Also finish the round | No switching or starting |

A short press is a debounced press released before two real seconds. While running, holding the initiating button fills a thin line along the bottom of the screen over two real seconds. Releasing early removes the line and leaves the original timer running. Reaching the threshold cancels the timer. Collection briefly fades the fruit out before idle; cancellation returns to idle without presenting a collection acknowledgement.

One physical press may cause at most one action. All buttons must be released before a subsequent action is armed. Simultaneous presses have no command and must not start, cancel, or collect a round. The state and routine at press start determine the gesture: a press begun while running cannot become a collection confirmation merely because the preset duration expires while it is held. If a two-second running hold completes after that boundary, it still cancels that same round. An early release leaves the newly reached waiting state intact. These edge rules protect the confirmed interaction model; they add no new user gesture.

After confirming collection of washed clothes with A, the user moves them into the dryer, starts the dryer, and separately presses B. B never implicitly collects a wash or overwrites it. A short press in the waiting state can still accidentally confirm collection; the initial design deliberately keeps collection lightweight and makes the ending visible. That usability tradeoff remains to be tested.

## Storyboard plan

Seven main-flow frames show starting the washer and pressing A, ripening during washing, a harmless short press, estimated completion at 38 minutes, visible waiting at +20 minutes, removing clothes and confirming with A, and starting the dryer with B. Three separate cancellation frames show a running hold and two alternative outcomes: release before two seconds / hold through two seconds. The alternatives must not look like consecutive steps.

The storyboard uses pencil linework, warm paper, restrained fruit colors, short English captions, and HTML typography. Original Part E artwork remains as the first iteration. New files use `storyboard-orange-v2` names. This design document carries the full rules; the storyboard carries the observable story.

## Implementation and verification boundary

Implement the clock in an isolated worktree without replacing the course's boot-display program or original examples. Separate time/input logic from hardware so state transitions can be tested locally. Use monotonic elapsed time for timers and holds. Provide an accelerated demo mode for ripening and waiting; keep the hold threshold at two real seconds. Provide reproducible rendering or simulation evidence of idle, wash, dry, hold, ready, and overripe states.

Meaningful checks cover short-press immunity, cancellation threshold and early release, wrong-button immunity, simultaneous presses, wash/dry boundaries, overripe milestones and cap, collection, release before rearming, and gestures crossing the completion boundary. Mac tests and rendered screens do not establish GPIO operation, readability on the TFT, or visibility at the actual placement distance. Hardware validation requires Orange and must follow the local `Lab 2/AGENTS.md` service/environment instructions.

## Contributions

Jiesen selected the long-press interaction and adopted Terence's post-completion idea. Mandy and Wenqing's feedback motivated clearer stopping and accidental-input behavior; their original feedback remains in the Lab 2 report. Codex helped formulate the state rules and implementation edge cases and will generate the storyboard illustrations and layout. Implementation and test results are recorded separately when verified.
