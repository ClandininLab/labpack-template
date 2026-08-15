#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DAQ drivers, one vendor per file, mirroring the stimpack.daq package this extends.

The config's module_paths.daq points at this file, so every class re-exported here can be
named by a rig config's ``trigger:`` expression and imported as
``from template_labpack.daq import ...``. Imports are relative so the package loads
identically as an installed package and as the file the config names.
"""
from .ni import NIUSB6001, NIUSB6210
from .labjack import LabJackTSeries
from .on_server import DAQonServer

__all__ = ['DAQonServer', 'NIUSB6001', 'NIUSB6210', 'LabJackTSeries']
