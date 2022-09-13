#=======================================================================
"""
Decode binary files
"""
#=======================================================================
from __future__ import print_function
from contextlib import contextmanager
from io import BytesIO
import struct

class Decoder:
    def __init__(self, stream, view, big_endian=False):
        self.stream = stream
        self.view = view
        self.pos = 0
        self.end = '>' if big_endian else '<'
        self.stream_stack = []

    def i1(self, name=None):
        """Signed 8-bit integer"""
        return self.scalar(name, 1, 'b')

    def u1(self, name=None):
        """Unsigned 8-bit integer"""
        return self.scalar(name, 1, 'B')

    def i2(self, name=None):
        """Signed 16-bit integer"""
        return self.scalar(name, 2, 'h')

    def u2(self, name=None):
        """Unsigned 16-bit integer"""
        return self.scalar(name, 2, 'H')

    def i4(self, name=None):
        """Signed 32-bit integer"""
        return self.scalar(name, 4, 'i')

    def u4(self, name=None):
        """Unsigned 32-bit integer"""
        return self.scalar(name, 4, 'I')

    def i8(self, name=None):
        """Signed 64-bit integer"""
        return self.scalar(name, 8, 'q')

    def u8(self, name=None):
        """Unsigned 64-bit integer"""
        return self.scalar(name, 8, 'Q')

    def f4(self, name=None):
        """Unsigned 32-bit floating-point"""
        return self.scalar(name, 4, 'f')

    def f8(self, name=None):
        """Unsigned 64-bit floating-point"""
        return self.scalar(name, 8, 'd')

    def scalar(self, name, size, desc):
        value, = struct.unpack(self.end + desc, self.read(size))
        if name:
            self.vset(name, value)
        return value

    def read(self, size=None):
        """Read a number of bytes"""
        if size is None:
            data = self.stream.read()
        else:
            data = self.stream.read(size)
            if len(data) < size:
                raise EOFError('Tried to read %d byte%s, only %d available' %
                               (size, '' if size==1 else 's', len(data)))
        self.pos += len(data)
        return data

    def seek(self, position):
        """Move to a specific position in the file"""
        self.stream.seek(position)
        self.pos = position

    @contextmanager
    def substream(self, size):
        data = self.read(size)
        sub = BytesIO(data)
        self.stream_stack.append((self.stream, self.pos))
        self.stream, self.pos = sub, 0
        try:
            yield
        finally:
            self.stream, self.pos = self.stream_stack.pop()

    @contextmanager
    def endian(self, big):
        old_end, self.end = self.end, '>' if big else '<'
        try:
            yield
        finally:
            self.end = old_end

    def vset(self, name, value):
        self.view.set(name, value)

#-----------------------------------------------------------------------
#       Viewer
#-----------------------------------------------------------------------
class Viewer:
    """Abstract base class"""
    @contextmanager
    def map(self, name):
        self.enter_map(name)
        try:
            yield
        finally:
            self.exit()

    @contextmanager
    def array(self, name):
        self.enter_array(name)
        try:
            yield
        finally:
            self.exit()

    def enter_map(self, name):
        raise NotImplementedError

    def enter_array(self, name):
        raise NotImplementedError

    def set(self, name, value):
        raise NotImplementedError

    def blob(self, name, data):
        """Typically unparsed data, or wrapped encoded data"""
        raise NotImplementedError

class PlainViewer(Viewer):
    def __init__(self):
        self.level = 0

    def set(self, name, value):
        self.show('%s = %r' % (name, value))

    def blob(self, name, data):
        hdata = ' '.join('%02x' % b for b in data[:16])
        if len(data) > 16:
            hdata += '...'
        self.show('%s[%d]: %s' % (name, len(data), hdata))

    def show(self, text):
        print('%s%s' % ('  ' * self.level, text))

    def enter(self, name):
        self.show('%s:' % name)
        self.level += 1

    enter_map = enter
    enter_array = enter

    def exit(self):
        self.level -= 1

class DataViewer(Viewer):
    """Build a native data structure using dicts and lists"""
    map_class = dict
    array_class = list

    def __init__(self):
        super(Viewer,self).__init__()
        self.stack = []
        self.cur = self.map_class()

    def enter_map(self, name):
        new = self.map_class()
        self.set(name, new)
        self.stack.append(self.cur)
        self.cur = new

    def enter_array(self, name):
        new = self.array_class()
        self.set(name, new)
        self.stack.append(self.cur)
        self.cur = new

    def exit(self):
        self.cur = self.stack.pop()

    def set(self, name, value):
        if isinstance(self.cur, list):
            if name != len(self.cur):
                raise IndexError('Invalid array index %s, expected %d' %
                                 (name, len(self.cur)))
            self.cur.append(value)
        else:
            if name in self.cur:
                raise KeyError('Repeatsd key "%s"' % name)
            self.cur[name] = value

    blob = set

    def result(self):
        return self.cur
