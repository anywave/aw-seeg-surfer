
import re
import pprint

import numpy as np


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
        r = np.r_[:ncont] * dr
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
        color[:, 0] = elei
        color[:, 2] = 1.0 - elei
        color[:, 3] = 1.0
        # sizes
        size = 3 + (3 * elei).astype(int)
        # add item
        ball_items.append(gl.GLScatterPlotItem(
            pos=pos, color=color, size=size, pxMode=False))
    return ball_items
