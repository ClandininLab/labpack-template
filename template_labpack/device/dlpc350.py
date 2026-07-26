# ref: https://github.com/SivyerLab/pyCrafter4500

import platform
import time
import hid
from math import floor


def clamp(x, min, max):
    if x < min:
        return min
    elif x > max:
        return max
    else:
        return x



class DLPC350:
    def __init__(self, device, timeout=10, poll_period=0.1):
        """
        :param device: HIDAPI device corresponding to the Lightcrafter unit
        :param timeout: Time to wait (in seconds) when polling a register status
        :param poll_period: Delay (in seconds) between polls of a register status
        """

        # save settings
        self.device = device
        self.timeout = timeout
        self.poll_period = poll_period

    def command(self, mode, cmd2, cmd3, data=None):
        # set defaults
        if data is None:
            data = []

        # build up command
        command = []

        command.append(0)               # report ID = 0
        command.append(mode)            # read/write
        command.append(0)               # sequence number = 0
        command.append(2+len(data))     # length LSB
        command.append(0)               # length MSB
        command.append(cmd3)            # CMD3
        command.append(cmd2)            # CMD2
        command.extend(data)            # data

        # add padding
        command.extend([0]*(65-len(command)))

        # run command
        self.device.write(command)

    def write(self, cmd2, cmd3, data=None):
        # send command
        self.command(mode=0x40, cmd2=cmd2, cmd3=cmd3, data=data)

        # read response
        resp = self.device.read(64)

        # check response
        assert resp[0] == 0x40
        assert resp[1] == 0
        assert resp[4] == cmd3
        assert resp[5] == cmd2

    def read(self, cmd2, cmd3):
        # send command
        resp = self.command(mode=0xC0, cmd2=cmd2, cmd3=cmd3)

        # read response
        resp = self.device.read(64)

        # check response
        assert resp[0] == 0xC0
        assert resp[1] == 0

        # return data
        bytes = resp[2]
        return resp[4:(4+bytes)]

    def play_sequence(self):
        self.write(cmd2=0x1a, cmd3=0x24, data=[0x02])

    def stop_sequence(self):
        # write the state
        self.write(cmd2=0x1a, cmd3=0x24, data=[0x00])

        # poll the sequence state register
        start_time = time.time()
        while (time.time() - start_time) < self.timeout:
            resp = self.read(cmd2=0x1a, cmd3=0x24)[0]

            if resp == 0x00:
                break
            else:
                time.sleep(self.poll_period)
                continue
        else:
            raise Exception('Timed out waiting for sequence to stop.')

    def validate(self, allow_post_vector_warning=True):
        # start validation
        self.write(cmd2=0x1a, cmd3=0x1a, data=[0x00])

        # poll the validation register
        start_time = time.time()
        while (time.time() - start_time) < self.timeout:
            resp = self.read(cmd2=0x1a, cmd3=0x1a)[0]

            if ((resp >> 7) & 1) == 1:
                # if bit 7 is set, it means that validation is still ongoing
                time.sleep(self.poll_period)
                continue
            elif resp == 0:
                # "0" means no errors
                break
            elif (resp == 8) and allow_post_vector_warning:
                # "8" means that a post vector was not inserted.  But that's expected when there is no
                # black period following a pattern.
                break
            else:
                raise Exception('Invalid configuration')
        else:
            raise Exception('Timed out waiting for pattern sequence validation.')

    # Which 8-bit slice of the incoming 24-bit frame each pattern number selects.
    # DLPC350 Programmer's Guide (DLPU010G) Table 2-70, "Pattern Number Mapping", 8-BIT column:
    #     0 -> G7..G0     1 -> R7..R0     2 -> B7..B0
    # so at 8-bit depth there are exactly three patterns in a frame, one per colour channel.
    EIGHT_BIT_PATTERNS = {'green': 0, 'red': 1, 'blue': 2}

    # Named LED combinations, Table 2-69 byte 1 bits 6:4 (b0 red, b1 green, b2 blue).
    # The guide names these directly: b101 = "Magenta (blue + red)", b111 = "White", and so on.
    LED_COMBINATIONS = {
        'none': (), 'red': ('red',), 'green': ('green',), 'blue': ('blue',),
        'yellow': ('red', 'green'), 'magenta': ('red', 'blue'), 'cyan': ('green', 'blue'),
        'white': ('red', 'green', 'blue'),
    }
    LED_BITS = {'red': 0x10, 'green': 0x20, 'blue': 0x40}

    # Trigger types, Table 2-69 byte 0 bits 1:0.
    TRIGGER_EXTERNAL_POSITIVE = 0b01
    TRIGGER_CONTINUE = 0b11          # "no input trigger (continue from previous)"

    def pattern_mode(self, fps=60, red=False, green=False, blue=True, channels=('blue',),
                     leds=None):
        """Put the projector in video-pattern mode.

        Two independent things are being chosen here, and they are easy to confuse because both are
        named after colours:

          `leds`     which LEDs light the DMD -- the colour the animal sees
          `channels` which colour channels of the video frame are read as successive patterns --
                     data, not colour

        They are not coupled. Displaying the red channel does not require the red LED, and under
        multiplexing it usually should not: each channel is a slice of time, and every slice is lit
        the same way. Magenta at 360 Hz is leds='magenta' with all three channels:

            pattern_mode(fps=120, leds='magenta', channels=('red', 'green', 'blue'))

        Each 8-bit channel becomes a separate pattern, so a 120 Hz video link drives the DMD at
        360 Hz. Pass one channel (the default) for the original single-pattern behaviour.

        :param fps: rate of the incoming video link, e.g. 120
        :param leds: 'magenta', 'white', 'blue', ... or an iterable like ('red', 'blue'). Overrides
            the red/green/blue flags, which are kept for the calls that already use them.
        :param red/green/blue: the older way of choosing LEDs, one flag each.
        :param channels: which channels to display, in the order they should appear. The renderer
            packs the earliest timepoint into channels[0], so this and stimpack's
            Screen(subframe_channel_order=...) describe the same decision from either end and have
            to agree.
        """
        if leds is not None:
            if isinstance(leds, str):
                if leds not in self.LED_COMBINATIONS:
                    raise ValueError(f'unknown LED combination {leds!r}; expected one of '
                                     f'{sorted(self.LED_COMBINATIONS)}, or an iterable of colours')
                chosen = self.LED_COMBINATIONS[leds]
            else:
                chosen = tuple(leds)
                unknown = [c for c in chosen if c not in self.LED_BITS]
                if unknown:
                    raise ValueError(f'unknown LED(s) {unknown}; expected some of '
                                     f'{sorted(self.LED_BITS)}')
            red, green, blue = ('red' in chosen, 'green' in chosen, 'blue' in chosen)
        if not channels:
            raise ValueError('channels must name at least one of green, red, blue')
        unknown = [c for c in channels if c not in self.EIGHT_BIT_PATTERNS]
        if unknown:
            raise ValueError(f'unknown channel(s) {unknown}; expected some of '
                             f'{sorted(self.EIGHT_BIT_PATTERNS)}')
        if len(set(channels)) != len(channels):
            raise ValueError(f'each channel can appear once; got {channels}')

        # stop sequence mode
        self.stop_sequence()

        # set display to pattern mode
        self.write(cmd2=0x1a, cmd3=0x1b, data=[0x01])

        # pattern data streamed over video
        self.write(cmd2=0x1a, cmd3=0x22, data=[0x00])

        # pattern LUT control (Table 2-65): entries-1, repeat, patterns-to-display-1, unused
        self.write(cmd2=0x1a, cmd3=0x31,
                   data=[len(channels) - 1, 0x01, len(channels) - 1, 0x00])

        # select VSYNC as trigger source
        self.write(cmd2=0x1a, cmd3=0x23, data=[0x00])

        # Exposure and frame period (Table 2-63). The guide is explicit that in external video input
        # pattern modes the exposure must equal the frame period, and here that period is per
        # *pattern*: three patterns inside one 120 Hz video frame each last 1/360 s.
        period_us = int(floor(1e6 / (fps * len(channels))))
        time_data = [(period_us >> shift) & 0xff for shift in [0, 8, 16, 24]]
        self.write(cmd2=0x1a, cmd3=0x29, data=(time_data + time_data))

        # open mailbox
        self.write(cmd2=0x1a, cmd3=0x33, data=[0x02])

        # set mailbox offset
        self.write(cmd2=0x1a, cmd3=0x32, data=[0x00])

        # write LUT data, three bytes per pattern (Table 2-69)

        # build up the LED code: 8-bit depth in bits 3:0, LED select in bits 6:4
        led_code = 8
        if red:
            led_code |= self.LED_BITS['red']
        if green:
            led_code |= self.LED_BITS['green']
        if blue:
            led_code |= self.LED_BITS['blue']

        for index, channel in enumerate(channels):
            # Only the first pattern waits for VSYNC; the rest follow on immediately inside the same
            # video frame. Triggering each on VSYNC would give one pattern per frame, three times
            # over, which is the failure that looks like it works.
            trigger = self.TRIGGER_EXTERNAL_POSITIVE if index == 0 else self.TRIGGER_CONTINUE
            pattern_number = self.EIGHT_BIT_PATTERNS[channel]
            byte0 = (pattern_number << 2) | trigger

            # 0x04 == trigger out 1 frames pattern, perform buffer swap, do not insert post pattern,
            # do not invert pattern. Only the last pattern of a frame swaps buffers.
            byte2 = 0x04 if index == len(channels) - 1 else 0x00

            self.write(cmd2=0x1a, cmd3=0x34, data=[byte0, led_code, byte2])

        # close mailbox
        self.write(cmd2=0x1a, cmd3=0x33, data=[0x00])

        # run validation
        self.validate()

        # start pattern mode
        self.play_sequence()
        time.sleep(0.1)
        self.play_sequence()

    def set_current(self, red=0.0, green=0.0, blue=0.0):
        # compute PWM control codes
        red_code, green_code, blue_code = self.currents_to_codes(red=red, green=green, blue=blue)

        # send codes to part
        self.write(cmd2=0x0b, cmd3=0x01, data=[red_code, green_code, blue_code])

    def currents_to_codes(self, red=0.0, green=0.0, blue=0.0):
        # sanity check
        assert red+green+blue < 4.3, 'The sum of red, green, and blue currents is too high.'

        # compute codes
        # the "255-x" computation is to account for apparent
        # inversion of PWM on the LCR4500 board
        red_code = 255-int(floor((red-0.4495)/0.0175))
        green_code = 255-int(floor((green-0.3587)/0.0181))
        blue_code = 255-int(floor((blue-0.1529)/0.0160))

        # limit values to 0-255
        red_code = clamp(red_code, 0, 255)
        green_code = clamp(green_code, 0, 255)
        blue_code = clamp(blue_code, 0, 255)

        # return codes
        return red_code, green_code, blue_code

def make_dlpc350_objects() -> list[DLPC350]:
    """
    Returns a list of DLPC350 objects corresponding to the connected Lightcrafter 4500 units.
    """

    dlpc350_objects = []

    for d in hid.enumerate():
        if d['product_string'] != 'DLPC350':
            continue

        if platform.system() == 'Windows':
            if d['usage'] != 65280:
                continue
            if d['usage_page'] != 65280:
                continue
        elif platform.system() == 'Linux':
            path = d['path'].decode('utf-8')
            if path[-1:] != '0':
                continue

        device = hid.device()
        device.open_path(d['path'])
        dlpc350_objects.append(DLPC350(device=device))

    return dlpc350_objects

