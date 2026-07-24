"""Example rig server -- copy this per rig and edit it to describe that rig's hardware.

A "rig server" describes one physical setup (its screens' geometry, its locomotion tracker, its DAQ)
and then runs the socket server that a client/GUI connects to.

Run it directly:      python server/example_server.py
Or point a config at it:  rig_config.<rig>.server_options.local_server_path: server/example_server.py
"""
import os
import sys

from stimpack.device.locomotion.loco_managers.keytrac_managers import KeytracClosedLoopManager
from stimpack.util import ROOT_DIR
from stimpack.visual_stim.screen import Screen, SubScreen

from base_server import BaseServer


class ExampleServer(BaseServer):
    pass  # add rig-specific behavior here; screen geometry is defined below, outside the class


# Screen geometry is a property of the rig, not of the server object, so it lives here as a plain
# function rather than a method (see todo.txt).
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

    # # # Locomotion (optional) # # #
    # KeyTrac is a keyboard-driven stand-in for a real tracker -- handy for testing without hardware.
    # For a real rig, swap in your own LocoClosedLoopManager subclass (e.g. a FicTrac manager) and
    # give it that tracker's host/port.
    loco_class = KeytracClosedLoopManager
    loco_kwargs = {
        'host': '127.0.0.1',
        'port': 33335,
        'python_bin': sys.executable,
        'kt_py_fn': os.path.join(ROOT_DIR, 'device', 'locomotion', 'keytrac', 'keytrac.py'),
        'relative_control': True,
    }

    # # # DAQ (optional) # # #
    # Set daq_class to a DAQ subclass from labpack/device/daq.py (e.g. NIUSB6001, LabJackTSeries)
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

    # Start the server loop (blocks).
    server.loop()


if __name__ == '__main__':
    main()
