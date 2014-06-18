
import pyqtgraph.opengl as gl


class GLView(gl.GLViewWidget):

    def __init__(self, *args, **kwds):
        gl.GLViewWidget.__init__(self, *args, **kwds)
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
