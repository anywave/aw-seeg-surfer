import os
import re
import shutil
import pprint
import tempfile
import cStringIO


import numpy as np
import pyqtgraph as pg
from pyqtgraph.opengl import GLViewWidget
from pyqtgraph import QtGui, QtCore
from nibabel.gifti import giftiio
import PIL

from . import surface, seeg, widgets


class Config(QtCore.QSettings):

    "Assumes all strings"

    def __getitem__(self, key):
        val = self.value(key)
        try:
            val = unicode(val.toString())
        except:
            pass
        return val

    def __setitem__(self, key, val):
        self.setValue(key, val)


class TempDir(object):

    def __init__(self):
        self.dirname = tempfile.mkdtemp()

    def path(self, val):
        return os.path.join(self.dirname, val)

    def __del__(self):
        shutil.rmtree(self.dirname)


class UserCancel(Exception):
    pass


def ask_for_filename(caption='', filter='', path='', mode='open'):
    cfg = Config('INS', 'sEEG Surfer')
    path = path or cfg['last-path']
    if len(path) == 0:
        path = os.path.expanduser('~/')
    dlg = getattr(QtGui, 'get%sFileName' % (mode.title(), ))
    path = dlg(caption=caption, filter=filter, dir=path)
    try:
        path, _ = path
    except:
        pass
    if path:
        cfg['last-path'] = os.path.dirname(path)
        return path
    else:
        raise UserCancel()


def ask_for_gii():
    path = ask_for_filename('Open surface', 'Gifti surfaces (*.gii)')
    parts = giifile.split('.gii')[0].split('_')
    basename = '_'.join(parts[:-1])
    # first letter is L or R, we don't care
    giitype = parts[-1][1:]
    return basename, giitype


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


def parse_label(label):
    reg, num = re.match("([A-Za-z']+)(\d+)", label).groups()
    num = int(num)
    return reg, num


class Contact(object):

    def __init__(self, label, **info):
        self.label = label
        self.bipolar = '-' in label
        if self.bipolar:
            l1, l2 = label.split('-')
            self.region, self.index = parse_label(l1)
            _, self.index_ref = parse_label(l2)
        else:
            self.region, self.index = parse_label(label)
        for k, v in info.items():
            setattr(self, k, v)

    def __repr__(self):
        fmt = "<Contact %s%s>"
        idx = "{0.index}-{0.index_ref}" if self.bipolar else "{0.index}"
        fmt %= self.region, idx.format(self)
        return fmt


class Electrode(object):

    def __init__(self, contacts, oblique=False, **info):
        self.region = contacts[0].region
        self.contacts = contacts
        for k, v in info.items():
            setattr(self, k, v)
        self.oblique = oblique
        self.ncont = max(
            c.index_ref if c.bipolar else c.index
            for c in contacts)

    def __repr__(self):
        fmt = "<Electrode %05s %02s contacts>"
        fmt %= self.region, self.ncont
        return fmt

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        elif all(hasattr(c, key) for c in self.contacts):
            return np.array([getattr(c, key) for c in self.contacts])


class Implantation(dict):

    def __init__(self, electrodes):
        self.electrodes = electrodes
        for elec in self.electrodes:
            self[elec.region] = elec

    def __repr__(self):
        return pprint.pformat(self.electrodes)


def parse_ei_txt(filename):
    with open(filename) as fd:
        ei_lines = fd.readlines()
    electrodes = []
    contacts = []
    for line in ei_lines:
        if line.startswith('-'):
            electrodes.append(Electrode(contacts))
            contacts = []
            continue
        label, ei = line.split('\t')
        ei = float(ei.strip())
        contacts.append(Contact(label, ei=ei))
    electrodes.append(Electrode(contacts))
    return Implantation(electrodes)


