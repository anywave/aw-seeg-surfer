import os
import re
import shutil
import pprint
import tempfile
import cStringIO

import numpy as np
import pyqtgraph as pg
from pyqtgraph import opengl as gl
from pyqtgraph import QtGui, QtCore
from nibabel.gifti import giftiio
import openpyxl
import PIL


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


def ask_for_filename(caption='', filter='', path='', mode='open'):
    mode_map = {
        'open': 'getOpenFileName',
        'opens': 'getOpenFileNames',
        'save': 'getSaveFileName',
        'dir': 'getExistingDirectory'
        }
    if mode not in mode_map:
        fmt = "received mode=%r, expected one of %r"
        content = mode, mode_map.keys()
        raise ValueError(fmt % content)
    cfg = Config('INS', 'sEEG Surfer')
    path = path or cfg['last-path']
    if len(path) == 0:
        path = os.path.expanduser('~/')
    dlg = getattr(QtGui.QFileDialog, mode_map[mode])
    kwds = {'caption': caption, 'directory': path}
    if not mode == 'dir':
        kwds['filter'] = filter
    path = dlg(**kwds)
    if mode == 'opens':
        path = map(unicode, path)
    else:
        path = unicode(path)
    if path:
        cfg['last-path'] = path[0] if mode == 'opens' else path
        return path
    else:
        raise RuntimeError('User canceled')


def xl_find_cell(wb, value, ignore_case=True, test_in=True):
    hits = []
    value = unicode(value)
    if ignore_case:
        value = value.lower()
    for sheet in wb.worksheets:
        for row in sheet.rows:
            for cell in row:
                cval = cell.value
                if isinstance(cval, unicode) and ignore_case:
                    cval = cval.lower()
                    ok = value in cval if test_in else value == cval
                else:
                    ok = value == cval
                if ok:
                    hits.append(cell)
    return hits


def xl_find_rect(origin):
    # get sheet & row for origin
    sheet = origin.parent
    row = origin.row
    # determine value columns
    row = sheet.rows[origin.row - 1]
    found_origin = False
    value_columns = []
    clo, chi = 0, 0
    for i, c in enumerate(row):
        if found_origin:
            val = c.value
            if val is None:
                chi = i
                break
            else:
                value_columns.append(val)
        elif c.coordinate == origin.coordinate:
            found_origin = True
            clo = i
        else:
            pass
    # determine rows
    rhi = 0
    for i in xrange(origin.row, sheet.get_highest_row() + 1):
        idx = origin.column + str(i)
        val = sheet[idx].value
        if val is None:
            break
        rhi = i
    # return rectangle
    return [row[clo:chi] for row in sheet.rows[origin.row - 1:rhi]]


def xl_get(fname, *origins):
    wb = openpyxl.load_workbook(fname)
    rects = []
    for origin in origins:
        try:
            rect = xl_find_rect(xl_find_cell(wb, origin)[0])
            rects.append([[c.value for c in r] for r in rect])
        except:
            print "couldn't find ", origin
    return rects


def parse_seeg_label(label):
    match = lambda l: re.match("([A-Za-z']+)(\d+)", l).groups()
    bipolar = '-' in label
    if bipolar:
        l1, l2 = label.split('-')
        region, index = match(l1)
        _, index_ref = match(l2)
    else:
        region, index = match(label)
        index_ref = None
    if region.endswith("'"):
        region = region[:-1] + "p"
    return region, int(index), int(index_ref) if index_ref else None


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

    def labels_on_off(self):
        _ = not self.scene.render_labels
        self.a_labels_on_off.setChecked(_)
        self.scene.render_labels = _
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

# create items for elements of scene graph

# interesting methods on GLGraphicsItem: hide/show, update, map{To, From}View


