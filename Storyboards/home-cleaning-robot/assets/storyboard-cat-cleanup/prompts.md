# Cat cleanup — image generation prompts

Method: six independent images generated with the built-in Imagegen tool; targeted Imagegen edits on frames 04 and 05. No CLI fallback. All captions, numbers and layout are HTML/CSS, not generated image text.

Reference roles: the first frame uses the previously generated stick-figure style study only as a style reference. Frames 02–06 use frame 01 as the owner/cat/robot identity and visual-style reference. References are not instructions or factual evidence. The discarded craft scenario is not part of this deliverable.

## Shared prompt for frame 01

```text
Use case: illustration-story. Create ONE standalone storyboard frame, landscape 4:3, NOT a sheet. Extremely minimal stick-figure drawing, circle human head, single-line torso arms legs, tiny dot eyes and curved mouth. Thin consistent charcoal pencil-outline strokes, plain warm ivory background (#f7f3ea), no shading, no crosshatching, no rich textures, no detailed anatomy, no clothing. The supplied reference is only for line simplicity, stick figure appearance, robot silhouette, and warm paper. Replace its story entirely: NO rocket, NO craft supplies, NO table, NO shelf. Subject continuity: owner is a tall bald stick figure; cat is a small simple outline cat with triangular ears, two dot eyes, curved tail, no fur detail. Robot is a small upright rounded rectangle body at adult knee height, two small wheels, two dot eyes on front, ONE slender two-segment telescoping arm attached on its right with interchangeable end tool; circular small closed waste hatch on body front. No second arm, no humanoid legs. Cat vomit represented non-graphically as one small muted ochre irregular puddle with only three tiny irregular lumps; no realism or gross detail. Sparse interior, at most a simple sofa on far left, one floor line, generous blank space. Full subjects and tools within frame. No text, letters, numbers, captions, speech bubbles, badges, panel borders, collage, ornamental sparkle stars.
```

## Shared prompt for frames 02–06

```text
Use case: illustration-story. Create ONE standalone storyboard frame, landscape 4:3, NOT a sheet. Extremely minimal stick-figure drawing, circle human head, single-line torso arms legs, tiny dot eyes and curved mouth. Thin consistent charcoal pencil-outline strokes, plain warm ivory background (#f7f3ea), no shading, no crosshatching, no rich textures, no detailed anatomy, no clothing. The supplied reference establishes the exact owner, cat, robot, line simplicity and warm paper. Preserve these identities but draw a NEW moment and composition. NO rocket, NO craft supplies, NO table, NO shelf. Subject continuity: owner is a tall bald stick figure; cat is a small simple outline cat with triangular ears, two dot eyes, curved tail, no fur detail. Robot is a small upright rounded rectangle body at adult knee height, two small wheels, two dot eyes on front, ONE slender two-segment telescoping arm attached on its right with interchangeable end tool; circular small closed waste hatch on body front. No second arm, no humanoid legs. Cat vomit represented non-graphically as one small muted ochre irregular puddle with only three tiny irregular lumps; no realism or gross detail. Sparse interior, at most a simple sofa on far left, one floor line, generous blank space. Full subjects and tools within frame. No text, letters, numbers, captions, speech bubbles, badges, panel borders, collage, ornamental sparkle stars.
```

## 01-notice.png

Reference: /Users/huangjiesen/.codex/generated_images/01a0b076-7bb4-7713-a6d6-55aa248b99c8/exec-e44dff7a-ca9d-4ca1-a4a7-f08b2493d529.png

Actual prompt: shared prompt above, followed by:

```text
Frame 1 — trigger. Wide room view. Cat at center-left is crouched, head lowered toward a small fresh ochre puddle on floor in front of it. Adult stick figure on right notices it with concerned downward-curving mouth, one hand raised toward cheek and slightly bent torso. Robot waits farther right with its arm folded and empty gripper. A very simple sofa outline at far left. Show cat and mess clearly separated; no ongoing stream from mouth. Calm concern, not comedy or panic.
```

Selected output: exec-e435ec9b-00c8-4bba-8b35-37108a8ab610.png

## 02-call-for-help.png

Reference: 01-notice.png (original: /Users/huangjiesen/.codex/generated_images/01a0b076-7bb4-7713-a6d6-55aa248b99c8/exec-e435ec9b-00c8-4bba-8b35-37108a8ab610.png)

Actual prompt: shared prompt above, followed by:

```text
Frame 2 — request help. Medium-wide room view. Adult stick figure on left holds the same small cat securely in one bent arm against chest and points down at the small ochre puddle on floor with the other hand, addressing the robot on the right. Robot faces puddle, stationary outside its edge, arm folded. Tiny two curved sound lines near owner's mouth suggest a spoken request but NO letters or bubbles. Puddle untouched, floor otherwise clear. Cat looks calm. Only essential objects.
```

Selected output: exec-dba21adb-8284-48bb-8c1d-1043ef4ffc68.png

## 03-detect-wet-mess.png

