import numpy as np
from stimpack.visual_stim import distribution as spv_distribution

class SparseBinary(spv_distribution.Distribution):
    """
    Ternary distribution with tunable degree of sparseness. High sparseness means lower
    probability of min or max values being shown. Note that:
        Sparseness of 0 is a binary, uniform distribution,
        Sparseness of 1/3 is a standard ternary distribution
    """

    def __init__(self, rand_min=0, rand_max=1, sparseness=0):
        self.rand_min = rand_min
        self.rand_max = rand_max
        self.mean_p = sparseness
        self.tail_p = (1.0-sparseness)/2

    def get_random_values(self, output_shape):
        rand_values = np.random.choice([self.rand_min, (self.rand_min + self.rand_max)/2, self.rand_max],
                                       size=output_shape,
                                       p=(self.tail_p, self.mean_p, self.tail_p))
        return rand_values


