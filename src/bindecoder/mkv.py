#=======================================================================
"""
Decode Matroska or webm file
"""
#       References:
#	https://www.matroska.org/technical/elements.html
#=======================================================================
from .decoder import Decoder
from .hexdumper import HexDumper

C_UNKNOWN, C_ELEMENTS, C_UINT, C_FLOAT, C_STRING, C_UTF8 = range(6)

elem_name = {
    # Generic EBML elements
    0xa45dfa3: ('EBML', C_ELEMENTS),
    0x286: ('EMBLVersion', C_UINT),
    0x2f7: ('EMBLReadVersion', C_UINT),
    0x2f2: ('EMBLMaxIDLength', C_UINT),
    0x2f3: ('EMBLMaxSizeLength', C_UINT),
    0x282: ('DocType', C_STRING),
    0x287: ('DocTypeVersion', C_UINT),
    0x285: ('DocTypeReadVersion', C_UINT),
    0x281: ('DocTypeExtension', C_UINT),

    # Matroska elements
    0x8538067: ('Segment', C_ELEMENTS),
    0x14d9b74: ('SeekHead', C_ELEMENTS),
    0xdbb: ('Seek', C_ELEMENTS),
    0x13ab: ('SeekID', C_UNKNOWN),
    0x13ac: ('SeekPosition', C_UINT),

    0x6c: ('Void', C_UNKNOWN),  # Filler

    0x549a966: ('Info', C_ELEMENTS),
    0x33a4: ('SegmentUID', C_UNKNOWN),
    0xad7b1: ('TimestampScale', C_UINT),
    0x489: ('Duration', C_FLOAT),
    0x3ba9: ('Title', C_UTF8),
    0xd80: ('MuxingApp', C_UTF8),
    0x1741: ('WritingApp', C_UTF8),

    0x654ae6b: ('Tracks', C_ELEMENTS),
    0x2e: ('TrackEntry', C_ELEMENTS),
    0x57: ('TrackNumber', C_UINT),
    0x33c5: ('TrackUID', C_UINT),
    0x3: ('TrackType', C_UINT),
    0x1c: ('FlagLacing', C_UINT),
    0x2b59c: ('Language', C_STRING),
    0x6: ('CodecID', C_STRING),
    0x3e383: ('DefaultDuration', C_UINT),
    0x60: ('Video', C_ELEMENTS),
    0x30: ('PixelWidth', C_UINT),
    0x3a: ('PixelHeight', C_UINT),
    0x23a2: ('CodecPrivate', C_UNKNOWN),
    0x15b0: ('Colour', C_ELEMENTS),
    0x15b7: ('ChromaSitingHorz', C_UINT),
    0x15b8: ('ChromaSitingVert', C_UINT),

    0x254c367: ('Tags', C_ELEMENTS),
    0x3373: ('Tag', C_ELEMENTS),
    0x23c0: ('Targets', C_ELEMENTS),
    0x23c5: ('TagTrackUID', C_UINT),
    0x27c8: ('SimpleTag', C_ELEMENTS),
    0x5a3: ('TagName', C_UTF8),
    0x487: ('TagString', C_UTF8),

    0xf43b675: ('Cluster', C_ELEMENTS),
    0x67: ('Timestamp', C_UINT),
    0x23: ('SimpleBlock', C_UNKNOWN),

    0xc53bb6b: ('Cues', C_ELEMENTS),
    0x3b: ('CuePoint', C_ELEMENTS),
    0x33: ('CueTime', C_UINT),
    0x37: ('CueTrackPositions', C_ELEMENTS),
    0x77: ('CueTrack', C_UINT),
    0x71: ('CueClusterPosition', C_UINT),
    0x70: ('CueRelativePosition', C_UINT),
}

class EBMLDecoder(Decoder):
    def __init__(self, file, view):
        super(EBMLDecoder,self).__init__(file, view, big_endian=True)

    def run(self):
        with self.view.map('header'):
            self.header()
        #self.vset('_endheader', True)
        with self.view.map('body'):
            self.body()
        #self.vset('_endbody', True)
        tail = self.read()
        if tail:
            with self.view.map('tail'):
                self.hexdump(tail)

    def header(self):
        self.element()

    def body(self):
        self.element()

    def element(self):
        # ID
        elemid = self.vint()
        #self.vset('_id', elemid)
        # Data Size
        datasize = self.vint()
        #self.vset('_datasize', datasize)
        # Data
        name, ctype = elem_name.get(elemid) or ('%#x' % elemid, C_UNKNOWN)
        func = getattr(self, 'do_'+name, None)
        if func:
            func(name, datasize)
        else:
            self.generic(name, ctype, datasize)

    def container(self, name, size):
        with self.view.map(name):
            with self.substream(size):
                while True:
                    try:
                        self.element()
                    except EOFError:
                        #self.vset('_EOI_',True)
                        break

    do_EBML = container

    def do_SeekID(self, name, size):
        elem = self.vint()
        ename,_ = elem_name.get(elem, '%#x' % elem)
        self.vset(name, ename)

    def generic(self, name, ctype, size):
        if ctype == C_ELEMENTS:
            self.container(name, size)
        elif ctype == C_UINT:
            self.val_uint(name, size)
        elif ctype == C_FLOAT:
            self.val_float(name, size)
        elif ctype == C_STRING:
            value = self.read(size).decode('ascii')
            self.vset(name, value)
        elif ctype == C_UTF8:
            value = self.read(size).decode('utf8')
            self.vset(name, value)
        else:
            self.view.blob(name, self.read(size))

    def val_float(self, name, size):
        if size == 0:
            value = 0.0
        elif size == 4:
            value = self.f4()
        elif size == 8:
            value = self.f8()
        else:
            raise ValueError('float with size %d' % size)
        self.vset(name, value)

    def val_uint(self, name, size):
        if size == 0:
            value = 0
        elif size == 1:
            value = self.u1()
        elif size == 2:
            value = self.u2()
        elif size == 3:
            hi = self.u1()
            lo = self.u2()
            value = hi << 16 | lo
        elif size == 4:
            value = self.u4()
        else:
            raise NotImplementedError('uint with size %d' % size)
        self.vset(name, value)

    # Specific read methods
    def vint(self):
        """Read variable-sized integer"""
        b0 = self.u1()
        #self.vset('_VINT_b0', hex(b0))
        if b0 == 0:
            raise ValueError('Invalid 0 first octet of VINT')
        lenmask = 0x80
        value = b0
        olen = 1
        while b0 & lenmask == 0:
            value = value << 8 | self.u1()
            olen += 1
            lenmask >>= 1
        vmask = (1 << (7 * olen)) - 1
        value &= vmask
        if value == vmask:
            return None
        #self.vset('_VINT_hex', hex(value))
        return value

    # Output methods
    def hexdump(self, data, limit=256):
        for line in HexDumper(data[:limit]).iter_lines():
            offset, _, dump = line.partition(': ')
            self.vset(offset[1:].replace(' ','0'), dump)
        if len(data) > limit:
            self.vset('dump_size', len(data))

def main():
    from .viewer import PlainViewer
    import sys
    view = PlainViewer()
    with open(sys.argv[1],'rb') as f:
        dec = EBMLDecoder(f, view)
        dec.run()

if __name__=='__main__':
    main()
