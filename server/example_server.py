"""Example rig server -- copy this per rig and edit it to describe that rig's hardware.

A "rig server" describes one physical setup (its screens' geometry, its locomotion tracker, its DAQ)
and then runs the socket server that a client/GUI connects to.

Run it directly:      python server/example_server.py
Or point a config at it:  rig_config.<rig>.server_options.local_server_path: server/example_server.py
"""

from stimpack.locomotion.keytrac import KeytracClosedLoopManager
from stimpack.visual_stim.screen import Screen, SubScreen

from base_server import BaseServer


class ExampleServer(BaseServer):
    pass  # add rig-specific behavior here; screen geometry is defined below, outside the class


# Screen geometry is a property of the rig, not of the server object, so it lives here as a plain
# function rather than a method.
# pa/pb/pc are the physical corners of the display in meters, relative to the subject at the origin:
# pa = lower-left, pb = lower-right, pc = upper-left, as seen by the subject. viewport_* place that
# face on the display device in normalized device coordinates, so several faces can share a display.
def get_subscreen(name: str) -> SubScreen:
    if name == 'aux':
        # A plain full-viewport screen for a laptop / operator display.
        viewport_ll = (-1.0, -1.0)
        viewport_width = 2.0
        viewport_height = 2.0
        pa = (-0.15, 0.15, -0.15)
        pb = (+0.15, 0.15, -0.15)
        pc = (-0.15, 0.15, +0.15)
    elif name == 'left':
        # Example of a second, angled face occupying the left half of a display.
        viewport_ll = (-1.0, -1.0)
        viewport_width = 1.0
        viewport_height = 2.0
        pa = (-0.15, 0.00, -0.15)
        pb = (-0.15, 0.30, -0.15)
        pc = (-0.15, 0.00, +0.15)
    else:
        raise ValueError(f'Invalid subscreen name: {name}')

    return SubScreen(pa=pa, pb=pb, pc=pc, viewport_ll=viewport_ll,
                     viewport_width=viewport_width, viewport_height=viewport_height)


