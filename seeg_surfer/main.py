
import pyqtgraph as pg
from pyqtgraph.opengl import GLViewWidget
from pyqtgraph import QtGui, QtCore
from . import surface, seeg, widgets


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
        pass

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

    def export_film_360():
        pass

    def export_film_180():
        pass

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


def get_file_name():
    opener = pg.QtGui.QFileDialog.getOpenFileName
    giifile = opener(parent=None,
                     caption='Open left hemisphere surface',
                     filter='Gifti surfaces (*Lwhite.gii)')
    if type(giifile) in (tuple,) and len(tuple) == 2:
        giifile, _ = giifile
    basename = giifile.split('_Lwhite')[0]
    return basename


def parse_data():
    try:
        O, L, R = setup_hemispheres(basename)
        impl = ei.parse_ei_txt(basename + '_ei.txt')
        ei.parse_locations(impl, basename + '_seeg.txt')
    except Exception as exc:
        msg = pg.QtGui.QErrorMessage()
        msg.showMessage("Unable to read data files:\n\n%r" % (exc,))
        app.exec_()
        sys.exit()
    locballs = []
    try:
        # QString doesn't have same methods as Python string
        py_str_fname = str(basename + '_loc.txt')
        locs = np.loadtxt(py_str_fname)
        if locs.ndim == 1:
            locs = locs.reshape((1, -1))
        for x, y, z, r, g, b, sz in locs:
            locballs.append(gl.GLScatterPlotItem(
                pos=np.r_[x,y,z], color=np.r_[r,g,b], size=sz))
    except Exception as exc:
        import sys, traceback
        _, _, tb = sys.exc_info()
        traceback.print_tb(tb)
        print exc
    return O, L, R, impl, locballs
