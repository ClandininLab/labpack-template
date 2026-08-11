"""What pattern_mode actually sends to a DLPC350.

No projector required: the driver is stubbed and the byte sequence is checked against the
DLPC350 Programmer's Guide (DLPU010G). That covers the part that can be got wrong silently --
a LUT whose fields are in the wrong bits still validates and still plays, it just displays
something other than what was meant.

Reference tables:
  2-63  Pattern Display Exposure and Frame Period
  2-65  Pattern Display LUT Control
  2-69  Pattern Display LUT Data: Pattern Definition
  2-70  Pattern Number Mapping (8-bit column: 0 -> green, 1 -> red, 2 -> blue)
"""
import sys
import types
from unittest import mock

import pytest

# hid is only present on a machine with the projector attached, and importing the driver needs it.
sys.modules.setdefault('hid', types.ModuleType('hid'))

from template_labpack.device.dlpc350 import DLPC350  # noqa: E402


@pytest.fixture
def projector():
    """A DLPC350 that records the commands it would send instead of sending them."""
    device = mock.MagicMock()
    dlpc = DLPC350(device=device)
    dlpc.writes = []
    dlpc.write = lambda cmd2, cmd3, data=None: dlpc.writes.append((cmd2, cmd3, list(data or [])))
    dlpc.stop_sequence = lambda: None
    dlpc.play_sequence = lambda: None
    dlpc.validate = lambda: None
    return dlpc


def commands(projector, cmd3):
    return [data for _cmd2, c3, data in projector.writes if c3 == cmd3]


def lut_entries(projector):
    return commands(projector, 0x34)


def decode(entry):
    """Split a LUT entry into its documented fields (Table 2-69)."""
    byte0, byte1, byte2 = entry
    return {
        'trigger': byte0 & 0b11,
        'pattern_number': (byte0 >> 2) & 0b111111,
        'bit_depth': byte1 & 0b1111,
        'led_select': (byte1 >> 4) & 0b111,
        'buffer_swap': bool(byte2 & 0x04),
    }


# --- the single-pattern case, which is what the rigs run today -----------------------------------

def test_one_channel_reproduces_the_original_configuration(projector):
    """The default has to keep behaving exactly as before, or every rig changes when this lands."""
    projector.pattern_mode(fps=120, red=False, green=False, blue=True)

    assert commands(projector, 0x31) == [[0, 0x01, 0, 0]], 'one LUT entry, one pattern, repeating'
    entries = lut_entries(projector)
    assert len(entries) == 1
    assert entries[0] == [0x09, 0x48, 0x04], 'the bytes the rigs have been sending'
    assert decode(entries[0]) == {'trigger': 0b01, 'pattern_number': 2, 'bit_depth': 8,
                                  'led_select': 4, 'buffer_swap': True}


def test_one_pattern_gets_the_whole_video_frame(projector):
    """Exposure and period are equal, as the guide requires for video-streamed pattern modes."""
    projector.pattern_mode(fps=120, channels=('blue',))
    exposure, period = split_timing(commands(projector, 0x29)[0])
    assert exposure == period == pytest.approx(1e6 / 120, abs=1)


# --- three patterns per frame --------------------------------------------------------------------

def split_timing(data):
    """Table 2-63: four bytes of exposure then four of frame period, little-endian microseconds."""
    value = lambda b: b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)   # noqa: E731
    return value(data[:4]), value(data[4:])


def test_three_channels_ask_for_three_patterns(projector):
    projector.pattern_mode(fps=120, channels=('green', 'red', 'blue'))

    assert commands(projector, 0x31) == [[2, 0x01, 2, 0]], \
        'entries-1 and patterns-1 must both be 2 for three patterns per frame'
    assert len(lut_entries(projector)) == 3


