"""Settings, free/paid plans, license keys, dispatcher switches."""

import json
import os
from datetime import date

import pytest

from vision_ai.actions.dispatcher import Dispatcher
from vision_ai.config import settings as st
from vision_ai.licensing import ed25519, license
from vision_ai.licensing.features import GESTURES, allowed_ids, gesture_for_event

SECRET = bytes(range(32))
PUB = ed25519.public_key(SECRET).hex()


# --- ed25519 against the official test vector (RFC 8032, test 1) -----------------------


def test_ed25519_matches_rfc8032_test_vector():
    sec = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    assert ed25519.public_key(sec).hex() == (
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    )
    sig = ed25519.sign(sec, b"")
    assert sig.hex() == (
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e3970"
        "1cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )
    assert ed25519.verify(ed25519.public_key(sec), b"", sig)
    assert not ed25519.verify(ed25519.public_key(sec), b"x", sig)


# --- license keys ----------------------------------------------------------------------


def test_good_key_is_paid():
    key = license.make_key(SECRET, "pro", "a@b.com")
    info = license.check(key, public_hex=PUB)
    assert info.valid and info.paid and info.who == "a@b.com"


def test_owner_key_is_paid_and_spaces_in_pasted_key_are_ok():
    key = license.make_key(SECRET, "owner", "me")
    spaced = key[:20] + " \n " + key[20:]
    assert license.check(spaced, public_hex=PUB).paid


def test_tampered_key_is_rejected():
    key = license.make_key(SECRET, "pro", "a@b.com")
    bad = key[:-3] + ("AAA" if not key.endswith("AAA") else "BBB")
    assert not license.check(bad, public_hex=PUB).valid
    assert not license.check("VAI1.NOTAKEY", public_hex=PUB).valid
    assert not license.check("hello", public_hex=PUB).valid


def test_key_signed_by_someone_else_is_rejected():
    other = license.make_key(bytes(range(1, 33)), "pro", "x")
    assert not license.check(other, public_hex=PUB).valid


def test_expired_key_is_rejected_with_reason():
    key = license.make_key(SECRET, "pro", "a", expires="2026-01-01")
    info = license.check(key, today=date(2026, 6, 1), public_hex=PUB)
    assert not info.valid and "expired" in info.reason
    assert license.check(key, today=date(2025, 12, 31), public_hex=PUB).valid


def test_empty_key_is_free_and_no_public_key_never_unlocks():
    assert not license.check("", public_hex=PUB).paid
    key = license.make_key(SECRET, "pro", "a")
    assert not license.check(key, public_hex="").paid


# --- plans -----------------------------------------------------------------------------


def test_free_plan_has_the_four_basic_gestures_paid_has_all():
    free = allowed_ids(paid=False)
    assert free == {"move", "tap", "scroll", "pause"}
    assert allowed_ids(paid=True) == {g.id for g in GESTURES}


def test_user_can_switch_off_gestures_but_not_move():
    ids = allowed_ids(paid=True, user_off={"drag", "move"})
    assert "drag" not in ids and "move" in ids


def test_events_map_to_gestures():
    assert gesture_for_event(("click", "left")) == "tap"
    assert gesture_for_event(("click", "right")) == "right_click"
    assert gesture_for_event(("hscroll", 5)) == "scroll"
    assert gesture_for_event(("home",)) == "home"
    assert gesture_for_event(("zoom2", 5)) == "two_hand_zoom"


class Fake:
    def __init__(self):
        self.calls = []

    def button(self, which, down):
        self.calls.append(("button", which, down))

    def wheel(self, delta, horizontal=False):
        self.calls.append(("wheel", delta, horizontal))

    def key(self, name, down):
        self.calls.append(("key", name, down))


def test_dispatcher_skips_gestures_not_allowed():
    b = Fake()
    d = Dispatcher(b, lambda: None, allowed=lambda g: g in {"tap", "pause"})
    d.handle([("click", "right"), ("scroll", 5), ("zoom", 5), ("click", "left")], paused=False)
    assert b.calls == [("button", "left", True), ("button", "left", False)]


def test_denied_drag_still_ends_as_a_click():
    b = Fake()
    d = Dispatcher(b, lambda: None, allowed=lambda g: g == "tap")
    d.handle([("down", "left"), ("up", "left")], paused=False)
    assert b.calls == [("button", "left", True), ("button", "left", False)]
    assert not d.left_down


def test_resume_from_pause_always_works_even_if_pause_gesture_is_off():
    toggled = []
    d = Dispatcher(Fake(), lambda: toggled.append(1), allowed=lambda g: False)
    d.handle([("toggle_pause",)], paused=True)
    d.handle([("toggle_pause",)], paused=False)  # pausing needs the gesture
    assert toggled == [1]


def test_home_presses_win_tab_and_releases_win():
    b = Fake()
    Dispatcher(b, lambda: None).handle([("home",)], paused=False)
    assert b.calls == [
        ("key", "win", True),
        ("key", "tab", True),
        ("key", "tab", False),
        ("key", "win", False),
    ]


def test_keys_are_released_even_if_the_wheel_fails():
    class Bad(Fake):
        def wheel(self, delta, horizontal=False):
            raise OSError("no")

    b = Bad()
    Dispatcher(b, lambda: None).handle([("zoom", 5)], paused=False)
    assert ("key", "ctrl", False) in b.calls


def test_on_event_called_only_for_events_that_ran():
    seen = []
    d = Dispatcher(
        Fake(), lambda: None, allowed=lambda g: g == "tap", on_event=lambda e: seen.append(e[0])
    )
    d.handle([("click", "left"), ("scroll", 3)], paused=False)
    assert seen == ["click"]


# --- settings --------------------------------------------------------------------------


def test_settings_round_trip_and_defaults(tmp_path):
    p = tmp_path / "s.json"
    assert st.load(p) == st.Settings()
    s = st.Settings(main_hand="left", smoothness=8, gestures_off=["drag"])
    st.save(s, p)
    assert st.load(p) == s


def test_broken_or_wrong_values_fall_back(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{not json", encoding="utf-8")
    assert st.load(p) == st.Settings()
    p.write_text(
        json.dumps({"main_hand": "up", "smoothness": 99, "mode": 5, "bogus": 1}), encoding="utf-8"
    )
    s = st.load(p)
    assert s.main_hand == "right" and s.smoothness == 10 and s.mode == "absolute"


def test_default_sliders_give_the_tuned_numbers():
    assert st.cursor_params(st.Settings()) == pytest.approx((1.0, 0.05))
    steady = st.cursor_params(st.Settings(smoothness=10))[0]
    assert steady < 1.0 < st.cursor_params(st.Settings(smoothness=1))[0]
    assert st.cursor_params(st.Settings(responsiveness=10))[1] > 0.05


def test_make_configs_applies_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    cam, trk, cur, _ = st.make_configs(st.Settings(camera_index=2, two_hand=True, main_hand="left"))
    assert cam.index == 2 and trk.num_hands == 2 and cur.main_hand == "left"
    assert os.path.isdir(tmp_path)


def test_autostart_command_points_at_this_program_in_background_mode():
    from vision_ai.platform import autostart

    cmd = autostart.command()
    assert cmd.endswith("--background") and cmd.startswith('"')


def test_platform_helpers_are_safe_off_windows():
    from vision_ai.platform import autostart, uipi

    assert autostart.is_enabled() is False and autostart.set_enabled(True) is False
    assert uipi.foreground_blocks_us() is False
