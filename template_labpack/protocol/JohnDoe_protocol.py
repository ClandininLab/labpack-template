#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
An example protocol file defining visual stimulus protocols.
The protocols defined here can be imported in experiment configuration files.
"""

from template_labpack.protocol import base_protocol


class BaseProtocol(base_protocol.BaseProtocol):
    def __init__(self, cfg):
        super().__init__(cfg)  # call the parent class init method

# %% Some simple visual stimulus protocol classes

class DriftingSquareGrating(BaseProtocol):
    """
    Drifting square wave grating, painted on a cylinder
    """
    def __init__(self, cfg):
        super().__init__(cfg)

        self.run_parameters = self.get_run_parameter_defaults()
        self.protocol_parameters = self.get_protocol_parameter_defaults()

    def get_trial_parameters(self):
        super().get_trial_parameters()
        
        center = self.adjust_center(self.trial_protocol_parameters['center'])
        centerX = center[0]
        centerY = center[1]

        self.trial_stim_parameters = {'name': 'RotatingGrating',
                                      'period': self.trial_protocol_parameters['period'],
                                      'rate': self.trial_protocol_parameters['rate'],
                                      'color': [1, 1, 1, 1],
                                      'mean': self.trial_protocol_parameters['mean'],
                                      'contrast': self.trial_protocol_parameters['contrast'],
                                      'angle': self.trial_protocol_parameters['angle'],
                                      'offset': 0.0,
                                      'cylinder_radius': 1,
                                      'cylinder_height': 10,
                                      'profile': 'square',
                                      'theta': centerX,
                                      'phi': centerY}

    def get_protocol_parameter_defaults(self):
        return {'pre_time': 1.0,
                'stim_time': 4.0,
                'tail_time': 1.0,
                
                'period': 20.0,
                'rate': 20.0,
                'contrast': 1.0,
                'mean': 0.5,
                'angle': [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0],
                'center': (0, 0),
                }

    def get_run_parameter_defaults(self):
        return {'num_trials': 40,
                'idle_color': 0.5,
                'all_combinations': True,
                'randomize_order': True}

# %%

class MovingEllipsoid(BaseProtocol):
    def __init__(self, cfg):
        super().__init__(cfg)

        self.run_parameters = self.get_run_parameter_defaults()
        self.protocol_parameters = self.get_protocol_parameter_defaults()

    def get_trial_parameters(self):
        super().get_trial_parameters()

        stim_time = self.trial_protocol_parameters['stim_time']

        x_trajectory = {'name': 'TVPairs',
                        'tv_pairs': [(0, -2), (stim_time, 2)],
                        'kind': 'linear'}
        y_trajectory = {'name': 'TVPairs',
                        'tv_pairs': [(0, 4), (stim_time, 6)],
                        'kind': 'linear'}
        z_trajectory = {'name': 'TVPairs',
                        'tv_pairs': [(0, -2), (stim_time, 2)],
                        'kind': 'linear'}

        yaw_trajectory = {'name': 'TVPairs',
                            'tv_pairs': [(0, 0), (stim_time, 90*stim_time)],
                            'kind': 'linear'}
        pitch_trajectory   = {'name': 'TVPairs',
                            'tv_pairs': [(0, 0), (stim_time, 90*stim_time)],
                            'kind': 'linear'}
        roll_trajectory = {'name': 'TVPairs',
                            'tv_pairs': [(0, 0), (stim_time, 0)],
                            'kind': 'linear'}

        self.trial_stim_parameters = {'name': 'MovingEllipsoid',
                            'x_length': self.trial_protocol_parameters['dimensions'][0],
                            'y_length': self.trial_protocol_parameters['dimensions'][1],
                            'z_length': self.trial_protocol_parameters['dimensions'][2],
                            'color': self.trial_protocol_parameters['color'],
                            'x': x_trajectory,
                            'y': y_trajectory,
                            'z': z_trajectory,
                            'yaw': yaw_trajectory,
                            'pitch': pitch_trajectory,
                            'roll': roll_trajectory,
                            'n_subdivisions': 6}

    def get_protocol_parameter_defaults(self):
        return {'pre_time': 0.5,
                'stim_time': 4.0,
                'tail_time': 0.5,

                'dimensions': (2,1,1),
                'color': None,
                }

    def get_run_parameter_defaults(self):
        return {'num_trials': 2,
                'idle_color': 0.5,
                'all_combinations': True,
                'randomize_order': True}

# %%