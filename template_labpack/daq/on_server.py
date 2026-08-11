#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional

from stimpack import daq
from stimpack.rpc.multicall import MyMultiCall


class DAQonServer(daq.DAQonServer):
    '''
    Dummy DAQ class for when the DAQ resides on the server, so that we can call methods as if the DAQ is on the client side.

    Calls are addressed to the server's 'voltage_out' module with target('voltage_out'), so the
    method names here are just the driver's own method names (e.g. LabJackTSeries.start_stream).
    'voltage_out' is the current name of what used to be called the 'daq' module; target('daq')
    still resolves to it, but with a one-time deprecation warning. Note the even older style -- an
    untargeted call to a "daq_"-prefixed name -- no longer works at all: untargeted requests are
    routed to the server's root node, where those names are not registered, so they would silently
    do nothing.
    '''
    def setup_pulse_wave_stream_out(self, multicall:Optional[MyMultiCall]=None, **kwargs):
        if multicall is not None and isinstance(multicall, MyMultiCall):
            multicall.target('voltage_out').setup_pulse_wave_stream_out(**kwargs)
            return multicall
        if self.manager is not None:
            self.manager.target('voltage_out').setup_pulse_wave_stream_out(**kwargs)

    def start_stream(self, multicall:Optional[MyMultiCall]=None, **kwargs):
        if multicall is not None and isinstance(multicall, MyMultiCall):
            multicall.target('voltage_out').start_stream(**kwargs)
            return multicall
        if self.manager is not None:
            self.manager.target('voltage_out').start_stream(**kwargs)

    def stop_stream(self, multicall:Optional[MyMultiCall]=None, **kwargs):
        if multicall is not None and isinstance(multicall, MyMultiCall):
            multicall.target('voltage_out').stop_stream(**kwargs)
            return multicall
        if self.manager is not None:
            self.manager.target('voltage_out').stop_stream(**kwargs)

    def stream_with_timing(self, multicall:Optional[MyMultiCall]=None, **kwargs):
        if multicall is not None and isinstance(multicall, MyMultiCall):
            multicall.target('voltage_out').stream_with_timing(**kwargs)
            return multicall
        if self.manager is not None:
            self.manager.target('voltage_out').stream_with_timing(**kwargs)
