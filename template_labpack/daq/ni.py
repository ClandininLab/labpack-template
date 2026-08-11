#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""National Instruments USB DAQs.

NOTE: nidaqmx is imported inside the methods that use it, not up here. Stimpack imports the daq
module on every client start -- before it knows whether the rig config names a trigger at all --
so a module-level vendor import would crash the client on any machine without NI drivers
installed (a laptop, or a rig with only the other vendor's hardware). The extras are per rig on
purpose: pip install -e .[nidaq].
"""
from stimpack import daq


class NIUSB6001(daq.DAQ):
    """
    https://www.ni.com/en-us/support/model.usb-6001.html
    """
    def __init__(self, dev='Dev1', trigger_channel='port2/line0'):
        super().__init__()  # call the parent class init method
        self.dev = dev
        self.trigger_channel = trigger_channel

    def send_trigger(self):
        import nidaqmx  # local so machines without NI drivers can still import this module
        with nidaqmx.Task() as task:
            task.do_channels.add_do_chan('{}/{}'.format(self.dev, self.trigger_channel))
            task.start()
            task.write([True, False])


class NIUSB6210(daq.DAQ):
    """
    https://www.ni.com/en-us/support/model.usb-6210.html
    """
    def __init__(self, dev='Dev5', trigger_channel='ctr0'):
        super().__init__()  # call the parent class init method
        self.dev = dev
        self.trigger_channel = trigger_channel

    def send_trigger(self):
        import nidaqmx  # local so machines without NI drivers can still import this module
        with nidaqmx.Task() as task:
            task.co_channels.add_co_pulse_chan_time('{}/{}'.format(self.dev, self.trigger_channel),
                                                    low_time=0.002,
                                                    high_time=0.001)
            task.start()

    def output_step(self, output_channel='ctr1', low_time=0.001, high_time=0.100, initial_delay=0.00):
        import nidaqmx  # local so machines without NI drivers can still import this module
        with nidaqmx.Task() as task:
            task.co_channels.add_co_pulse_chan_time('{}/{}'.format(self.dev, output_channel),
                                                    low_time=low_time,
                                                    high_time=high_time,
                                                    initial_delay=initial_delay)

            task.start()
            task.wait_until_done()
            task.stop()
