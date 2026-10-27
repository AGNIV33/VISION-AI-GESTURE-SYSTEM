from vision_ai.actions.dispatcher import Dispatcher
from vision_ai.gestures.hand_pose import EXT, FOLD, HandPose
from vision_ai.gestures.recognizer import DRAG, IDLE, SCROLL, ZOOM, GestureRecognizer

OPEN = (EXT, EXT, EXT, EXT)
FIST = (FOLD, FOLD, FOLD, FOLD)
PEACE = (EXT, EXT, FOLD, FOLD)
DT = 1 / 30


def pose(idx=1.0, mid=1.0, fingers=OPEN):
    return HandPose(pinch_index=idx, pinch_middle=mid, fingers=fingers)


class Runner:
    """Feeds pictures at 30 fps and collects everything that happened."""

    def __init__(self):
        self.r = GestureRecognizer()
        self.t = 0.0
        self.events = []
        self.out = None

    def feed(self, p, pos=(500.0, 500.0), frames=1):
        for _ in range(frames):
            self.t += DT
            self.out = self.r.update(p, pos, self.t)
            self.events += self.out.events
        return self.out


def test_open_hand_just_moves():
    run = Runner()
    out = run.feed(pose(), frames=20)
    assert out.state == IDLE and not out.freeze and run.events == []


def test_quick_pinch_is_a_left_click():
    run = Runner()
    run.feed(pose(), frames=3)
    run.feed(pose(idx=0.1), frames=4)  # ~130 ms pinch
    run.feed(pose(idx=0.9), frames=3)
    assert run.events == [("click", "left")]


def test_cursor_freezes_while_pinching_so_the_click_lands_still():
    run = Runner()
    run.feed(pose())
    assert run.feed(pose(idx=0.45)).freeze  # fingers getting close
    assert run.feed(pose(idx=0.1), frames=3).freeze  # pinched


def test_relaxed_hand_near_pinch_does_not_freeze_forever():
    run = Runner()
    run.feed(pose())
    out = run.feed(pose(idx=0.45), frames=20)  # hovering, never pinching
    assert not out.freeze and run.events == []


def test_one_noisy_picture_is_not_a_click():
    run = Runner()
    run.feed(pose(), frames=3)
    run.feed(pose(idx=0.1), frames=1)  # single glitch
    run.feed(pose(idx=0.9), frames=5)
    assert run.events == []


def test_pinch_and_move_is_a_drag():
    run = Runner()
    run.feed(pose(), frames=2)
    run.feed(pose(idx=0.1), frames=3)
    out = run.feed(pose(idx=0.1), pos=(600, 500))  # moved 100 units
    assert out.state == DRAG and run.events == [("down", "left")]
    assert not out.freeze  # cursor follows the hand while dragging
    run.feed(pose(idx=0.1), pos=(700, 500), frames=5)
    run.feed(pose(idx=0.9), pos=(700, 500), frames=3)
    assert run.events == [("down", "left"), ("up", "left")]


def test_long_pinch_without_moving_becomes_a_drag_not_a_click():
    run = Runner()
    run.feed(pose())
    run.feed(pose(idx=0.1), frames=30)  # ~1 s
    run.feed(pose(idx=0.9), frames=3)
    assert run.events == [("down", "left"), ("up", "left")]


def test_losing_the_hand_mid_drag_releases_the_button():
    run = Runner()
    run.feed(pose())
    run.feed(pose(idx=0.1), frames=3)
    run.feed(pose(idx=0.1), pos=(650, 500))
    run.t += DT
    out = run.r.update(None, None, run.t)
    assert out.events == [("up", "left")] and out.state == IDLE


def test_thumb_to_middle_is_a_right_click():
    run = Runner()
    run.feed(pose(), frames=2)
    run.feed(pose(idx=0.8, mid=0.1), frames=4)
    run.feed(pose(idx=0.8, mid=0.9), frames=3)
    assert run.events == [("click", "right")]


def test_second_tap_soon_after_snaps_to_first_tap_spot():
    run = Runner()
    run.feed(pose())
    run.feed(pose(idx=0.1), frames=3)
    run.feed(pose(idx=0.9), frames=2)  # first click
    out = run.feed(pose(idx=0.45))  # starting second tap quickly
    assert out.snap_to_last_click


def test_tap_long_after_does_not_snap():
    run = Runner()
    run.feed(pose())
    run.feed(pose(idx=0.1), frames=3)
    run.feed(pose(idx=0.9), frames=30)  # 1 s later
    assert not run.feed(pose(idx=0.45)).snap_to_last_click


