#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional

from stimpack.device import daq
from stimpack.rpc.multicall import MyMultiCall

import nidaqmx

from labjack import ljm
import numpy as np
import time
import threading

# %%
class DAQonServer(daq.DAQonServer):
    '''
    Dummy DAQ class for when the DAQ resides on the server, so that we can call methods as if the DAQ is on the client side.

    Calls are addressed to the server's 'daq' module with target('daq'), so the method names here are
    just the driver's own method names (e.g. LabJackTSeries.start_stream). Note the older style --
    an untargeted call to a "daq_"-prefixed name -- no longer works: untargeted requests are routed
    to the server's root node, where those names are not registered, so they would silently do nothing.
    '''
    def setup_pulse_wave_stream_out(self, multicall:Optional[MyMultiCall]=None, **kwargs):
        if multicall is not None and isinstance(multicall, MyMultiCall):
            multicall.target('daq').setup_pulse_wave_stream_out(**kwargs)
            return multicall
        if self.manager is not None:
            self.manager.target('daq').setup_pulse_wave_stream_out(**kwargs)

    def start_stream(self, multicall:Optional[MyMultiCall]=None, **kwargs):
        if multicall is not None and isinstance(multicall, MyMultiCall):
            multicall.target('daq').start_stream(**kwargs)
            return multicall
        if self.manager is not None:
            self.manager.target('daq').start_stream(**kwargs)

    def stop_stream(self, multicall:Optional[MyMultiCall]=None, **kwargs):
        if multicall is not None and isinstance(multicall, MyMultiCall):
            multicall.target('daq').stop_stream(**kwargs)
            return multicall
        if self.manager is not None:
            self.manager.target('daq').stop_stream(**kwargs)

    def stream_with_timing(self, multicall:Optional[MyMultiCall]=None, **kwargs):
        if multicall is not None and isinstance(multicall, MyMultiCall):
            multicall.target('daq').stream_with_timing(**kwargs)
            return multicall
        if self.manager is not None:
            self.manager.target('daq').stream_with_timing(**kwargs)


# %% National instruments USB daqs
class NIUSB6001(daq.DAQ):
    """
    https://www.ni.com/en-us/support/model.usb-6001.html
    """
    def __init__(self, dev='Dev1', trigger_channel='port2/line0'):
        super().__init__()  # call the parent class init method
        self.dev = dev
        self.trigger_channel = trigger_channel

    def send_trigger(self):
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
        with nidaqmx.Task() as task:
            task.co_channels.add_co_pulse_chan_time('{}/{}'.format(self.dev, self.trigger_channel),
                                                    low_time=0.002,
                                                    high_time=0.001)
            task.start()

    def output_step(self, output_channel='ctr1', low_time=0.001, high_time=0.100, initial_delay=0.00):
        with nidaqmx.Task() as task:
            task.co_channels.add_co_pulse_chan_time('{}/{}'.format(self.dev, output_channel),
                                                    low_time=low_time,
                                                    high_time=high_time,
                                                    initial_delay=initial_delay)

            task.start()
            task.wait_until_done()
            task.stop()

# %% LabJack