def main():
    # # # Screens # # #
    # Add a Screen per physical display. Use fullscreen=True on the real stimulus display(s).
    aux_screen = Screen(subscreens=[get_subscreen('aux')],
                        display_index=0, fullscreen=False, vsync=True,
                        square_size=(0.25, 0.25), name='Aux')
    visual_stim_kwargs = {'screens': [aux_screen]}

    # # # Curved screen (optional) # # #
    # A hemisphere or cylinder screen lit by a projector cannot be described by flat SubScreens.
    # stimpack's curved path instead takes the screen surface's shape plus the projector's pose and
    # optics, and renders through a cube map. Uncomment on a rig with such a screen -- and replace
    # the numbers, which are stimpack's placeholders and describe no real rig: measure the
    # projector's position and read its throw ratio off its data sheet, then check the result with
    # stimpack.visual_stim.draw.draw_curved_screen().
    #
    # from stimpack.visual_stim.curved_screen import CurvedScreen, PinholeProjector, SphericalSurface
    #
    # surface = SphericalSurface(radius=0.15, elevation_range=(0, 90))     # an upper-hemisphere bowl
    # projector = PinholeProjector(position=(0, 0, 0.30),                  # meters, in the rig frame
    #                              throw_ratio=0.5, aspect_ratio=1.6)      # aimed at the origin by default
    # bowl_screen = CurvedScreen(surface=surface, projector=projector,
    #                            display_index=1, fullscreen=True, vsync=True, name='Bowl')
    # visual_stim_kwargs = {'screens': [aux_screen, bowl_screen]}
    #
    # Do NOT set horizontal_flip for rear projection here: that flag only reaches get_perspective,
    # which is the planar path, so on a curved screen it is silently inert -- and it is also not
    # needed, because the mesh carries, per vertex, both where the point lands in the projector
    # image and which direction it lies in from the subject, so rear projection is described
    # exactly by the geometry.

    # # # Locomotion (optional) # # #
    # KeyTrac is a keyboard-driven stand-in for a real tracker -- handy for testing without hardware.
    # For a real rig, swap in your own LocoClosedLoopManager subclass; a FicTrac example follows below.
    loco_class = KeytracClosedLoopManager
    loco_kwargs = {
        'host': '127.0.0.1',
        'port': 33335,
        # python_bin and kt_py_fn are omitted: the defaults are this interpreter and the app stimpack ships.
        'relative_control': True,
    }

    # FicTrac wiring, using this labpack's own manager (template_labpack/device/locomotion/).
    # Left commented because it launches the fictrac binary at the paths below, which only exist
    # on a machine with FicTrac installed. Uncomment on a rig that has one, replacing the two
    # paths, and delete the KeyTrac assignment above.
    #
    # from template_labpack.device.locomotion.loco_managers.fictrac_managers import FtClosedLoopManager
    #
    # loco_class = FtClosedLoopManager
    # loco_kwargs = {
    #     'host':             '127.0.0.1',
    #     'port':             33334,                              # must match out_port in the FicTrac config
    #     'ft_bin':           '/path/to/fictrac/bin/fictrac',
    #     'ft_config':        '/path/to/fictrac/config.txt',
    #     # Column indices into FicTrac's output lines, matching its data_header.txt: integrated
    #     # animal heading (theta) and integrated x/y position, plus frame counter and timestamp.
    #     # These are the columns _parse_line in fictrac_managers.py reads.
    #     'ft_theta_idx':     16,
    #     'ft_x_idx':         14,
    #     'ft_y_idx':         15,
    #     'ft_frame_num_idx': 0,
    #     'ft_timestamp_idx': 21,
    # }

    # # # DAQ (optional) # # #
    # Set daq_class to a DAQ subclass from template_labpack/device/daq.py (e.g. NIUSB6001, LabJackTSeries)
    # to send acquisition triggers / opto waveforms from this server.
    daq_class, daq_kwargs = None, {}

    # # # Server # # #
    # host: stimpack defaults to loopback (127.0.0.1) since the RPC channel is unauthenticated.
    # For a remote client, pass this rig's own network address and firewall the port.
    server = ExampleServer(host='127.0.0.1', port=60629,
                           visual_stim_kwargs=visual_stim_kwargs,
                           loco_class=loco_class, loco_kwargs=loco_kwargs,
                           daq_class=daq_class, daq_kwargs=daq_kwargs)

    # Register any server-side functions to be called from the client, e.g.
    #   manager.target('root').hello_server()
    server.register_function_on_root(lambda: print("Hello, Server! From Client"), "hello_server")

    # # # Subframe multiplexing (optional) # # #
    # A projector that reads a video frame's color channels as successive patterns turns a 120 Hz
    # link into a 240/360 Hz monochrome display. stimpack renders that; putting the projector into
    # the matching mode is this script's job, since which projector is attached is a property of the
    # rig. Full explanation, including the limits: stimpack's docs, "Subframe multiplexing".
    #
    # Left commented because template_labpack.device.dlpc350 imports `hid`, which is only installed
    # on a machine with the projector attached -- an import here would break this example server for
    # everyone else. Uncomment on a rig that has one.
    #
    # Register it as ONE function that sets both halves. Setting them separately is the mistake this
    # shape exists to prevent: when the projector and the renderer disagree, the result is not an
    # error but a plausible-looking wrong stimulus, and scrambled motion is still motion.
    #
    # from stimpack.visual_stim.screen import channel_names
    # from template_labpack.device.dlpc350 import make_dlpc350_objects
    #
    # dlpc350_objects = make_dlpc350_objects()
    #
    # def set_subframes(n, leds='white', channel_order=(0, 1, 2)):
    #     # channel_order is one permutation with two readings: the renderer takes channel indices,
    #     # because a color write mask is positional, and the projector takes names. Deriving one
    #     # from the other here is what stops them being transposed.
    #     channels = ('blue',) if n == 1 else channel_names(channel_order[:n])
    #     dlpc350_objects[0].pattern_mode(fps=120, channels=channels, leds=leds)
    #     for screen_manager in server.modules['visual'].screen_managers:
    #         screen_manager.set_subframes(n, channel_order=channel_order)
    #
    # server.register_function_on_root(set_subframes, "set_subframes")
    #
    # Call it from a protocol, between trials only, and guarded so protocols still run on rigs
    # without a projector:
    #     if self.has_server_function('set_subframes'):
    #         self.manager.target('root').set_subframes(3)
    #
    # Then commission the rig with stimpack's SubframeTimingCheck protocol and a high-speed camera
    # or a photodiode on the corner square. Nothing in software can check that the projector is
    # really unpacking the patterns.

    # Start the server loop (blocks).
    server.loop()


if __name__ == '__main__':
    main()
