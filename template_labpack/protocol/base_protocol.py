#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protocol parent class. Override any methods in here in the user protocol subclass

stimpack presents one stimulus per *trial* and calls a run of them a *series*. (It used to say
epoch and epoch run; both spellings still work, with a deprecation warning naming the new one.)

-protocol_parameters: user-defined params, as entered in the GUI. A parameter given as a list of
                     more than one value takes a different value each trial.
                     *saved as attributes at the series level
-trial_protocol_parameters: this trial's value for each of them
                     *saved as attributes at the individual trial level
-trial_stim_parameters: parameter set used to define stimpack.visual_stim stimulus
                     *saved as attributes at the individual trial level
"""
from stimpack.experiment import protocol


class _DroppedTarget:
    """
    Stands in for a module this rig does not have: every call on it does nothing.

    Lets a protocol keep one code path for rigs with and without a piece of hardware, instead of
    wrapping each call in a conditional or letting the request go out and be dropped, with a
    warning, by the server.
    """
    def __getattr__(self, name):
        def dropped(*args, **kwargs):
            pass
        return dropped


class BaseProtocol(protocol.BaseProtocol):
    """Lab-wide protocol base. Helpers shared by all your protocols go here -- voltage_out below
    is a worked example of what such a helper looks like."""

    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method

    def voltage_out(self, manager):
        """
        ``manager.target('voltage_out')`` on a rig that has voltage-out hardware, and a sink that
        drops the calls on one that does not.

        Use it wherever you would write ``manager.target('voltage_out')``::

            self.voltage_out(multicall).setup_pulse_wave_stream_out(output_channel='DAC0', ...)

        Why it exists: one protocol usually runs on several rigs, and not all of them have the
        hardware. Without this, opto / odor / trigger calls on a rig with no voltage_out module --
        a laptop, say -- are sent anyway, dropped by the server, and reported as a warning for
        every single request. This checks ``has_module()`` (which the server advertises on
        connect), says once per run that the calls are being skipped, and stays quiet after that.

        Takes a manager or a multicall, whichever the call site already has -- both have
        ``.target()``.
        """
        if self.has_module('voltage_out'):
            return manager.target('voltage_out')

        if not getattr(self, '_warned_no_voltage_out', False):
            self._warned_no_voltage_out = True
            print('This rig has no voltage_out module; voltage-out calls (opto, odor, triggers) '
                  'in this protocol will be skipped.')
        return _DroppedTarget()