class LabJackTSeries(daq.DAQ):
    def __init__(self, dev=None, trigger_channel=['FIO4'], init_device=True):
        super().__init__()  # call the parent class init method
        self.serial_number = dev
        self.trigger_channel = trigger_channel

        self.stream_thread = None

        self.init_device()

    def init_device(self):
        # Initialize ljm T4/T7 handle
        self.handle = ljm.openS("TSERIES", "ANY", "ANY" if self.serial_number is None else self.serial_number)
        self.info = ljm.getHandleInfo(self.handle)
        self.deviceType = self.info[0]
        self.serial_number = self.info[2]

        self.is_open = True

        if self.deviceType == ljm.constants.dtT4:
            # LabJack T4 configuration

            # All analog input ranges are +/-1 V, stream settling is 0 (default) and
            # stream resolution index is 0 (default).
            aNames = ["AIN_ALL_RANGE", "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
            aValues = [10.0, 0, 0]

            # Configure FIO4 to FIO7 as digital I/O.
            ljm.eWriteName(self.handle, "DIO_INHIBIT", 0xFFF0F)
            ljm.eWriteName(self.handle, "DIO_ANALOG_ENABLE", 0x00000)
        else:
            # LabJack T7 and other devices configuration

            # Ensure triggered stream is disabled.
            ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

            # Enabling internally-clocked stream.
            ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

            # All analog input ranges are +/-1 V, stream settling is 6
            # and stream resolution index is 0 (default).
            aNames = ["AIN_ALL_RANGE", "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX", "AIN_ALL_NEGATIVE_CH"]
            aValues = [10.0, 6, 0, 199]

        # Write the analog inputs' negative channels (when applicable), ranges,
        # stream settling time and stream resolution configuration.
        numFrames = len(aNames)
        ljm.eWriteNames(self.handle, numFrames, aNames, aValues)

    def set_trigger_channel(self, trigger_channel):
        self.trigger_channel = trigger_channel

    def write(self, names, vals):
        ljm.eWriteNames(self.handle, len(names), names, vals)

    def send_trigger(self, trigger_channel=None, trigger_duration=0.05):
        if trigger_channel is None:
            trigger_channel = self.trigger_channel
        self.output_step(output_channel=trigger_channel, low_time=0, high_time=trigger_duration, initial_delay=0)

    def output_step(self, output_channel=['FIO4'], low_time=0.001, high_time=0.100, initial_delay=0.00):
        if not isinstance(output_channel, list):
            output_channel = [output_channel]

        write_states = np.ones(len(output_channel), dtype=int)
        if initial_delay > 0:
            time.sleep(initial_delay)
        if low_time > 0:
            self.write(output_channel, (write_states*0).tolist())
            time.sleep(low_time)
        if high_time > 0:
            self.write(output_channel, (write_states*1).tolist())
            time.sleep(high_time)
        self.write(output_channel, (write_states*0).tolist())

    def set_digital_state(self, value=[1], output_channel=['FIO6']):
        if not isinstance(output_channel, list):
            output_channel = [output_channel]

        if not isinstance(value, list):
            value = [value]

        assert len(value) == len(output_channel)

        self.write(output_channel, value)

    def analog_output_step(self, output_channel='DAC0', pre_time=0.5, step_time=1, tail_time=0.5, step_amp=0.5, dt=0.01):
        """
        Generate a voltage step with defined amplitude
            Step comes on at pre_time and goes off at pre_time+step_time

        output_channel: (str) name of analog output channel on device
        pre_time: (sec) time duration before the step comes on (v=0)
        step_time: (sec) duration that step is on
        tail_time: (sec) duration after step (v=0)
        step_amp: (V) amplitude of output step
        dt: (sec) time step size used to generate waveform

        """

        total_time = pre_time + step_time + tail_time
        t0 = time.time()
        clock_time = time.time() - t0  # sec since t0
        while clock_time < total_time:
            clock_time = time.time() - t0  # sec since t0
            if clock_time < pre_time:
                value = 0
            elif clock_time > pre_time and clock_time <= (pre_time+step_time):
                value = step_amp
            elif clock_time > (pre_time+step_time):
                value = 0
            else:
                value = 0
            ljm.eWriteName(self.handle, output_channel, value)
            time.sleep(dt)

    def set_analog_output_to_zero(self, output_channel='DAC0'):
        ljm.eWriteName(self.handle, output_channel, 0)

    def setup_periodic_stream_out(self, output_channel='DAC0', waveform=[0], streamOutIndex=0, scanRate=5000):
        """
        Setup periodic stream out for a defined waveform

        output_channel: (str) name of analog output channel on device
        waveform: (V) waveform to output repeatedly
        scanRate: (Hz) sampling rate of waveform
        """
        ljm.periodicStreamOut(self.handle, streamOutIndex, ljm.nameToAddress(output_channel)[0], scanRate, len(waveform), waveform)

    def setup_pulse_wave_stream_out(self, output_channel='DAC0', freq=1, amp=2.5, pulse_width=0.1, streamOutIndex=0, scanRate=5000):
        """
        Setup periodic stream out for a defined waveform

        output_channel: (str) name of analog output channel on device
        freq: (Hz) frequency of waveform
        amp: (V) amplitude of waveform
        pulse_width: (sec) width of pulse in waveform
        scanRate: (Hz) sampling rate of waveform
        scansPerRead: (int) number of samples to read at a time
        """

        self.stream_output_channel = output_channel
        waveform = np.zeros(int(scanRate/freq))
        waveform[0:int(scanRate*pulse_width)] = amp
        self.setup_periodic_stream_out(output_channel=output_channel, waveform=waveform, scanRate=scanRate)

    def start_stream(self, scanListNames=["STREAM_OUT0"], scanRate=5000, scansPerRead=1000):
        scanList = ljm.namesToAddresses(len(scanListNames), scanListNames)[0]
        actualScanRate = ljm.eStreamStart(self.handle, scansPerRead, len(scanList), scanList, scanRate)

    def stop_stream(self):
        ljm.eStreamStop(self.handle)
        ljm.eWriteName(self.handle, self.stream_output_channel, 0)

    def stream_with_timing(self, scanListNames=["STREAM_OUT0"], scanRate=5000, scansPerRead=1000, pre_time=0.5, stim_time=1):
        def timing_helper():
            time.sleep(pre_time)
            self.start_stream(scanListNames=scanListNames, scanRate=scanRate, scansPerRead=scansPerRead)
            time.sleep(stim_time)
            self.stop_stream()
        self.stream_thread = threading.Thread(target=timing_helper, daemon=True)
        self.stream_thread.start()

    def analog_periodic_output(self, output_channel='DAC0', pre_time=0.5, stim_time=1, waveform=[0], scanRate=5000, scansPerRead = 1000):
        """
        Repeat waveform for a defined duration.
            stim comes on at pre_time and goes off at pre_time+stim_time

        output_channel: (str) name of analog output channel on device
        pre_time: (sec) time duration before the stim comes on (v=0)
        stim_time: (sec) duration that stim is on
        waveform: (V) waveform to output repeatedly
        scanRate: (Hz) sampling rate of waveform
        scansPerRead: (int) number of samples to read at a time
        """

        self.setup_periodic_stream_out(output_channel=output_channel, waveform=waveform, scanRate=scanRate)
        time.sleep(pre_time)
        actualScanRate = ljm.eStreamStart(self.handle, scansPerRead, 1, [ljm.nameToAddress("STREAM_OUT0")[0]], scanRate)
        time.sleep(stim_time)
        ljm.eStreamStop(self.handle)
        ljm.eWriteName(self.handle, output_channel, 0)

    def square_wave(self, output_channel='DAC0', pre_time=0.5, stim_time=1, freq=1, amp=2.5, scanRate=5000, scansPerRead = 1000):
        """
        Generate a square wave with defined frequency and amplitude
            stim comes on at pre_time and goes off at pre_time+stim_time

        output_channel: (str) name of analog output channel on device
        pre_time: (sec) time duration before the stim comes on (v=0)
        stim_time: (sec) duration that stim is on
        freq: (Hz) frequency of output square wave
        amp: (V) amplitude of output square wave
        scanRate: (Hz) sampling rate of waveform
        scansPerRead: (int) number of samples to read at a time
        """

        self.pulse_wave(output_channel=output_channel, pre_time=pre_time, stim_time=stim_time, pulse_width=0.5/freq, freq=freq, amp=amp, scanRate=scanRate, scansPerRead=scansPerRead)

    def pulse_wave(self, output_channel='DAC0', pre_time=0.5, stim_time=1, freq=1, amp=2.5, pulse_width=0.1, scanRate=5000, scansPerRead = 1000):
        """
        Generate a square wave with defined frequency and amplitude
            stim comes on at pre_time and goes off at pre_time+stim_time

        output_channel: (str) name of analog output channel on device
        pre_time: (sec) time duration before the stim comes on (v=0)
        stim_time: (sec) duration that stim is on
        freq: (Hz) frequency of output square wave
        amp: (V) amplitude of output square wave
        pulse_width: (sec) duration of pulse
        scanRate: (Hz) sampling rate of waveform
        scansPerRead: (int) number of samples to read at a time
        """

        waveform = np.zeros(int(scanRate/freq))
        waveform[0:int(scanRate*pulse_width)] = amp
        self.analog_periodic_output(output_channel=output_channel, pre_time=pre_time, stim_time=stim_time, waveform=waveform, scanRate=scanRate, scansPerRead=scansPerRead)

    def close(self):
        if self.is_open:
            ljm.close(self.handle)
            self.is_open = False
