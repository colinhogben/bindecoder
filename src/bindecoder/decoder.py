#=======================================================================
"""
Decode binary files
"""
#=======================================================================
from contextlib import contextmanager
from io import BytesIO
import struct

class Decoder:
    """Base class for decoding binary data"""
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
        """Use the following size bytes as a self-contained stream"""
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
        """Temporarily use a given endianness"""
        old_end, self.end = self.end, '>' if big else '<'
        try:
            yield
        finally:
            self.end = old_end

    def vset(self, name, value):
        self.view.set(name, value)
        return value

