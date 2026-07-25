import os
import numpy as np
import template_labpack
from stimpack.visual_stim import util as spv_util

# <repo>/template_labpack/__init__.py -> <repo>. Derived from the package's own location rather than
# by splitting the path on the package name: that idiom breaks as soon as the name appears more than
# once in the path (e.g. a checkout at ~/labpack/labpack/), and silently returns the wrong prefix.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(template_labpack.__file__)))


def get_resource_path(resource_name):
    """Absolute path to <repo>/resources/<resource_name>.

    Put movies, images and trajectory files your stimuli need in a `resources/` directory at the
    root of your labpack. This template ships without one, so calling this before you create it
    raises -- the message tells you where it looked.
    """
    path_to_resource = os.path.join(_REPO_ROOT, 'resources', resource_name)

    assert os.path.exists(path_to_resource), 'Resource not found at {}'.format(path_to_resource)

    return path_to_resource

def rot1_scale_rot2(pts, yaw1, pitch1, roll1, scale_x, scale_y, scale_z, yaw2, pitch2, roll2):
    A = spv_util.rot_mat(yaw2, pitch2, roll2) @ np.diag([scale_x, scale_y, scale_z]) @ spv_util.rot_mat(yaw1, pitch1, roll1)
    return A @ pts

