
from nibabel.gifti import giftiio


class GiiSurface(object):

    def __init__(self, filename, xyz_order=[1, 0, 2]):
        self.obj = giftiio.read(filename)
        self.vert, self.face = [a.data for a in self.obj.darrays]
        self.face = self.face[:, xyz_order]
        self.mesh_data = gl.MeshData(vertexes=self.vert, faces=self.face)

    @property
    def center(self):
        return self.vert.mean(axis=0)


def setup_hemispheres(basename, post='white', **glopt):
    L = GiiSurface(basename + '_L%s.gii' % post)
    R = GiiSurface(basename + '_R%s.gii' % post)
    O = (L.center + R.center) / 2
    return O, L, R


def create_mesh_items():
    glopt = {'shader': 'shaded',
             'glOptions': 'opaque',
             'smooth': True,
             'color': (0.7, 0.7, 0.7, 1.0)}
    return [gl.GLMeshItem(meshdata=S.mesh_data, **glopt) for S in (L, R)]
