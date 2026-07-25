import numpy as np
from stimpack.visual_stim import shapes as spv_shapes
from stimpack.visual_stim import util as spv_util
import icosphere

class GlVertices(spv_shapes.GlVertices):
    def rot1_scale_rot2(self, yaw1, pitch1, roll1, scale_x, scale_y, scale_z, yaw2, pitch2, roll2):
        '''
        rot2 @ scale @ rot1 @ vertices
        '''
        return GlVertices(vertices=spv_util.rot1_scale_rot2(self.vertices, yaw1, pitch1, roll1, scale_x, scale_y, scale_z, yaw2, pitch2, roll2), colors=self.colors, tex_coords=self.tex_coords)

class GlIcosphere(GlVertices):
    def __init__(self, colors=(1, 1, 1, 1), n_subdivisions=6):
        '''
        :param colors: list of colors, one for each face or a single color for all faces; None for default colors
        :param n_subdivisions: number of subdivisions of each edge of the icosahedron. 
                                nr_vertex = 12 + 10 * (nu**2 -1) (e.g. 1=12, 2=42, 3=92, 4=162, 5=252, 6=362)
                                nr_face = 20 * nu**2 (e.g. 1 = 20, 2 = 80, 3 = 180, 4 = 320, 5 = 500, 6 = 720)
        '''
        super().__init__()

        vertices, faces = icosphere.icosphere(n_subdivisions)
        
        if colors is None:
            colors = np.linspace(0, 1, len(faces))
        elif isinstance(colors, tuple):
            colors = [colors] * len(faces)
        elif isinstance(colors, (int, float)):
            colors = [(colors, colors, colors, 1.0)] * len(faces)
        else:
            assert len(colors) == len(faces), 'Number of colors must match number of faces'
        
        for face, color in zip(faces, colors):
            self.add(spv_shapes.GlTri(vertices[face[0]], vertices[face[1]], vertices[face[2]], spv_util.get_rgba(color)))
            