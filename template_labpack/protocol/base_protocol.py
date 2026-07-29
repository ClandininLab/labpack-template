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

class BaseProtocol(protocol.BaseProtocol):
    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method
