
import os
from pyqtgraph import QtGui, QtCore

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
    giitype = parts[-1][1:] # first letter is L or R, we don't care
    return basename, giitype
    