def parse_locations(impl, fname):
    with open(fname) as fd:
        for l in fd.readlines():
            l = l.strip()
            if l and not l.startswith('#'):
                parts = l.split('\t')
                r = parts[0].strip()
                n = int(parts[1])
                tx, ty, tz, ix, iy, iz = map(float, parts[2:])
                if r not in impl:
                    if r[-1] == 'p':
                        r = r[:-1] + "'"
                elec = impl[r]
                elec.target = np.array([tx, ty, tz])
                elec.entry = np.array([ix, iy, iz])
                elec.oblique = abs(tz - iz) > abs(tx - ix)


def create_balls(impl, log=True):
    ball_items = []
    eis = np.concatenate([e['ei'] for e in impl.values()])
    eimin, eimax = np.percentile(eis, [5, 95])
    for name, elec in impl.items():
        ncont = len(elec.contacts)
        elei = (elec['ei'] - eimin) / eimax
        # normal direction from target to entry
        u = elec.entry - elec.target
        u /= np.linalg.norm(u)
        # contacts are 2mm long, 1.5mm spaced
        dr = 2.0 + 1.5
        r = np.array([c.index for c in elec.contacts]) * dr
        # handle bipolar / monopolar correctly
        bip = [c.bipolar for c in elec.contacts]
        if all(bip):
            r += dr / 2.0
        elif any(bip):
            msg = 'mixed mono & bipolar electrodes not implemented'
            raise NotImplementedError(msg)
        # positions
        pos = elec.target + u * r[:, np.newaxis]
        # colors
        color = np.zeros((ncont, 4))
        color[:, 0] = elei * 0.8
        color[:, 1] = 0.2
        color[:, 2] = (1.0 - elei) * 0.8
        color[:, 3] = 1.0
        # sizes
        size = 2 + (elei).astype(int)
        # add item
        ball_items.append(gl.GLScatterPlotItem(
            pos=pos, color=color, size=size, pxMode=False, glOptions='additive'))
        ball_items.append(gl.GLScatterPlotItem(
            pos=pos, color=color, size=size, pxMode=False, glOptions='translucent'))
    return ball_items


def save_frame(self, fb, fname):
    buff = pg.QtCore.QBuffer()
    buff.open(pg.QtCore.QIODevice.ReadWrite)
    fb.save(buff, "PNG")
    sio = cStringIO.StringIO()
    sio.write(buff.data())
    buff.close()
    sio.seek(0)
    ary_im = np.array(PIL.Image.open(sio))
    if ary_im.shape[0] % 2:
        ary_im = ary_im[:-1]
    if ary_im.shape[1] % 2:
        ary_im = ary_im[:, :-1]
    PIL.Image.fromarray(ary_im).save(fname)


def make_film(self, fname, scene, deg_per_frame=0.5, mode='360'):
    if mode not in ('360', '180'):
        raise ValueError('mode must be "360" or "180"')

    path = util.ask_for_filename(caption='Save movie (GIF Animation)',
                                 filter='GIF Image (*.gif)', mode='save')
    for i in range(2 * 360):
        self.save_frame(gvw.grabFrameBuffer(), 'shot%03d.png' % (i,))
        gvw.orbit(0.5, 0)
        app.processEvents()


class ExportFilm(QtGui.QDialog):
    pass