class ColorSizeMap(object):
    "For a value, generate a color (RGBA) and size"
    maps = {
        'default': (
            np.r_[0.0, 1.0],
            np.array([[0.0, 0.0, 1.0, 1.0],
                      [1.0, 0.0, 0.0, 1.0]]),
            np.r_[0, 50]
            ),
        'rb': (
            np.r_[0.0, 1.0],
            np.array([[0.0, 0.0, 1.0, 1.0],
                      [1.0, 0.0, 0.0, 1.0]]),
            None
            ),
        'sz': (
            np.r_[0.0, 1.0],
            None,
            np.r_[0, 50]
            ),
    }

    def __init__(self, map='default', log=False, logeps=-1):
        self.map = self.maps.get(map, map)
        self.log = log
        self.logeps = logeps

    def __call__(self, vals):
        vals = vals.astype(np.float32)
        vmin = vals.min()
        vptp = vals.ptp()
        if self.log:
            vals += vmin*10**self.logeps
            vals = np.log(vals)
        vals = (vals - vmin)/vptp
        v, c, sz = self.map
        if sz is not None:
            size = np.interp(vals, v, sz).astype(sz.dtype)
        else:
            size = None
        if c is not None:
            color = np.empty(vals.shape + (4,), np.float32)
            for i in xrange(4):
                color[..., i] = np.interp(vals, v, c[:, i])
        else:
            color = None
        return color, size


class ColorSizeMultiMap(object):

    def __init__(self, maps, mode='add'):
        self.maps = []
        for map in maps:
            if not isinstance(map, ColorSizeMap):
                map = ColorSizeMap(map)
            self.maps.append(map)
        self.mode = mode
        if mode not in ('add',):
            raise ValueError('mode not supported: %r', mode)

    def __call__(self, *vals):
        colors = []
        sizes = []
        for map, val in zip(self.maps, vals):
            color, size = map(val)
            if color is not None:
                colors.append(color)
            if size is not None:
                sizes.append(size)
        colors = np.array(colors).mean(axis=0)
        sizes = np.array(sizes).mean(axis=0)
        return colors, sizes


class ColorSizeMapsView(object):
    "Registry of color/size mappings"
    def add_map(self, name, map):
        pass


class sEEG(gl.GLScatterPlotItem):
    # options: pxMode, color/size mapping

    def __init__(self):
        gl.GLScatterPlotItem.__init__(self)
        self.electrodes = {}
        self.montage = {}

    def paint(self):
        self.setGLOptions('additive')
        gl.GLScatterPlotItem.paint(self)
        self.setGLOptions('translucent')
        gl.GLScatterPlotItem.paint(self)

    def add_electrode(self, *args):
        if len(args) == 1 and len(args[0]) == 7:
            args = args[0]
        name, tx, ty, tz, ix, iy, iz = args
        if name.endswith("'"):
            name = name[:-1] + "p"
        self.electrodes[name] = {
            'target': np.array([tx, ty, tz], np.float32),
            'entry': np.array([ix, iy, iz], np.float32),
            'oblique': np.abs(tz - iz) > np.abs(tx - ix)
        }

    def update_pos(self):
        self.setData(pos=self.contact_pos)

    def update_color_size(self):
        values = []
        for measure in self.mapped_measures:
            values.append(self.montage['measures'][measure])
        color, size = self.csmap(*values)
        self.setData(color=color, size=size)

    @classmethod
    def from_xls(cls, fname):
        self = cls()
        elec, mont = xl_get(fname, 'electrodes', 'montage')
        # setup electrodes
        map(self.add_electrode, elec[1:])
        # setup montage
        self.montage['contacts'] = [r[0] for r in mont[1:]]
        self.montage['measures'] = {}
        for i, name in enumerate(mont[0][1:]):
            values = [r[i + 1] for r in mont[1:]]
            self.montage['measures'][name] = np.array(values)
        self.update_pos()
        self.csmap = ColorSizeMultiMap(('default',))
        self.mapped_measures = [mont[0][1]]
        self.update_color_size()
        return self

    @property
    def contact_pos(self):
        pos = []
        for contact in seeg.montage['contacts']:
            reg, ix, ixrf = parse_seeg_label(contact)
            i, t = [seeg.electrodes[reg][k] for k in 'entry target'.split()]
            u = i - t
            u /= np.linalg.norm(u)
            # contacts are 2.0 mm long, spaced at 1.5 mm
            dr = 2.0 + 1.5
            if ixrf is None:                # monopolar
                r = dr * ix
            else:                           # bipolar, ixrf > ix
                r = dr * (ixrf - ix) / 2.0
            pos.append(t + u * r)
        return np.vstack(pos)


