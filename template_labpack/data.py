#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Starting point for a lab-specific data class. Nothing here is wired up.

module_paths.data is commented out in the example config on purpose: naming a data module
overrides `data_format` entirely -- stimpack uses your class and never consults the setting, so
the startup dialog's format choice silently does nothing and you get this class's format
whatever was picked. Subclass BaseData (HDF5, series/trials), data.LegacyHdf5Data (the pre-0.3
epoch_runs/epochs layout) or data_nwb.NWBData (a directory of .nwb files), then point the
config here -- and expect its data_format to be ignored from then on.
"""

from stimpack.experiment import data

class Data(data.BaseData):
    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method
