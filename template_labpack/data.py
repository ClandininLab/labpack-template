#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data file class
"""

from stimpack.experiment import data

class Data(data.BaseData):
    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method
