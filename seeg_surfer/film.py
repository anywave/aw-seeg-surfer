import os
import cStringIO
import PIL

class Filmer(object):
    def __init__(self, scene, mode='360', parent=None):
        self.scene = scene
        if mode not in ('360', '180'):
            raise ValueError('mode must be "360" or "180"')

    def __call__():
        # TODO use temp directory
        path = util.ask_for_filename(caption='Save movie (GIF Animation)', 
                                     filter='GIF Image (*.gif)', mode='save')
        for i in range(2*360):
            self.save_frame(gvw.grabFrameBuffer(), 'shot%03d.png' % (i,))
            gvw.orbit(0.5, 0)
            app.processEvents()

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