def test_each_pattern_reads_the_channel_it_was_asked_for(projector):
    """Table 2-70, 8-bit column: pattern 0 is green, 1 is red, 2 is blue."""
    projector.pattern_mode(fps=120, channels=('green', 'red', 'blue'))
    assert [decode(e)['pattern_number'] for e in lut_entries(projector)] == [0, 1, 2]

    projector.writes.clear()
    projector.pattern_mode(fps=120, channels=('blue', 'green', 'red'))
    assert [decode(e)['pattern_number'] for e in lut_entries(projector)] == [2, 0, 1], \
        'the display order is ours to choose; it must follow the order asked for'


def test_only_the_first_pattern_waits_for_vsync(projector):
    """Every pattern triggering on VSYNC would give one pattern per frame, three times over --
    which plays, validates, and looks like it works."""
    projector.pattern_mode(fps=120, channels=('green', 'red', 'blue'))
    triggers = [decode(e)['trigger'] for e in lut_entries(projector)]

    assert triggers[0] == DLPC350.TRIGGER_EXTERNAL_POSITIVE
    assert triggers[1:] == [DLPC350.TRIGGER_CONTINUE] * 2, \
        'later patterns must continue from the previous one, not wait for another VSYNC'


def test_three_patterns_share_the_video_frame(projector):
    """1/360 s each inside a 120 Hz frame, and exposure equals period as the guide requires."""
    projector.pattern_mode(fps=120, channels=('green', 'red', 'blue'))
    exposure, period = split_timing(commands(projector, 0x29)[0])

    assert exposure == period, 'video-streamed pattern modes require exposure == frame period'
    assert exposure == pytest.approx(1e6 / 360, abs=1), f'{exposure} us, expected {1e6/360:.0f}'


def test_buffer_swap_happens_once_per_video_frame(projector):
    """Swapping after every pattern would fetch a new video frame three times per frame."""
    projector.pattern_mode(fps=120, channels=('green', 'red', 'blue'))
    swaps = [decode(e)['buffer_swap'] for e in lut_entries(projector)]
    assert swaps == [False, False, True]


def test_every_pattern_is_lit_the_same_way(projector):
    """Each channel is a slice of time, not a color, so they must all use the same LED."""
    projector.pattern_mode(fps=120, red=False, green=False, blue=True,
                           channels=('green', 'red', 'blue'))
    led_selects = {decode(e)['led_select'] for e in lut_entries(projector)}
    assert led_selects == {4}, f'patterns lit differently: {led_selects}'


def test_bit_depth_is_eight_for_every_pattern(projector):
    projector.pattern_mode(fps=120, channels=('green', 'red', 'blue'))
    assert {decode(e)['bit_depth'] for e in lut_entries(projector)} == {8}


@pytest.mark.parametrize('channels, reason', [
    ((), 'no channels'),
    (('purple',), 'not a channel'),
    (('red', 'red'), 'repeated'),
])
def test_nonsense_channel_lists_are_rejected(projector, channels, reason):
    with pytest.raises(ValueError):
        projector.pattern_mode(fps=120, channels=channels)


# --- fewer than three, for a rig with two usable LEDs or one wanting a longer exposure ------------

def test_two_channels_split_the_frame_in_two(projector):
    """Three is the ceiling, not the only option: the LUT and the timing follow len(channels)."""
    projector.pattern_mode(fps=120, channels=('red', 'green'))

    assert commands(projector, 0x31) == [[1, 0x01, 1, 0]], 'two entries, two patterns per frame'
    entries = lut_entries(projector)
    assert len(entries) == 2
    assert [decode(e)['pattern_number'] for e in entries] == [1, 0]
    assert [decode(e)['buffer_swap'] for e in entries] == [False, True]

    exposure, period = split_timing(commands(projector, 0x29)[0])
    assert exposure == period == pytest.approx(1e6 / 240, abs=1)


# --- keeping the projector and the renderer in step -----------------------------------------------

