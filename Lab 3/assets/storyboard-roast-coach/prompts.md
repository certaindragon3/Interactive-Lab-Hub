# Storyboard image generation prompts

Generated with the built-in Imagegen tool on 2026-09-23. Each frame was generated as a separate 4:3 illustration; HTML supplies all captions and numbers. The Lab 2 storyboard was a **style reference only** for frame 01. Frames 02–06 used the accepted frame 01 as a **continuity reference**. Frames 05 and 06 were then edited to remove unrelated food bubbles; only the edited versions are used.

## 01-start.png

Reference: ../../../Lab 2/storyboard-orange-render.png, style only.

> Use case: illustration-story. Create ONE standalone landscape 4:3 storyboard frame, first panel of a six-panel interaction story. Reference image supplies ONLY the restrained warm ivory paper, pencil linework, thin grey graphite shading, subtle color pencil accents and spacious visual style, not its orange fruit or screen graphics. Consistent subject for all future panels: a small white rectangular Raspberry Pi desktop device with a black horizontal screen on its right and two round physical buttons vertically stacked on its left, viewed on a kitchen table. One adult user with simple neutral appearance sits beside it. Frame 1: medium shot, user deliberately presses the TOP round button with one finger, preparing to report food to a voice coach. Screen shows one small neutral off-white circular face with simple eyes and mouth, just waking up; a tiny microphone indication may be represented by subtle listening arcs but no text. Keep device and finger legible at small size; human has an everyday, expectant expression. No collage, no other panels, no labels, no title, no lettering, no speech bubbles, no number badge, no panel border, no food yet.

## 02-broccoli.png to 06-laugh.png

Reference: 01-start.png, exact character/device continuity guide. The following common prompt was prepended to each frame-specific instruction:

> Use case: illustration-story. Create ONE standalone landscape 4:3 storyboard frame in a six-panel sequence. Image reference is the exact visual/character/device continuity guide: same adult woman with short dark bob and muted sage sweater, same small white rectangular Raspberry Pi desktop device on kitchen table with two vertically stacked round buttons on left and black horizontal screen on right. Warm ivory paper, restrained graphite outlines and fine colored pencil, spacious composition. The device screen has exactly ONE small circular face with simple eyes/mouth, not multiple circles. Food shown only as a small floating hand-drawn memory doodle of what she is reporting, not as a meal physically on table. No text, labels, letters, speech bubbles, title, collage, number badge, border, or extra controls.

### 02-broccoli.png

> Panel 2. Medium shot. The woman speaks to the device and lightly gestures as she reports broccoli; a tiny broccoli doodle floats near her speech gesture. On device screen the circular face is bright leafy green with warmly smiling eyes, gentle upbeat motion marks. She is encouraged and amused. Do not show cake or chicken.

### 03-cake.png

> Panel 3. Same kitchen, medium close shot. The woman confesses to a slice of cake with a playful sheepish expression; a small cake-slice doodle floats near her raised hand. The one circular face on the screen turns golden yellow, with one raised eyebrow and a crooked sardonic smile; one restrained eyebrow twitch mark. This is a comic tonal shift, not a scolding. No broccoli or chicken.

### 04-chicken.png

> Panel 4. Same kitchen, scene widens slightly. She adds that she ate fried chicken too, hand near face as if bracing for the response. A single small fried chicken drumstick memory doodle floats near her gesture. The one circular face on device screen has gone vivid red with narrowed angry eyebrows, little radiating agitation ticks. She watches it with surprised amusement. No other food.

### 05-pause.png

> Panel 5. Dramatic reaction close-up of the SAME Raspberry Pi device with its two stacked buttons and black screen; in the screen ONE vivid red circular face with eyebrows raised as if incredulous, mouth closed, holding a theatrical silent beat before delivering the punchline. A small pulse of light and sparse graphite motion arcs suggest a held pause. Woman's face appears only in edge of frame, watching expectantly. No food, no text.

Edit target: the first generated panel 05. Final edit prompt:

> Use case: precise-object-edit. This image is the EDIT TARGET, not just a style reference. Remove ONLY the entire thought bubble containing banana and apple, including its outlines and adjacent radiating marks. Restore that upper central area as the same clean warm ivory kitchen wall, matching existing subtle pencil texture. Keep woman, her expression, device, two buttons, black screen, single red circular face, kitchen counter, plant, style, composition and dimensions unchanged. Do not add new text, labels, symbols, food, or bubbles.

### 06-laugh.png

> Panel 6. Same woman in kitchen laughs at the absurd sharp comeback from the voice coach, shoulders loosened, one hand pointing toward the device. The SAME screen has one red circular face with a sly sideways smirk, less angry than before, and small audio rhythm lines, suggesting a comic line just spoken. Her other hand approaches the TOP button to end the session, but is not yet touching it. No physical food, no text.

Edit target: the first generated panel 06. Final edit prompt:

> Use case: precise-object-edit. This image is the EDIT TARGET, not just a style reference. Remove ONLY the entire thought bubble containing ice cream and its outline and nearby radiating marks. Restore the area as matching warm ivory kitchen wall. Keep laughing woman, her hands pressing the top button, device with two buttons, black screen and one red smirking circular face, kitchen setting, style, composition and dimensions unchanged. Do not add new text, labels, symbols, food, or bubbles.
