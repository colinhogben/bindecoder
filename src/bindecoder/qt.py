#=======================================================================
"""
Decode Quicktime (.mov) file
"""
#	Also MPEG-4 (mp42) and JPEG-2000 (isom) (?)
#	ISO/IEC 14496-12:2004 (MPEG-4 Part 12: ISO base media file format)
#
#	https://en.wikipedia.org/wiki/QuickTime_File_Format
#	https://developer.apple.com/library/archive/documentation/QuickTime/QTFF/QTFFPreface/qtffPreface.html
#=======================================================================
from .decoder import Decoder
from .hexdumper import HexDumper

class QtDecoder(Decoder):
    def __init__(self, file, view):
        super(QtDecoder,self).__init__(file, view, big_endian=True)

    def run(self):
        self.atoms()

    def atoms(self):
        while self.atom():
            pass

    def atom(self):
        try:
            size = self.u4()
        except EOFError:
            return False
        if size == 0:
            return False
        atype = self.s4()
        with self.substream(size - 8):

            with self.view.map("'%s'" % atype):
                self.vset('_size', size)
                method = getattr(self, 'do_'+atype, None)
                if method:
                    method()
                rest = self.read()
                if rest:
                    self.hexdump(rest)
        return True

    #    self.decode
    do_moov = atoms
    do_trak = atoms
    do_mdia = atoms
    do_minf = atoms
    #do_dinf = atoms
    do_stbl = atoms
    do_udta = atoms

    def atom_data(self):
        self.atom()
        self.hexdump(self.read())

    do_dinf = atom_data

    def do_ftyp(self):
        brand = self.s4()       # 'qt  ' or 'mp42'
        self.vset('brand', brand)
        self.vset('minor', self.u4())
        with self.view.array('compatible'):
            i = 0
            while True:
                try:
                    comp = self.s4()
                except EOFError:
                    break
                if comp != '\0\0\0\0':
                    self.vset(i, comp)
                i += 1

    def do_tkhd(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        self.vset('creation_time', self.u4())
        self.vset('modification_time', self.u4())
        self.vset('track_id', self.u4())
        self.read(4)               # Reserved
        self.vset('duration', self.u4())
        self.read(8)               # Reserved
        self.vset('layer', self.u2())
        self.vset('alternate_group', self.u2())
        self.vset('volume', self.u2())
        self.read(2)               # Reserved
        #m = [s.v4() for i in range(9)]
        #self.put('matrix = ( %8g %8g %8g )' % (m[0], m[1], m[2]/16384))
        #self.put('         ( %8g %8g %8g )' % (m[3], m[4], m[5]/16384))
        #self.put('         ( %8g %8g %8g )' % (m[6], m[7], m[8]/16384))
        self.matrix('matrix')
        self.vset('track_width', self.v4())
        self.vset('track_height', self.v4())
        self.hexdump(self.read())

    def do_hdlr(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        self.vset('component_type', self.s4())
        self.vset('component_subtype', self.s4())
        self.read(12)              # Reserved (manuf, flags, flagsmask)
        self.hexdump(self.read())

    def do_mdhd(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        self.vset('creation_time', self.u4())
        self.vset('modification_time', self.u4())
        self.vset('timescale', self.u4())
        self.vset('duration', self.u4())
        self.vset('language', self.u2())
        self.vset('quality', self.u2())
        self.hexdump(self.read())

    def do_mvhd(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        self.vset('creation_time', self.u4())
        self.vset('modification_time', self.u4())
        self.vset('timescale', self.u4())
        self.vset('duration', self.u4())
        self.vset('preferred_rate', self.fix32())
        self.vset('preferred_volume', self.u2()) # FIXME fixed 16
        self.read(10)
        self.matrix('matrix')
        self.vset('preview_time', self.u4())
        self.vset('poster_time', self.u4())
        self.vset('poster_duration', self.u4())
        self.vset('selection_time', self.u4())
        self.vset('selection_duration', self.u4())
        self.vset('current_time', self.u4())
        self.vset('next_track_id', self.u4())        

    def do_vmhd(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        self.vset('graphics_mode', self.u2())
        r, g, b = [self.u2() for i in range(3)]
        self.vset('opcolor', '(%d, %d, %d)' % (r, g, b))

    def do_dref(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        nent = self.u4()
        with self.view.array('entries'):
            for i in range(nent):
                with self.view.array(i):
                    esize = self.u4()
                    self.vset('type', self.s4())
                    evf = self.u4()
                    self.vset('version', evf >> 24)
                    self.vset('flags', evf & 0xffffff)
                    edata = self.read(esize - 12)
                    if edata:
                        self.hexdump(edata)

    def do_stsd(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        nent = self.u4()
        for i in range(nent):
            with self.view.map('entry[%d]' % i):
                esize = self.u4()
                self.vset('size', esize)
                self.vset('format', self.s4())
                self.read(6)       # Reserved
                self.vset('data_reference_index', self.u2())
                self.hexdump(self.read(esize - 16))

    def do_stts(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        nent = self.u4()
        for i in range(nent):
            with self.view.map('entry[%d]' % i):
                self.vset('sample_count', self.u4())
                self.vset('sample_duration', self.u4())

    def do_stss(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        nent = self.u4()
        for i in range(nent):
            self.vset('sample[%d]' % i, self.u4())

    def do_stsc(self):
        """Map sample numbers to chunk numbers"""
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        nent = self.u4()
        for i in range(nent):
            self.vset('sample[%d].first' % i, self.u4())
            self.vset('sample[%d].samples' % i, self.u4())
            self.vset('sample[%d].descID' % i, self.u4())
        
    def do_stsz(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        sampsize = self.u4()
        self.vset('sample_size', sampsize)
        if sampsize == 0:       # Use table
            nent = self.u4()
            self.vset('nent', nent)
            for i in range(nent):
                self.vset('size[%d]' % i, self.u4())
        else:
            # Junk?
            self.hexdump(self.read())

    def do_stco(self):
        vf = self.u4()
        self.vset('version', vf >> 24)
        self.vset('flags', vf & 0xffffff)
        nent = self.u4()
        for i in range(nent):
            self.vset('offset[%d]' % i, self.u4())

    def matrix(self, name):
        for row in range(3):
            v0, v1, v2 = self.fix32(16), self.fix32(16), self.fix32(30)
            self.vset('%s_%d' % (name, row),
                      '( %8g %8g %8g )' % (v0, v1, v2))

    # Output methods
    def hexdump(self, data, limit=256):
        for line in HexDumper(data[:limit]).iter_lines():
            offset, _, dump = line.partition(': ')
            self.vset(offset[1:].replace(' ','0'), dump)
        if len(data) > limit:
            self.vset('dump_size', len(data))

    # Qt-specific low-level items
    def s4(self):
        """Read a 4-byte string (fourcc)"""
        b4 = self.read(4)
        return b4.decode('iso-8859-1')

    def v4(self):
        """Read unsigned fixed-point 16.16 bit value"""
        val = self.u4()
        return val / 65536.

    def fix32(self, fracbits=16):
        """Read a fixed-point real"""
        val = self.i4()
        return float(val) / (1 << fracbits)

def main():
    from .viewer import PlainViewer
    import sys
    view = PlainViewer()
    with open(sys.argv[1],'rb') as f:
        dec = QtDecoder(f, view)
        dec.run()

if __name__=='__main__':
    main()
