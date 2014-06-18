
import pyqtgraph as pg
from . import surface, seeg, widgets


def create_main_window():
    app = pg.mkQApp()

    # main widget
    win = pg.QtGui.QWidget()
    win.resize(450, 450)
    lay = pg.QtGui.QVBoxLayout()
    win.setLayout(lay)

    # visualization
    gvw = GLView()
    lay.addWidget(gvw)
    gvw.setCameraPosition(distance=200)
    for item in [mL, mR] + create_balls(impl):
        item.translate(*(-O))
        item.rotate(160, 1.0, 0.0, 0.0)
        gvw.addItem(item)

    # button container
    lay_ctrl = pg.QtGui.QHBoxLayout()
    lay.addLayout(lay_ctrl)

    # screen shot
    def take_shot():
        f = pg.QtGui.QFileDialog.getSaveFileName
        path, _ = f(caption='Save screenshot (PNG Image)',
                    filter='PNG Image (*.png)')
        gvw.grabFrameBuffer().save(path)
    b_capt = pg.QtGui.QPushButton('Screenshot')
    b_capt.clicked.connect(take_shot)
    lay_ctrl.addWidget(b_capt)

    # spin
    is_spinning = [False]

    def do_spin():
        if is_spinning[0]:
            gvw.orbit(2, 0)
    spin_timer = pg.QtCore.QTimer()
    spin_timer.setInterval(10)
    spin_timer.timeout.connect(do_spin)
    spin_timer.start()

    def toggle_spin():
        if is_spinning[0]:
            is_spinning[0] = False
            b_spin.setText('Spin')
        else:
            is_spinning[0] = True
            b_spin.setText('Stop Spin')
    b_spin = pg.QtGui.QPushButton('Spin')
    b_spin.clicked.connect(toggle_spin)
    lay_ctrl.addWidget(b_spin)

    # labels
    def toggle_labels():
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
    b_labels = pg.QtGui.QPushButton('Show labels')
    lay_ctrl.addWidget(b_labels)
    b_labels.clicked.connect(toggle_labels)
    # value table
    value_table = []

    def show_values():
        eis = []
        for electrode in impl.electrodes:
            for contact in electrode.contacts:
                eis.append((contact.label, contact.ei))
        tw = pg.TableWidget()
        tw.setData(eis)
        tw.show()
        value_table.append(tw)
    b_value_table = pg.QtGui.QPushButton('Table of values')
    lay_ctrl.addWidget(b_value_table)
    b_value_table.clicked.connect(show_values)
    # gif

    def make_gif():
        f = pg.QtGui.QFileDialog.getSaveFileName
        path = f(caption='Save movie (GIF Animation)',
                 filter='GIF Image (*.gif)')
        try:
            path, _ = path
        except:
            pass
        try:
            import gif
            import cStringIO
            import PIL
        except Exception as exc:
            msg = pg.QtGui.QErrorMessage(parent=win)
            msg.showMessage("Unable to load libraries:\n\n%r" % (exc,))
            msg.wait()
            return None
        images = []
        pd = pg.QtGui.QProgressDialog(parent=win)
        pd.setModal(True)
        pd.setLabelText("Generating movie...")
        pd.show()
        pd.setMaximum(2 * 360)
        is_canceled = [False]

        def cancel():
            is_canceled[0] = True
        pd.canceled.connect(cancel)
        for i in range(2 * 360):
            if is_canceled[0]:
                break
            img = gvw.grabFrameBuffer()
            buff = pg.QtCore.QBuffer()
            buff.open(pg.QtCore.QIODevice.ReadWrite)
            img.save(buff, "PNG")
            sio = cStringIO.StringIO()
            sio.write(buff.data())
            buff.close()
            sio.seek(0)
            # images.append(PIL.Image.open(sio))
            ary_im = np.array(PIL.Image.open(sio))
            print ary_im.shape
            if ary_im.shape[0] % 2:
                ary_im = ary_im[:-1]
            if ary_im.shape[1] % 2:
                ary_im = ary_im[:, :-1]
            PIL.Image.fromarray(ary_im).save('shot%03d.png' % (i,))
            gvw.orbit(0.5, 0)
            pd.setValue(i)
            app.processEvents()
        """
        if not is_canceled[0]:
            gif.writeGif('spin.gif', images, duration=0.05, dither=5)
        """
        pd.close()
    b_gif = pg.QtGui.QPushButton('Make GIF')
    lay_ctrl.addWidget(b_gif)
    b_gif.clicked.connect(make_gif)
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
