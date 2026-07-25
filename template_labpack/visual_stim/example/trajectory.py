import numpy as np
from scipy.interpolate import interp1d

from stimpack.visual_stim import trajectory as spv_trajectory

class LoomGabb(spv_trajectory.Trajectory):
    """
    Expanding loom trajectory defined by rv ratio and collision time
    See def'n in Gabbiani et al., 1999
    https://www.jneurosci.org/content/jneuro/19/3/1122.full.pdf

    :rv_ratio: sec. Ratio of object physical length to approach speed
    :end_radius: deg., maximum radius of spot
    :collision_time: sec., time at which object is 180 deg

    : returns radius of spot for time t
    """
    def __init__(self, rv_ratio, end_radius, collision_time):
        def get_loom_size(t):
            # note this is spot radius
            angular_size = np.rad2deg( np.arctan( rv_ratio / (collision_time - t) ) )
            # Cap the curve at end_size and have it just hang there
            if (angular_size > end_radius):
                angular_size = end_radius

            # Freeze it at the max in case there is more stim time to go
            if t > collision_time:
                angular_size = end_radius

            return angular_size
        self.getValue = get_loom_size

