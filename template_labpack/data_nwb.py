#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Starting point for a lab-specific NWB data class. Nothing here is wired up.

This is the file the per-format mapping in configs/example_config.yaml points at:

    module_paths:
      data:
        hdf5: template_labpack/data.py
        nwb:  template_labpack/data_nwb.py

With that mapping, the `data_format` choice (config or startup dialog) keeps working and picks
the matching class -- see the notes in template_labpack/data.py for why naming a single data
module instead would fix the format outright.
"""

from stimpack.experiment import data_nwb

class Data(data_nwb.NWBData):
    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method
