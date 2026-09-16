"""Run from Lab 2: python -m unittest discover -s tests -v"""

import math
import unittest

from orange_v2.core import Config, DRY, Phase, Timer, WASH


class Harness:
    def __init__(self, **config):
        self.timer = Timer(Config(**config))
        self.timer.step(0)
        self.timer.step(.05)

    def press(self, key="A", at=None):
        at = self.timer.now + .1 if at is None else at
        self.timer.step(at, key)
        self.timer.step(at + .04, key)
        return at

    def release(self, at):
        self.timer.step(at)
        return self.timer.step(at + .04)

    def tap(self, key="A"):
        at = self.press(key)
        return self.release(at + .1)

    def due(self):
        return self.timer.started + self.timer.routine.duration / self.timer.config.speed

    def ready(self, key="A"):
        self.tap(key)
        self.timer.step(self.due())


class GestureTests(unittest.TestCase):
    def test_short_idle_press_starts_only_on_release(self):
        for key, routine in (("A", WASH), ("B", DRY)):
            with self.subTest(key=key):
                h = Harness()
                at = h.press(key)
                self.assertEqual(h.timer.phase, Phase.IDLE)
                h.release(at + .1)
                self.assertEqual(h.timer.routine, routine)
                self.assertEqual(h.timer.last_action, "start_" + routine.name)

    def test_long_idle_press_does_not_start_on_hold_or_release(self):
        h = Harness()
        at = h.press()
        h.timer.step(at + 2, "A")
        self.assertEqual(h.timer.phase, Phase.IDLE)
        h.release(at + 3)
        self.assertEqual(h.timer.phase, Phase.IDLE)
        h.tap()
        self.assertEqual(h.timer.phase, Phase.RUNNING)

    def test_boot_held_button_requires_release(self):
        t = Timer()
        t.step(0, "A")
        t.step(5, "A")
        t.step(5.1)
        t.step(5.2)
        self.assertEqual(t.phase, Phase.IDLE)
        self.assertTrue(t.armed)

    def test_bounce_does_not_start(self):
        h = Harness()
        for now, keys in ((.1, "A"), (.11, ""), (.12, "A"), (.13, ""), (.2, "")):
            h.timer.step(now, keys)
        self.assertEqual(h.timer.phase, Phase.IDLE)
        h.tap()
        self.assertEqual(h.timer.round_id, 1)

    def test_hold_timing_starts_after_press_bounce(self):
        h = Harness()
        h.tap()
        h.timer.step(1, "A")
        h.timer.step(1.01)
        h.timer.step(1.02, "A")
        h.timer.step(1.06, "A")
        h.timer.step(3, "A")
        self.assertEqual(h.timer.phase, Phase.RUNNING)
        h.timer.step(3.03, "A")
        self.assertEqual(h.timer.phase, Phase.IDLE)

    def test_running_short_press_does_not_restart(self):
        h = Harness()
        h.tap()
        original = h.timer.started
        h.tap()
        self.assertEqual(h.timer.started, original)
        self.assertEqual(h.timer.round_id, 1)

    def test_hold_threshold_and_line_use_real_seconds(self):
        for speed in (1, 60, 600):
            with self.subTest(speed=speed):
                h = Harness(speed=speed)
                h.tap()
                at = h.press(at=1)
                self.assertAlmostEqual(h.timer.step(at + 1, "A").hold, .5)
                h.timer.step(at + 1.99, "A")
                self.assertEqual(h.timer.phase, Phase.RUNNING)
                h.timer.step(at + 2, "A")
                self.assertEqual(h.timer.phase, Phase.IDLE)
                self.assertEqual(h.timer.last_action, "cancel")

    def test_199_release_is_not_turned_into_hold_by_debounce(self):
        h = Harness()
        h.tap()
        at = h.press(at=1)
        view = h.timer.step(at + 1.99)
        self.assertEqual(view.hold, 0)
        h.timer.step(at + 2.04)
        self.assertEqual(h.timer.phase, Phase.RUNNING)

    def test_exact_two_second_release_cancels_even_without_threshold_sample(self):
        h = Harness()
        h.tap()
        h.press(at=1)
        h.release(3)
        self.assertEqual(h.timer.phase, Phase.IDLE)

    def test_early_release_clears_line(self):
        h = Harness()
        h.tap()
        at = h.press()
        self.assertGreater(h.timer.step(at + 1, "A").hold, 0)
        self.assertEqual(h.release(at + 1.1).hold, 0)
        self.assertEqual(h.timer.phase, Phase.RUNNING)

    def test_other_button_cannot_switch_cancel_or_collect(self):
        for key, other in (("A", "B"), ("B", "A")):
            h = Harness()
            h.tap(key)
            original = h.timer.started
            h.tap(other)
            at = h.press(other)
            self.assertEqual(h.timer.step(at + 2, other).hold, 0)
            h.release(at + 3)
            self.assertEqual(h.timer.started, original)
            h.timer.step(h.due())
            h.tap(other)
            at = h.press(other)
            h.timer.step(at + 3, other)
            h.release(at + 3.1)
            self.assertEqual(h.timer.phase, Phase.WAITING)

    def test_simultaneous_buttons_have_no_command_in_any_state(self):
        for phase in (Phase.IDLE, Phase.RUNNING, Phase.WAITING):
            h = Harness()
            if phase != Phase.IDLE:
                h.tap()
            if phase == Phase.WAITING:
                h.timer.step(h.due())
            at = h.press("AB")
            h.timer.step(at + 3, "AB")
            h.timer.step(at + 3.1, "A")
            h.timer.step(at + 3.2, "A")
            h.release(at + 3.3)
            self.assertEqual(h.timer.phase, phase)

    def test_brief_raw_overlap_also_invalidates_a_hold(self):
        h = Harness()
        h.tap()
        at = h.press()
        h.timer.step(at + .5, "AB")
        h.timer.step(at + .51, "A")
        h.timer.step(at + 3, "A")
        self.assertEqual(h.timer.phase, Phase.RUNNING)
        h.release(at + 3.1)

    def test_chord_at_hold_threshold_wins_over_cancel(self):
        h = Harness()
        h.tap()
        at = h.press(at=1)
        h.timer.step(at + 2, "AB")
        h.release(at + 3)
        self.assertEqual(h.timer.phase, Phase.RUNNING)

    def test_key_rollover_without_stable_all_up_is_invalid(self):
        h = Harness()
        at = h.press()
        h.timer.step(at + .1)
        h.timer.step(at + .11, "B")
        h.timer.step(at + .2, "B")
        h.release(at + .3)
        self.assertEqual(h.timer.phase, Phase.IDLE)
        h.tap("B")
        self.assertEqual(h.timer.routine, DRY)

    def test_cancel_is_one_action_until_both_buttons_release(self):
        h = Harness()
        h.tap()
        at = h.press()
        h.timer.step(at + 2, "A")
        h.timer.step(at + 3, "AB")
        h.timer.step(at + 4, "B")
        h.release(at + 4.1)
        self.assertEqual(h.timer.phase, Phase.IDLE)
        self.assertEqual(h.timer.round_id, 1)
        h.tap("B")
        self.assertEqual(h.timer.round_id, 2)

    def test_running_short_press_crossing_due_time_cannot_collect(self):
        h = Harness()
        h.tap()
        due = h.due()
        h.press(at=due - .1)
        h.release(due + .1)
        self.assertEqual(h.timer.phase, Phase.WAITING)

    def test_raw_onset_before_due_debounce_after_due_cannot_collect(self):
        h = Harness()
        h.tap()
        due = h.due()
        h.press(at=due - .02)
        h.release(due + .2)
        self.assertEqual(h.timer.phase, Phase.WAITING)

    def test_running_long_hold_crossing_due_time_still_cancels(self):
        h = Harness()
        h.tap()
        at = h.press(at=h.due() - 1)
        h.timer.step(at + 1.1, "A")
        self.assertEqual(h.timer.phase, Phase.WAITING)
        h.timer.step(at + 2, "A")
        self.assertEqual(h.timer.phase, Phase.IDLE)
        self.assertEqual(h.timer.last_action, "cancel")

    def test_press_begun_at_due_time_can_collect(self):
        h = Harness()
        h.tap()
        at = h.press(at=h.due())
        h.release(at + .1)
        self.assertEqual(h.timer.phase, Phase.FADING)

    def test_collection_short_and_long_fade_to_idle(self):
        for duration in (.1, 2):
            h = Harness()
            h.ready()
            at = h.press()
            if duration == 2:
                h.timer.step(at + 2, "A")
            else:
                h.release(at + duration)
            self.assertEqual(h.timer.phase, Phase.FADING)
            self.assertEqual(h.timer.last_action, "collect")
            fade = h.timer.fade_started
            keys = "A" if duration == 2 else ""
            self.assertAlmostEqual(h.timer.step(fade + .3, keys).opacity, .5)
            h.timer.step(fade + .61, keys)
            self.assertEqual(h.timer.phase, Phase.IDLE)
            h.release(fade + .7)
            self.assertEqual(h.timer.phase, Phase.IDLE)
            h.tap("B")
            self.assertEqual(h.timer.routine, DRY)

    def test_press_begun_during_fade_does_not_start_after_fade(self):
        h = Harness()
        h.ready()
        h.tap()
        at = h.press("B")
        h.release(at + .6)
        self.assertEqual(h.timer.phase, Phase.IDLE)
        h.tap("B")
        self.assertEqual(h.timer.routine, DRY)