@pytest.mark.parametrize('subframes, order, expected', [
    (3, (0, 1, 2), ['red', 'green', 'blue']),
    (3, (2, 0, 1), ['blue', 'red', 'green']),
    (2, (2, 1, 0), ['blue', 'green']),
])
def test_the_renderer_and_the_projector_agree_on_the_order(projector, subframes, order, expected):
    """The permutation is one decision held in two vocabularies -- stimpack in channel indices,
    because a color write mask is positional, and the projector takes names. Transposing them
    reorders timepoints in time and raises nothing, since scrambled motion is still motion, so
    the rig derives one from the other and this checks they meet.
    """
    screen_module = pytest.importorskip('stimpack.visual_stim.screen')
    if not hasattr(screen_module.Screen, 'subframe_channel_names'):
        pytest.skip('stimpack predates Screen.subframe_channel_names')
    screen = screen_module.Screen(subframes=subframes, refresh_rate=120,
                                  subframe_channel_order=order)

    projector.pattern_mode(fps=120, channels=screen.subframe_channel_names())

    by_number = {number: name for name, number in DLPC350.EIGHT_BIT_PATTERNS.items()}
    displayed = [by_number[decode(e)['pattern_number']] for e in lut_entries(projector)]

    written = [screen_module.CHANNEL_NAMES[i]
               for mask in screen.subframe_color_masks()
               for i, writable in enumerate(mask[:3]) if writable]

    assert displayed == written == expected


# --- choosing the illumination -------------------------------------------------------------------

def test_magenta_at_360_hz(projector):
    """The case this API exists to make sayable: two LEDs on, all three channels as time slices.

    Note the two are independent. Displaying the green channel does not need the green LED -- under
    multiplexing a channel is a slice of time, and every slice is lit the same way.
    """
    projector.pattern_mode(fps=120, leds='magenta', channels=('red', 'green', 'blue'))

    entries = lut_entries(projector)
    assert len(entries) == 3
    assert {decode(e)['led_select'] for e in entries} == {0b101}, \
        "Table 2-69 names b101 'Magenta (blue + red)'"
    exposure, period = split_timing(commands(projector, 0x29)[0])
    assert exposure == period == pytest.approx(1e6 / 360, abs=1)


@pytest.mark.parametrize('name, expected', [
    ('none', 0b000), ('red', 0b001), ('green', 0b010), ('yellow', 0b011),
    ('blue', 0b100), ('magenta', 0b101), ('cyan', 0b110), ('white', 0b111),
])
def test_every_named_combination_matches_the_guide(projector, name, expected):
    """Table 2-69 byte 1 bits 6:4 spells these out; b0 = red, b1 = green, b2 = blue."""
    projector.pattern_mode(fps=120, leds=name)
    assert decode(lut_entries(projector)[0])['led_select'] == expected


def test_leds_can_also_be_given_as_a_list(projector):
    projector.pattern_mode(fps=120, leds=('red', 'blue'))
    assert decode(lut_entries(projector)[0])['led_select'] == 0b101


def test_leds_overrides_the_older_flags(projector):
    """server/ still passes red=/green=/blue=, so both have to work, with leds winning."""
    projector.pattern_mode(fps=120, red=False, green=True, blue=False, leds='magenta')
    assert decode(lut_entries(projector)[0])['led_select'] == 0b101


def test_the_old_flags_still_work_on_their_own(projector):
    projector.pattern_mode(fps=120, red=True, green=False, blue=True)
    assert decode(lut_entries(projector)[0])['led_select'] == 0b101


def test_illumination_and_channels_are_independent(projector):
    """A channel is data, not color: showing the red channel under a blue LED is normal."""
    projector.pattern_mode(fps=120, leds='blue', channels=('red',))
    entry = decode(lut_entries(projector)[0])
    assert entry['pattern_number'] == 1, 'pattern 1 reads R7..R0'
    assert entry['led_select'] == 0b100, 'lit by blue'


@pytest.mark.parametrize('leds', ['purple', ('red', 'ultraviolet')])
def test_unknown_leds_are_rejected(projector, leds):
    with pytest.raises(ValueError):
        projector.pattern_mode(fps=120, leds=leds)
