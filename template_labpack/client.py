#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from stimpack.experiment import client

class Client(client.BaseClient):
    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method