class SceneAdjustor(QtGui.QWidget):

    "Rot x-y-z, flip, etc"

    def __init__(self, scene, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.scene = scene
        lay = QtGui.QVBoxLayout()


class Scene(GLViewWidget):

    def __init__(self, *args, **kwds):
        GLViewWidget.__init__(self, *args, **kwds)
        self.texts = []

    def paintGL(self):
        super(GLView, self).paintGL()
        white = pg.QtGui.QColor(255, 255, 255)
        black = pg.QtGui.QColor(0, 0, 0)
        for x, y, z, text, font in self.texts:
            self.qglColor(black)
            self.renderText(x + 0.5, y + 0.5, z + 0.5, text, font)
            self.qglColor(black)
            self.renderText(x - 0.5, y - 0.5, z - 0.5, text, font)
            self.qglColor(white)
            self.renderText(x, y, z, text, font)

    def setup(self, items):
        self.setCameraPosition(distance=200)
        for item in [mL, mR] + create_balls(impl) + locballs:
            item.scale(1.0, -1.0, 1.0)
            item.translate(-O[0], O[1], -O[2])
            item.rotate(200, 1.0, 0.0, 0.0)
            self.addItem(item)


class MainWindow(QtGui.QMainWindow):

    "Menus, status and main view"

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(parent=parent)
        self.resize(450, 450)
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        # setup scene
        self.scene = Scene(parent=self)
        self.lay.addWidget(self.scene)
        # setup menus
        # setup status bar

    def load_surface():
        O, L, R = setup_hemispheres(basename)

    def load_implantation():
        pass

    def load_measure():
        pass

    def load_point_localization():
        pass

    def load_volume_localization():
        pass

    def load_mri():
        pass

    def export_screenshot():
        path = util.ask_for_filename(caption='Save screenshot (PNG Image)',
                                     filter='PNG Image (*.png)',
                                     mode='save')
        if path:
            window.scene.grabFrameBuffer().save(path)

    def export_film(self):
        dlg = ExportFilm(parent=self)
        dlg.exec_()

    def quit():
        pass

    def edit_implantation():
        pass

    def edit_values():
        eis = []
        for electrode in impl.electrodes:
            for contact in electrode.contacts:
                eis.append((contact.label, contact.ei))
        tw = pg.TableWidget()
        tw.setData(eis)
        tw.show()

    def edit_localization():
        pass

    def edit_surface_color():
        pass

    def swap_left_right():
        pass

    def labels_on_off():
        if gvw.texts:
            del gvw.texts[:]
            b_labels.setText('Show labels')
        else:
            b_labels.setText('Remove labels')
            font = pg.QtGui.QFont()
            font.setWeight(75)
            font.setPointSize(18)
            for elec in impl.electrodes:
                vec = pg.QtGui.QVector3D(*elec.entry)
                v = mL.mapToView(vec)
                gvw.texts.append((v.x(), v.y(), v.z(), elec.region, font))
            gvw.repaint()

    def single_view():
        pass

    def three_views():
        pass

    _menus = [
        ('&File', [
            ('Load &surface', load_surface),
            ('Load &implantation', load_implantation),
            ('Load &measure', load_measure),
            ('Load &point localization', load_point_localization),
            ('Load &volume localization', load_volume_localization),
            ('Load &MRI', load_mri),
            (None,),
            ('E&xport screenshot', export_screenshot),
            ('Export film &full turn', export_film_360),
            ('Export film &half turn', export_film_180),
            (None,),
            ('&Quit', quit),
        ]),
        ('&Edit', [
            ('&Implantation', edit_implantation),
            ('&Electrode values', edit_values),
            ('&Localization', edit_localization),
            ('&Surface color', edit_surface_color),
        ]),
        ('&View', [
            ('&Swap left/right', swap_left_right),
            ('&Labels on / off', labels_on_off),
            ('Single &view', single_view),
            ('&Three views', three_views),
        ])
    ]


def create_main_window():
    app = pg.mkQApp()

    # gif
    def make_gif():

    win.show()


def parse_data():
    try:
        impl = ei.parse_ei_txt(basename + '_ei.txt')
        ei.parse_locations(impl, basename + '_seeg.txt')
    locballs = []
    try:
        # QString doesn't have same methods as Python string
        py_str_fname = str(basename + '_loc.txt')
        locs = np.loadtxt(py_str_fname)
        if locs.ndim == 1:
            locs = locs.reshape((1, -1))
        for x, y, z, r, g, b, sz in locs:
            locballs.append(gl.GLScatterPlotItem(
                pos=np.r_[x, y, z], color=np.r_[r, g, b], size=sz))
    except Exception as exc:
        import sys
        import traceback
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb)
        print exc
    return O, L, R, impl, locballs