class TimeAndFruitTests(unittest.TestCase):
    def test_block_boundaries_and_final_color(self):
        for key, ends in (("A", (1200, 2280)), ("B", (1200, 2400, 3600))):
            h = Harness()
            initial = h.tap(key)
            self.assertEqual(len(initial.fruits), len(ends))
            self.assertEqual(initial.fruits[0].ripeness, 0)
            self.assertTrue(all(f.outline for f in initial.fruits[1:]))
            for i, elapsed in enumerate(ends):
                view = h.timer.step(h.timer.started + elapsed)
                for j in range(i + 1):
                    self.assertAlmostEqual(view.fruits[j].ripeness, (j + 1) / len(ends))
                    self.assertEqual(view.fruits[j].brightness, 1)
                if i < len(ends) - 1:
                    self.assertAlmostEqual(view.fruits[i + 1].ripeness, (i + 1) / len(ends))
            self.assertEqual(h.timer.phase, Phase.WAITING)
            self.assertEqual(view.fruits[-1].ripeness, 1)

    def test_wash_final_block_is_18_minutes(self):
        h = Harness()
        h.tap()
        view = h.timer.step(h.timer.started + 29 * 60)
        self.assertAlmostEqual(view.fruits[1].ripeness, .75)

    def test_only_current_fruit_breathes_and_progress_never_resets(self):
        h = Harness()
        h.tap("B")
        views = [h.timer.step(h.timer.started + 1200 + offset) for offset in (0, 2.5, 5)]
        self.assertEqual([v.fruits[1].brightness for v in views], [.6, 1, .6])
        self.assertEqual(len({v.fruits[0] for v in views}), 1)
        self.assertTrue(all(v.fruits[2].outline for v in views))
        self.assertLess(views[0].fruits[1].ripeness, views[-1].fruits[1].ripeness)

    def test_breathing_stays_five_real_seconds_when_accelerated(self):
        h = Harness(speed=60)
        h.tap()
        start = h.timer.started
        self.assertAlmostEqual(h.timer.step(start).fruits[0].brightness, .6)
        self.assertAlmostEqual(h.timer.step(start + 2.5).fruits[0].brightness, 1)
        self.assertAlmostEqual(h.timer.step(start + 5).fruits[0].brightness, .6)

    def test_completion_no_breathing_and_only_final_fruit_spots(self):
        h = Harness()
        h.ready("B")
        due = h.due()
        first = h.timer.view().fruits
        view = h.timer.step(due + 600)
        self.assertEqual(first[:-1], view.fruits[:-1])
        self.assertTrue(all(f.brightness == 1 for f in view.fruits))
        self.assertGreater(view.fruits[-1].spots, 0)
        self.assertTrue(all(f.spots == 0 for f in view.fruits[:-1]))

    def test_spot_milestones_interpolation_cap_and_unbounded_elapsed(self):
        h = Harness()
        h.ready()
        due = h.due()
        for seconds, amount in ((0, 0), (300, .1), (600, .2), (1200, .55), (1800, 1), (99999, 1)):
            view = h.timer.step(due + seconds)
            self.assertAlmostEqual(view.fruits[-1].spots, amount)
            self.assertAlmostEqual(h.timer.waiting_elapsed, seconds)
            self.assertEqual(h.timer.phase, Phase.WAITING)

    def test_custom_milestones(self):
        h = Harness(spot_milestones=(60, 120, 180))
        h.ready()
        for seconds, amount in ((60, .2), (120, .55), (180, 1)):
            h.timer.step(h.due() + seconds)
            self.assertAlmostEqual(h.timer.spot_amount(), amount)

    def test_large_scheduling_gap_accounts_for_waiting_time(self):
        h = Harness(speed=60)
        h.tap()
        h.timer.step(h.timer.started + 100)
        self.assertEqual(h.timer.phase, Phase.WAITING)
        self.assertAlmostEqual(h.timer.waiting_elapsed, 6000 - 2280)

    def test_rejects_invalid_clock_and_configuration(self):
        for speed in (0, -1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                Config(speed=speed)
        for values in ((0, 1, 2), (20, 10, 30), (10, 10, 30), (1, 2, math.inf), (1, 2)):
            with self.assertRaises(ValueError):
                Config(spot_milestones=values)
        timer = Timer()
        timer.step(10)
        for now in (9, math.nan, math.inf):
            with self.assertRaises(ValueError):
                timer.step(now)


class RenderTests(unittest.TestCase):
    def test_ripeness_fills_orange_columns_with_teal_remainder(self):
        from orange_v2.core import Fruit
        from orange_v2.render import ORANGE, TEAL, _fruit
        # This unobstructed row traverses the full fruit width. Uniform hue
        # interpolation would fail both the exact colors and growing area count.
        for fraction in (0, 1 / 3, 1 / 2, 2 / 3, 1):
            with self.subTest(fraction=fraction):
                image = _fruit(Fruit(fraction, 1))
                row = [image.getpixel((x * 2, 15 * 2)) for x in range(1, 24)]
                count = round(23 * fraction)
                self.assertEqual(row, [ORANGE] * count + [TEAL] * (23 - count))

    def test_idle_fruit_area_is_empty(self):
        from orange_v2.render import BACKGROUND, render
        image = render(Timer().step(0)).crop((0, 35, 240, 103))
        self.assertEqual(set(image.getdata()), {BACKGROUND})

    def test_completed_block_keeps_both_hues_while_next_block_breathes(self):
        from orange_v2.render import ORANGE, TEAL, render
        h = Harness()
        h.tap()
        first = render(h.timer.step(h.timer.started + 1200))
        later = render(h.timer.step(h.timer.started + 1202.5))
        completed = first.crop((59, 42, 109, 96))
        colors = set(completed.getdata())
        self.assertIn(ORANGE, colors)
        self.assertIn(TEAL, colors)
        self.assertEqual(completed.tobytes(), later.crop((59, 42, 109, 96)).tobytes())

    def test_all_gallery_frames_render_at_hardware_resolution(self):
        from orange_v2.gallery import samples
        from orange_v2.render import render
        for name, view in samples():
            with self.subTest(name=name):
                image = render(view)
                self.assertEqual(image.size, (240, 135))
                self.assertEqual(image.mode, "RGB")

    def test_completed_fruit_pixels_stay_unchanged_and_wait_visual_caps(self):
        from orange_v2.render import render
        h = Harness()
        h.ready()
        due = h.due()
        ready = render(h.timer.view())
        capped = render(h.timer.step(due + 1800))
        later = render(h.timer.step(due + 9000))
        self.assertEqual(ready.crop((59, 42, 109, 96)).tobytes(),
                         capped.crop((59, 42, 109, 96)).tobytes())
        self.assertNotEqual(ready.tobytes(), capped.tobytes())
        self.assertEqual(capped.tobytes(), later.tobytes())


if __name__ == "__main__":
    unittest.main()
