#=======================================================================
"""
Back ends for bindecoder
"""
#=======================================================================
from contextlib import contextmanager

class Viewer:
    """Base class for bindecoder back ends"""
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
    """Print structure, indented"""
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
                raise KeyError('Repeated key "%s"' % name)
            self.cur[name] = value

    blob = set

    def result(self):
        """Get the built data structure"""
        return self.cur