class PointLocalization(gl.GLScatterPlotItem):
    @classmethod
    def from_xls(cls, fname, key):
        self = cls()
        rows, = xl_get(fname, key)
        self.loc_name, _, _, _ = rows[0]
        vxyz = np.array(rows[1:])
        self.loc_values = vxyz[:, 0]
        self.loc_xyz = vxyz[:, 1:]
        self.loc_csmap = ColorSizeMap('default')
        self.update_data()
        return self
    def update_data(self):
        color, size = self.loc_csmap(self.loc_values)
        self.setData(pos=self.loc_xyz, color=color, size=size)


def cortical_mesh_items(fname, xyz=[1, 0, 2]):
    glopt = {'shader': 'shaded',
             'glOptions': 'opaque',
             'smooth': True,
             'color': (0.7, 0.7, 0.7, 1.0)}
    parts = fname.split('_')
    bname = '_'.join(parts[:-1])
    gtype = parts[-1].split('.gii')[0][1:]
    items = []
    centers = []
    for hemi in 'LR':
        gii = giftiio.read('%s_%s%s.gii' % (bname, hemi, gtype))
        vert, face = [a.data for a in gii.darrays]
        print vert.shape, face.shape
        items.append(gl.GLMeshItem(vertexes=vert, face=face[:, xyz], **glopt))
        centers.append(vert.mean(axis=0))
    center = (centers[0] + centers[1]) / 2.0
    return center, items


class Scene(gl.GLViewWidget):
    # options: label font
    # TODO setup for mixed qt/gl rendering e.g. colorbar
    def __init__(self, *args, **kwds):
        gl.GLViewWidget.__init__(self, *args, **kwds)
        self.labels = []
        self.label_font = QtGui.QFont()
        self.label_font.setWeight(75)
        self.label_font.setPointSize(18)
        self.label_offset = 0.5
        self.label_fg_color = QtGui.QColor(255, 255, 255)
        self.label_bg_color = QtGui.QColor(0, 0, 0)
        self.render_labels = False
    def paintGL(self):
        gl.GLViewWidget.paintGL(self)
        if self.render_labels:
            fg, bg = self.label_fg_color, self.label_bg_color
            font, os = self.label_font, self.label_offset
            for x, y, z, text in self.labels:
                self.qglColor(bg)
                self.renderText(x + os, y + os, z + os, text, font)
                self.qglColor(bg)
                self.renderText(x - os, y - os, z - os, text, font)
                self.qglColor(fg)
                self.renderText(x, y, z, text, font)
    def setup(self, items):
        self.setCameraPosition(distance=200)
        for item in [mL, mR] + create_balls(impl) + locballs:
            item.scale(1.0, -1.0, 1.0)
            item.translate(-O[0], O[1], -O[2])
            item.rotate(200, 1.0, 0.0, 0.0)
            self.addItem(item)

seeg = sEEG.from_xls('test.xlsx')
sc.addItem(seeg)
pl = PointLocalization.from_xls('test.xlsx', 'lcmv')
sc.addItem(pl)

sc = Scene()
sc.show()
cs, items = cortical_mesh_items('work/loe/LOE_Lwhite.gii')
[sc.addItem(i) for i in items]

print cm.l_mesh.vertexes

cm.l_mesh.opts['meshdata'].faceNormals()


sc = Scene()
xg = gl.GLGridItem()
yg = gl.GLGridItem()
zg = gl.GLGridItem()
xg.rotate(90, 0, 1, 0)
yg.rotate(90, 1, 0, 0)
xg.translate(-10, 0, 0)
yg.translate(0, -10, 0)
zg.translate(0, 0, -10)
[sc.addItem(g) for g in (xg, yg, zg)]
sc.show()


sci = gl.GLScatterPlotItem(pos=np.random.randn(50, 3), color=np.random.rand(50, 4), size=5)

sc.addItem(sci)

