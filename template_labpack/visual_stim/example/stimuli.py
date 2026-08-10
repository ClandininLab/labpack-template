import copy
from math import radians

import numpy as np

from stimpack.visual_stim import shapes as spv_shapes
from stimpack.visual_stim import stimuli as spv_stimuli
from stimpack.visual_stim.stimuli import BaseProgram
from stimpack.visual_stim.trajectory import make_as_trajectory, return_for_time_t
from stimpack.visual_stim.distribution import make_as_distribution

from template_labpack.visual_stim.example.shapes import GlIcosphere

class MovingEllipsoid(BaseProgram):
    def __init__(self, screen):
        super().__init__(screen=screen, num_tri=1000)

    def configure(self, x_length=1, y_length=1, z_length=1, x=0, y=0, z=0, yaw=0, pitch=0, roll=0, n_subdivisions=6):
        """
        Stimulus consisting of a rectangular patch on the surface of a sphere. Patch is rectangular in spherical coordinates.

        :param x_length: meters, x length of ellipsoid
        :param y_length: meters, y length of ellipsoid
        :param z_length: meters, z length of ellipsoid
        :param x: meters, x position of center of ellipsoid
        :param y: meters, y position of center of ellipsoid
        :param z: meters, z position of center of ellipsoid
        :param yaw: degrees, rotation around z axis
        :param pitch: degrees, rotation around y axis
        :param roll: degrees, rotation around x axis
        *Any of these params can be passed as a trajectory dict to vary these as a function of time elapsed
        """
        self.x_length = make_as_trajectory(x_length)
        self.y_length = make_as_trajectory(y_length)
        self.z_length = make_as_trajectory(z_length)
        self.x = make_as_trajectory(x)
        self.y = make_as_trajectory(y)
        self.z = make_as_trajectory(z)
        self.yaw = make_as_trajectory(yaw)
        self.pitch = make_as_trajectory(pitch)
        self.roll = make_as_trajectory(roll)
        
        # colors=None gives GlIcosphere's per-face grayscale gradient, which is what makes the
        # rotation visible -- a uniformly colored, unlit sphere looks the same at every angle.
        self.stim_object_template = GlIcosphere(colors=None, n_subdivisions=n_subdivisions).scale(0.5)

    def eval_at(self, t, subject_position={'x':0, 'y':0, 'z':0, 'theta':0, 'phi':0, 'roll':0}):
        x_length = return_for_time_t(self.x_length, t)
        y_length = return_for_time_t(self.y_length, t)
        z_length = return_for_time_t(self.z_length, t)
        x        = return_for_time_t(self.x, t)
        y        = return_for_time_t(self.y, t)
        z        = return_for_time_t(self.z, t)
        yaw    = return_for_time_t(self.yaw, t)
        pitch      = return_for_time_t(self.pitch, t)
        roll    = return_for_time_t(self.roll, t)

        self.stim_object = copy.copy(self.stim_object_template
                                    ).scale(np.array((x_length, y_length, z_length)).reshape(3,1)
                                    ).rotate(radians(yaw), radians(pitch), radians(roll)
                                    ).translate((x, y, z))