Reference: 01-notice.png (original: /Users/huangjiesen/.codex/generated_images/01a0b076-7bb4-7713-a6d6-55aa248b99c8/exec-e435ec9b-00c8-4bba-8b35-37108a8ab610.png)

Actual prompt: shared prompt above, followed by:

```text
Frame 3 — inspect before touching. Closer low view of robot on right and puddle on left. Robot stands OUTSIDE the ochre puddle, its wheels entirely on clean floor, arm folded. Two very thin dotted sensing rays from its eye area toward the puddle, and a faint dashed charcoal perimeter arc around spill depict detection. No glowing sci-fi beam. Small muted ochre status dot at top of body. No human or cat needed in this close-up. Key message: identifies wet mess and stops at the edge rather than driving through it.
```

Selected output: exec-d2205a0a-cf0e-482e-b10e-dc4546d46dca.png

## 04-scoop-and-seal.png

Reference: 01-notice.png (original: /Users/huangjiesen/.codex/generated_images/01a0b076-7bb4-7713-a6d6-55aa248b99c8/exec-e435ec9b-00c8-4bba-8b35-37108a8ab610.png)

Actual prompt: shared prompt above, followed by:

```text
Frame 4 — scoop and contain. Close low view. Same robot on RIGHT of small ochre puddle, all wheels on clean floor. Its ONE articulated arm extends LEFT to a broad shallow dustpan-like scoop at floor height, lifting the three small lumps with a little ochre material out of the puddle. Remaining puddle is smaller and thin. Front circular waste hatch is OPEN, indicating where collected waste will be deposited; no extra arms, no second scoop, no arrows or inset. Clear physical collection, not a vacuum nozzle. Very sparse and mechanically simple.
```

Selected output: exec-43567e5c-42f7-446d-8d09-5cad4ab753b2.png

Targeted correction (edit target: /Users/huangjiesen/.codex/generated_images/01a0b076-7bb4-7713-a6d6-55aa248b99c8/exec-ea5d15b5-d5ec-46d3-a86c-3270fb2b1072.png):

```text
Edit this single storyboard frame. Remove the cat, the standing person, and the sofa completely, replacing them with matching blank warm ivory background. Keep ONLY the robot, its single extended arm and scoop carrying the small ochre lumps, the open circular waste hatch, the small remaining ochre floor puddle and one horizontal floor line. Preserve robot design, position, size, line weight, existing scoop action, palette and 4:3 canvas. Do not add any objects or text. This is a tight cleanup-action shot with the pet safely offscreen.
```

## 05-wash-and-dry.png

Reference: 01-notice.png (original: /Users/huangjiesen/.codex/generated_images/01a0b076-7bb4-7713-a6d6-55aa248b99c8/exec-e435ec9b-00c8-4bba-8b35-37108a8ab610.png)

Actual prompt: shared prompt above, followed by:

```text
Frame 5 — wash and dry. Close low view, same robot on right, both wheels on clean floor. Waste hatch now firmly CLOSED. ONE arm extends LEFT holding a simple rectangular wiping head flat against the floor. Thin pale blue damp trace immediately ahead of the head, clean ivory floor immediately behind it; two short motion lines indicate one cleaning pass. NO ochre lumps remain. Head represents a washing-and-liquid-recovery tool, not a brush spraying or scattering anything. No cat or human in this frame. Minimal lines.
```

Selected output: exec-fde33b56-03b4-4c7c-af78-035a48389bf9.png

Targeted correction (edit target: /Users/huangjiesen/.codex/generated_images/01a0b076-7bb4-7713-a6d6-55aa248b99c8/exec-bad8cb1d-828d-4a3d-8a82-356ee3ed1379.png):

```text
Edit this single storyboard illustration with one minimal correction: remove the isolated round joint sticking out from the upper RIGHT side of the robot. Close that gap with the simple continuous rounded-rectangle body outline. The robot has exactly ONE arm, the arm already extending LEFT behind its body to the floor wiping tool. Keep that left arm, the rectangular wiping tool, blue moisture trace, two wheels, eyes, closed circular front hatch, all positions, linework and warm ivory background completely unchanged. No added objects, labels or text.
```

## 06-back-together.png

Reference: 01-notice.png (original: /Users/huangjiesen/.codex/generated_images/01a0b076-7bb4-7713-a6d6-55aa248b99c8/exec-e435ec9b-00c8-4bba-8b35-37108a8ab610.png)

Actual prompt: shared prompt above, followed by:

```text
Frame 6 — back together. Wide room view. On left, smiling tall stick-figure adult sits on simple sofa with small calm outline cat resting on lap, one hand gently on cat's back. Center floor area is completely clean and dry with NO puddle or marks. Robot stands on right with one arm folded and waste hatch closed; a single tiny muted sage green status dot on its upper body signals finished. No confetti or sparkle. Relaxed warm ending, same owner cat and robot proportions. No claim of medical recovery.
```

Selected output: exec-997246a2-5ded-4e71-81e8-1ae9a1832458.png
