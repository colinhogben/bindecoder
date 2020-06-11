#!/usr/bin/python3
#=======================================================================
#       Decode JPEG (JFIF) file
#	https://en.wikipedia.org/wiki/JPEG
#	http://vip.sugovica.hu/Sardi/kepnezo/JPEG%20File%20Layout%20and%20Format.htm
#=======================================================================
from decoder import Decoder, PlainViewer
from hexdumper import HexDumper

marker_name = {
    0xC0:'SOF0',
    0xC2:'SOF2',
    0xC4:'DHT',
    0xD0:'RST0',
    0xD1:'RST1',
    0xD2:'RST2',
    0xD3:'RST3',
    0xD4:'RST4',
    0xD5:'RST5',
    0xD6:'RST6',
    0xD7:'RST7',
    0xD8:'SOI',
    0xD9:'EOI',
    0xDA:'SOS',
    0xDB:'DQT',
    0xDD:'DRI',
    0xE0:'APP0',
    0xE1:'APP1',
    0xE2:'APP2',
    0xE3:'APP3',
    0xE4:'APP4',
    0xE5:'APP5',
    0xE6:'APP6',
    0xE7:'APP7',
    0xE8:'APP8',
    0xE9:'APP9',
    0xEA:'APP10',
    0xEB:'APP11',
    0xEC:'APP12',
    0xED:'APP13',
    0xEE:'APP14',
    0xEF:'APP15',
    0xFE:'COM',
    }

class JpgDecoder(Decoder):
    def __init__(self, file, view):
        super(JpgDecoder,self).__init__(file, view, big_endian=True)

    def run(self):
        while self.segment():
            pass

    def segment(self):
        ff = self.u1()
        if ff != 0xff:
            raise ValueError('Expected FF byte, found %#02x' % ff)
        marker = self.u1()
        name = marker_name.get(marker) or '%#02X' % marker
        lo = marker & 0xf
        if 0xD0 <= marker <= 0xD9:
            # No content
            pass
        else:
            size = self.u2()
            with self.view.map(name):
                self.vset('_size', '%#x' % size)
                if name == 'APP0':
                    with self.substream(size - 2):
                        ident = self.sz()
                        self.vset('identifier', ident)
                        if ident == 'JFIF':
                            vh, vl = self.u1(), self.u1()
                            self.vset('version', (vh, vl))
                            self.vset('units', self.u1())
                            self.vset('xdensity', self.u2())
                            self.vset('ydensity', self.u2())
                            xthumb, ythumb = self.u1(), self.u1()
                            self.vset('xthumbnail', xthumb)
                            self.vset('ythumbnail', ythumb)
                            if xthumb * ythumb:
                                with self.view.map('thumbnail_rgb'):
                                    self.hexdump(self.read(3*xthumb*ythumb))
                        self.hexdump(self.read())
                elif name == 'DQT':
                    with self.substream(size - 2):
                        qt = self.u1()
                        self.vset('qt_number', qt & 0x0f)
                        prec = 8 << (qt >> 4)
                        self.vset('precision', prec)
                        self.hexdump(self.read())
                elif name == 'SOF0':
                    with self.substream(size - 2):
                        self.vset('bpp', self.u1())
                        self.vset('width', self.u2())
                        self.vset('height', self.u2())
                        ncc = self.u1()
                        with self.view.array('colour_component'):
                            for i in range(ncc):
                                with self.view.map(i):
                                    self.vset('id', self.u1())
                                    vh = self.u1()
                                    self.vset('vert_factor', vh & 0xf)
                                    self.vset('horz_factor', vh >> 4)
                                    self.vset('quant_table', self.u1())
                        self.hexdump(self.read())
                elif name == 'DHT':
                    with self.substream(size - 2):
                        ht = self.u1()
                        self.vset('nht', ht & 0xf)
                        self.vset('type', 'AC' if ht & 0x10 else 'DC')
                        n = 0
                        with self.view.array('nsym'):
                            for i in range(16):
                                nsym = self.u1()
                                self.vset(i+1, nsym)
                                n += nsym
                        self.vset('_totsym', n)
                        for i in range(n):
                            pass
                        self.hexdump(self.read())
                elif name == 'SOS':
                    with self.substream(size - 2):
                        ncomp = self.u1()
                        self.vset('ncomp', ncomp)
                        with self.view.array('components'):
                            for i in range(ncomp):
                                with self.view.map(i):
                                    cid = self.u1()
                                    self.vset('cid',
                                              {1:'Y',2:'Cb',3:'Cr',4:'I',5:'Q'}.get(cid,cid))
                                    huff = self.u1()
                                    self.vset('AC_table', huff & 0x0f)
                                    self.vset('DC_table', huff >> 4)
                        self.hexdump(self.read())
                    with self.view.map('entropy_coded'):
                        self.hexdump(self.read(256))
                else:
                    self.hexdump(self.read(size - 2))
        return True

    # Specific read methods
    def sz(self):
        """Read NUL-terminated string"""
        tok = b''
        while True:
            b = self.read(1)
            if b == b'\0':
                break
            tok += b
        return tok.decode('ascii')

    # Output methods
    def hexdump(self, data, limit=256):
        for line in HexDumper(data[:limit]).iter_lines():
            offset, _, dump = line.partition(': ')
            self.vset(offset[1:].replace(' ','0'), dump)
        if len(data) > limit:
            self.vset('dump_size', len(data))

def main():
    import sys
    view = PlainViewer()
    with open(sys.argv[1],'rb') as f:
        dec = JpgDecoder(f, view)
        dec.run()

main()
