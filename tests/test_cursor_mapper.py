from vision_ai.gestures.cursor_mapper import CursorMapper, DeadZone, Rect

BOX = Rect(0.2, 0.25, 0.6, 0.6)
SCREEN = Rect(0, 0, 1920, 1080)


def test_box_corners_map_to_screen_corners():
    m = CursorMapper(BOX, SCREEN)
    assert m.unit_to_screen(*m.to_unit(0.2, 0.25)) == (0, 0)
    assert m.unit_to_screen(*m.to_unit(0.8, 0.85)) == (1919, 1079)


def test_centre_maps_to_centre():
    m = CursorMapper(BOX, SCREEN)
    x, y = m.unit_to_screen(*m.to_unit(0.5, 0.55))
    assert abs(x - 959.5) < 1 and abs(y - 539.5) < 1


def test_outside_box_is_clamped():
    m = CursorMapper(BOX, SCREEN)
    assert m.unit_to_screen(*m.to_unit(-1, 5)) == (0, 1079)


def test_negative_origin_for_monitor_on_the_left():
    m = CursorMapper(BOX, Rect(-1920, 0, 3840, 1080))
    assert m.unit_to_screen(0.0, 0.0)[0] == -1920
    assert m.unit_to_screen(1.0, 0.0)[0] == 1919


def test_dead_zone_ignores_small_moves():
    d = DeadZone(2.0)
    d(100, 100)
    assert d(101, 100) == (100, 100)


def test_dead_zone_follows_at_the_edge_without_jump():
    d = DeadZone(2.0)
    d(100, 100)
    x, y = d(110, 100)
    assert abs(x - 108) < 1e-9 and y == 100
