"""Pure state and gesture logic. All timestamps are real monotonic seconds.

Call step regularly with the currently pressed buttons. Only laundry elapsed
time is accelerated; debounce, breathing, holds and collection fades stay real.
No GPIO, drawing, wall clock, filesystem or sleep calls belong in this module.
"""

from dataclasses import dataclass
from enum import Enum
import math


class Phase(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    FADING = "fading"


@dataclass(frozen=True)
class Routine:
    name: str
    button: str
    block_ends: tuple[float, ...]

    @property
    def duration(self):
        return self.block_ends[-1]


WASH = Routine("wash", "A", (20 * 60, 38 * 60))
DRY = Routine("dry", "B", (20 * 60, 40 * 60, 60 * 60))
ROUTINES = {"A": WASH, "B": DRY}


@dataclass(frozen=True)
class Config:
    speed: float = 1.0
    spot_milestones: tuple[float, float, float] = (600, 1200, 1800)
    debounce_seconds: float = 0.03
    hold_seconds: float = 2.0
    fade_seconds: float = 0.6
    breath_seconds: float = 5.0

    def __post_init__(self):
        for value in (self.speed, self.debounce_seconds, self.hold_seconds,
                      self.fade_seconds, self.breath_seconds):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Timing values and speed must be finite and positive")
        if (len(self.spot_milestones) != 3 or
                any(not math.isfinite(x) or x <= 0 for x in self.spot_milestones) or
                not all(a < b for a, b in zip(self.spot_milestones,
                                             self.spot_milestones[1:]))):
            raise ValueError("Use three finite, positive, increasing spot milestones")


@dataclass(frozen=True)
class Fruit:
    ripeness: float
    brightness: float
    outline: bool = False
    spots: float = 0.0


@dataclass(frozen=True)
class View:
    phase: Phase
    routine: Routine | None
    fruits: tuple[Fruit, ...]
    hold: float = 0.0
    opacity: float = 1.0


class Debouncer:
    """Debounce the entire button set so a chord cannot create two edges."""

    def __init__(self, seconds):
        self.seconds = seconds
        self.candidate = frozenset()
        self.stable = frozenset()
        self.since = None

    def update(self, now, raw):
        if self.since is None or raw != self.candidate:
            self.candidate, self.since = raw, now
        settled = now - self.since >= self.seconds
        if settled:
            self.stable = raw
        return settled


@dataclass
class Gesture:
    button: str
    phase: Phase
    round_id: int
    started: float
    accepted: bool = False
    invalid: bool = False
    acted: bool = False


class Timer:
    def __init__(self, config=None):
        self.config = config or Config()
        self.phase = Phase.IDLE
        self.routine = None
        self.started = None
        self.fade_started = None
        self.round_id = 0
        self.now = None
        self.buttons = Debouncer(self.config.debounce_seconds)
        self.gesture = None
        # A button held at launch must be released before it can issue commands.
        self.armed = False
        self.last_action = None

    @property
    def elapsed(self):
        if self.started is None or self.now is None:
            return 0.0
        return max(0.0, (self.now - self.started) * self.config.speed)

    @property
    def waiting_elapsed(self):
        return max(0.0, self.elapsed - self.routine.duration) if self.routine else 0.0

    def _advance(self, now):
        if not math.isfinite(now) or (self.now is not None and now < self.now):
            raise ValueError("Expected a finite, nondecreasing monotonic timestamp")
        self.now = now
        if self.phase == Phase.RUNNING and self.elapsed >= self.routine.duration:
            self.phase = Phase.WAITING
        if (self.phase == Phase.FADING and
                now - self.fade_started >= self.config.fade_seconds):
            self._idle()

    def _idle(self):
        self.phase = Phase.IDLE
        self.routine = self.started = self.fade_started = None

    def _act(self, long):
        gesture = self.gesture
        gesture.acted = True  # Even an ignored gesture is consumed once.
        if gesture.phase == Phase.IDLE:
            if not long and self.phase == Phase.IDLE:
                self.round_id += 1
                self.routine = ROUTINES[gesture.button]
                self.started = self.now
                self.phase = Phase.RUNNING
                self.last_action = "start_" + self.routine.name
        elif (gesture.round_id == self.round_id and self.routine and
              gesture.button == self.routine.button):
            if gesture.phase == Phase.RUNNING and long:
                self._idle()
                self.last_action = "cancel"
            elif gesture.phase == Phase.WAITING:
                self.phase = Phase.FADING
                self.fade_started = self.now
                self.last_action = "collect"

    def step(self, now, pressed=()):
        """Consume a raw sample and return a renderable immutable view.

        A press's state is captured at its first observed edge, before debounce
        acceptance; a running press cannot collect across the due-time boundary.
        Durations use the edges of the accepted stable press/release, so release
        debounce does not accidentally convert a 1.99 s press into a long hold.
        Any observed overlap poisons the gesture until a stable all-up sample.
        """
        raw = frozenset(pressed)
        if not raw <= {"A", "B"}:
            raise ValueError("Buttons must be A and/or B")
        self._advance(now)
        self.last_action = None
        settled = self.buttons.update(now, raw)
        if not self.armed:
            if settled and not raw:
                self.armed = True
            return self.view()

        if self.gesture is None and raw:
            button = "A" if "A" in raw else "B"
            self.gesture = Gesture(button, self.phase, self.round_id, now)

        gesture = self.gesture
        if gesture:
            if raw and raw != {gesture.button}:
                gesture.invalid = True
            if not gesture.accepted and settled and raw == {gesture.button}:
                gesture.accepted = True
                gesture.started = self.buttons.since
            if not raw and settled:
                if gesture.accepted and not gesture.invalid and not gesture.acted:
                    duration = self.buttons.since - gesture.started
                    self._act(long=duration >= self.config.hold_seconds)
                self.gesture = None
            elif (gesture.accepted and not gesture.invalid and not gesture.acted
                  and raw == {gesture.button}
                  and now - gesture.started >= self.config.hold_seconds):
                self._act(long=True)
        return self.view()

    def spot_amount(self):
        """Piecewise linear milestones: few (20%), visible (55%), dense (100%)."""
        elapsed = self.waiting_elapsed
        points = ((0.0, 0.0), *zip(self.config.spot_milestones, (0.2, 0.55, 1.0)))
        for (t0, v0), (t1, v1) in zip(points, points[1:]):
            if elapsed < t1:
                return v0 + (v1 - v0) * (elapsed - t0) / (t1 - t0)
        return 1.0

    def view(self):
        if self.routine is None:
            return View(Phase.IDLE, None, ())
        fruits = []
        block_start = 0
        count = len(self.routine.block_ends)
        for index, end in enumerate(self.routine.block_ends):
            if self.elapsed >= end:
                fruit = Fruit((index + 1) / count, 1.0)
            elif self.elapsed >= block_start:
                progress = (self.elapsed - block_start) / (end - block_start)
                # Breathe in real time; finish each block at its prescribed hue.
                seconds_in_block = (self.elapsed - block_start) / self.config.speed
                pulse = (1 - math.cos(2 * math.pi * seconds_in_block /
                                      self.config.breath_seconds)) / 2
                fruit = Fruit((index + progress) / count, 0.60 + 0.40 * pulse)
            else:
                fruit = Fruit(0.0, 1.0, outline=True)
            if index == count - 1 and self.phase in (Phase.WAITING, Phase.FADING):
                fruit = Fruit(1.0, 1.0, spots=self.spot_amount())
            fruits.append(fruit)
            block_start = end
        hold = 0.0
        gesture = self.gesture
        if (gesture and gesture.accepted and not gesture.invalid and not gesture.acted
                and gesture.phase == Phase.RUNNING
                and gesture.button == self.routine.button
                and self.buttons.candidate == {gesture.button}):
            hold = min(1.0, (self.now - gesture.started) / self.config.hold_seconds)
        opacity = 1.0
        if self.phase == Phase.FADING:
            opacity = max(0.0, 1 - (self.now - self.fade_started) / self.config.fade_seconds)
        return View(self.phase, self.routine, tuple(fruits), hold, opacity)