def test_peace_sign_and_move_up_scrolls_up():
    run = Runner()
    run.feed(pose(fingers=PEACE), pos=(500, 500))
    for y in range(500, 400, -5):  # hand moves up
        run.feed(pose(fingers=PEACE), pos=(500, y))
    assert run.out.state == SCROLL and run.out.freeze
    total = sum(e[1] for e in run.events if e[0] == "scroll")
    assert total > 0 and all(e[0] == "scroll" for e in run.events)


def test_scroll_ignores_tiny_jitter():
    run = Runner()
    for i in range(30):
        run.feed(pose(fingers=PEACE), pos=(500 + (i % 2) * 0.5, 500 - (i % 2) * 0.5))
    assert run.events == []


def test_scroll_ends_when_pose_ends():
    run = Runner()
    run.feed(pose(fingers=PEACE), frames=5)
    assert run.feed(pose(), frames=3).state == IDLE


def test_holding_a_fist_toggles_pause_once():
    run = Runner()
    run.feed(pose(fingers=FIST), frames=60)  # 2 s
    assert run.events == [("toggle_pause",)]


def test_short_fist_does_nothing():
    run = Runner()
    run.feed(pose(fingers=FIST), frames=20)
    run.feed(pose(), frames=5)
    assert run.events == []


class FakeBackend:
    def __init__(self):
        self.calls = []

    def button(self, which, down):
        self.calls.append(("button", which, down))

    def wheel(self, delta, horizontal=False):
        self.calls.append(("wheel", delta, horizontal))

    def key(self, name, down):
        self.calls.append(("key", name, down))


def test_dispatcher_sends_clicks_drags_and_scrolls():
    b = FakeBackend()
    d = Dispatcher(b, lambda: None)
    d.handle([("click", "left"), ("down", "left"), ("up", "left"), ("scroll", 60)], paused=False)
    assert b.calls == [
        ("button", "left", True),
        ("button", "left", False),
        ("button", "left", True),
        ("button", "left", False),
        ("wheel", 60, False),
    ]


def test_dispatcher_ignores_actions_when_paused_but_still_resumes():
    b = FakeBackend()
    toggled = []
    d = Dispatcher(b, lambda: toggled.append(1))
    d.handle([("click", "left"), ("toggle_pause",)], paused=True)
    assert b.calls == [] and toggled == [1]


def test_dispatcher_release_all_frees_a_stuck_button():
    b = FakeBackend()
    d = Dispatcher(b, lambda: None)
    d.handle([("down", "left")], paused=False)
    d.release_all()
    d.release_all()  # second call does nothing
    assert b.calls == [("button", "left", True), ("button", "left", False)]


def test_zoom_pose_zooms_with_hand_up_and_down():
    run = Runner()
    run.feed(pose(), frames=3)
    run.feed(pose(idx=0.1, mid=0.1), pos=(500.0, 500.0), frames=6)
    assert run.out.state == ZOOM and run.out.freeze
    for i in range(1, 11):  # hand moves up 5 units per picture
        run.feed(pose(idx=0.1, mid=0.1), pos=(500.0, 500.0 - 5 * i))
    ups = [e[1] for e in run.events if e[0] == "zoom"]
    assert ups and all(d > 0 for d in ups)
    run.events.clear()
    for i in range(1, 11):  # then down
        run.feed(pose(idx=0.1, mid=0.1), pos=(500.0, 450.0 + 5 * i))
    downs = [e[1] for e in run.events if e[0] == "zoom"]
    assert downs and all(d < 0 for d in downs)


def test_zoom_ends_when_fingers_open_and_no_click_after_real_zoom():
    run = Runner()
    run.feed(pose(idx=0.1, mid=0.1), frames=6)
    for i in range(1, 30):
        run.feed(pose(idx=0.1, mid=0.1), pos=(500.0, 500.0 - 5 * i))
    run.feed(pose(), frames=5)
    assert run.out.state == IDLE
    assert ("click", "left") not in run.events


def test_quick_pinch_with_middle_close_still_clicks():
    run = Runner()
    run.feed(pose(), frames=3)
    run.feed(pose(idx=0.1, mid=0.1), frames=5)  # ~170 ms, no movement
    run.feed(pose(), frames=4)
    assert run.events == [("click", "left")]


def test_dispatcher_zoom_is_ctrl_wheel_and_releases_ctrl():
    b = FakeBackend()
    Dispatcher(b, lambda: None).handle([("zoom", 40)], paused=False)
    assert b.calls == [("key", "ctrl", True), ("wheel", 40, False), ("key", "ctrl", False)]
