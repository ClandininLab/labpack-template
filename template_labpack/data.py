#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Starting point for a lab-specific data class. Nothing here is wired up.

module_paths.data is commented out in the example config on purpose: naming ONE data module
fixes the format, because the class it subclasses is what decides it -- so `data_format` and the
startup dialog's choice stop being consulted and you get this class's format whatever was
picked. Subclass BaseData (HDF5, series/trials), data.LegacyHdf5Data (the pre-0.3
epoch_runs/epochs layout) or data_nwb.NWBData (a directory of .nwb files).

To keep the format selectable, map one class per format in the config instead:

    module_paths:
      data:
        hdf5: template_labpack/data.py
        nwb:  template_labpack/data_nwb.py

A `:ClassName` suffix picks a class out of a module, so overrides shared between the two HDF5
layouts can live in one mixin next to both classes rather than in two near-empty modules:

    class _Lab:
        ...your overrides...

    class Data(_Lab, data.BaseData): pass
    class DataLegacy(_Lab, data_legacy.LegacyHdf5Data): pass
"""

from stimpack.experiment import data

class Data(data.BaseData):
    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method
