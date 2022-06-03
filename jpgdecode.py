#!/usr/bin/python3
#=======================================================================
#       Decode JPEG (JFIF) file
#       https://en.wikipedia.org/wiki/JPEG
#       http://vip.sugovica.hu/Sardi/kepnezo/JPEG%20File%20Layout%20and%20Format.htm
#       https://users.cs.cf.ac.uk/Dave.Marshall/Multimedia/node234.html
#       https://johnloomis.org/ece563/notes/compression/jpeg/tutorial/jpegtut1.html
#       https://www.w3.org/Graphics/JPEG/itu-t81.pdf
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
    def __init__(self, file, view, with_ecd=False):
        super(JpgDecoder,self).__init__(file, view, big_endian=True)
        self.with_ecd = with_ecd

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
                        elif ident == 'AVI1':
                            # Example from borescope
                            # 0000 = ' 01 01 01 00  78 00 78 00  00 00 00 00  00 00 00 00  ....x.x.........'
                            # 0010 = ' 00 00 00 00  00 00 00 00  00 00                     ..........'
                            # Some clues from http://www.gdcl.co.uk/2013/05/02/Motion-JPEG.html
                            pol = self.u1()
                            self.vset('polarity', pol)
                            # Remainder unknown
                        self.hexdump(self.read())
                elif name == 'APP1':
                    with self.substream(size - 2):
                        atype = self.read(4)
                        if atype == b'Exif':
                            zz = self.read(2)
                            with self.substream(size - 8):
                                tiff = TIFFDecoder(self.stream, self.view)
                                tiff.run()
                        else:
                            self.hexdump(self.read())
                elif name == 'APP13':
                    with self.substream(size - 2):
                        app = self.read(14)
                        self.vset('app', app)
                        if app == b'Photoshop 3.0\0':
                            type = self.read(4)
                            self.vset('type', type)
                            if type == b'8BIM':
                                with self.endian(True):
                                    itag = self.u2('itag')
                                    nlen = self.u1()
                                    tag_name = self.read(nlen)
                                    if nlen % 2 == 0:
                                        self.read(1) # Align
                                    size = self.u4('size')
                                    id = self.u1('id')
                                    if id == 0x1c:
                                        rec = self.u1('rec')
                                        tag = self.u1('tag')
                                        len = self.u2('len')
                                        if tag == 25:
                                            # Keywords
                                            kw = self.read(len).rstrip(b'\0')
                                            self.vset('keywords', kw)
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
                elif name == 'DRI':
                    with self.substream(size - 2):
                        self.vset('restart_interval', self.u2())
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
                    if not self.with_ecd:
                        return False
                    with self.view.map('entropy_coded'):
                        # ff00 at:
                        # 44e
                        # 674
                        # 6ae
                        # 71f
                        # 7a6
                        # 99b
                        # 9bf
                        # a57
                        # b2a
                        # bf3
                        # c9b
                        # Then ffd9
                        self.hexdump(self.read())
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

# https://www.awaresystems.be/imaging/tiff/tifftags/baseline.html
# https://exiftool.org/TagNames/EXIF.html
tiff_tag = {
    #0x106: 'PhotometricInterpretation',
    0x10e: 'ImageDescription',
    0x10f: 'Make',
    0x110: 'Model',
    0x112: 'Orientation',
    0x11a: 'XResolution',
    0x11b: 'YResolution',
    0x128: 'ResolutionUnit',
    0x131: 'Software',
    0x132: 'DateTime',
    0x201: 'ThumbnailOffset',
    0x202: 'ThumbnailLength',
    0x212: 'YCbCrSubSampling',
    0x213: 'YCbCrPositioning',
    0x8298: 'Copyright',
    0x829a: 'ExposureTime',
    0x829d: 'FNumber',
    0x8769: 'ExifIFD',
    0x8822: 'ExposureProgram',
    0x8827: 'ISOSpeedRatings',
    0x8830: 'SensitivityType',
    0x8832: 'RecommendedExposureIndex',
    0x9000: 'ExifVersion',
    0x9003: 'DateTimeOriginal',
    0x9004: 'DateTimeDigitized',
    0x9101: 'ComponentsConfiguration',
    0x9102: 'CompressedBitsPerPixel',
    0x9201: 'ShutterSpeedValue',
    0x9202: 'ApertureValue',
    0x9203: 'BrightnessValue',
    0x9204: 'ExposureBiasValue',
    0x9205: 'MaxApertureValue',
    0x9207: 'MeteringMode',
    0x9208: 'LightSource',
    0x9209: 'LightSource',
    0x920a: 'FocalLength',
    0x927c: 'MakerNote',
    0x9286: 'UserComment',
    0xa000: 'FlashpixVersion',
    0xa001: 'ColorSpace',
    0xa002: 'PixelXDimension',
    0xa003: 'PixelYDimension',
    0xa005: 'InteroperabilityIFD',
    0xa20e: 'FocalPlaneXResolution',
    0xa20f: 'FocalPlaneYResolution',
    0xa210: 'FocalPlaneResolutionUnit',
    0xa217: 'SensingMethod',
    0xa300: 'FileSource',
    0xa301: 'SceneType',
    0xa401: 'CustomRendered',
    0xa402: 'ExposureMode',
    0xa403: 'WhiteBalance',
    0xa404: 'DigitalZoomRatio',
    0xa406: 'SceneCaptureType',
    0xa40a: 'Sharpness',
    0xa420: 'ImageUniqueID',
    }

def decode_ifd(self, ifdpos, base=0):
    """Mixin to decode IFD (EXIF) data.

    Offsets for string tags are relative to the start of the stream.
    In TIFF & JPEG files, there is a preamble with endianness etc.,
    whereas in AVI.strd.AVIF the offsets are from the nifd count.
    """
    self.seek(ifdpos)
    nifd = self.u2('_nifd')
    with self.view.map('IFD'):
        for i in range(nifd):
            self.stream.seek(ifdpos + 2 + 12*i)
            tag = self.u2()
            ftype = self.u2()
            count = self.u4()
            tagname = tiff_tag.get(tag,None) or 'tag_%#x' % tag
            if ftype == 1: # BYTE
                assert count == 1
                value = self.u1()
                value = 'BYTE[%d]@%d' % (count, offset)
            elif ftype == 2: # ASCII
                offset = self.u4()
                self.stream.seek(base + offset)
                vbytes = self.read(count)
                value = vbytes.decode('ascii').rstrip('\0')
                #value = 'ASCII[%d]@%d' % (count, offset)
            elif ftype == 3: # SHORT
                if count == 1:
                    value = self.u2()
                else:
                    value = [self.u2() for i in range(count)]
            elif ftype == 4: # LONG
                assert count == 1
                value = self.u4()
                #value = 'LONG[%d]@%d' % (count, offset)
            elif ftype == 5: # RATIONAL
                offset = self.u4()
                self.stream.seek(base + offset)
                num = self.u4()
                den = self.u4()
                value = '%d/%d' % (num, den)
            elif ftype == 7:  # UNDEFINED
                if count > 4:
                    offset = self.u4('_offset')
                    self.seek(base + offset)
                try:
                    value = self.read(count)
                except EOFError:
                    value = None
            elif ftype == 10: # SRATIONAL
                offset = self.u4()
                self.stream.seek(base + offset)
                num = self.i4()
                den = self.i4()
                value = '%d/%d' % (num, den)
            else:
                with self.view.map(i):
                    self.vset('tag', tagname)
                    self.vset('ftype', ftype)
                    self.vset('count', count)
                    self.u4('offset')
                continue
                #raise ValueError('Unexpected field type %d' % ftype)
            if tagname in ('ExifIFD','XXInteroperabilityIFD'):
                # InteroperabilityIFD broken or other layout?
                self.vset('_inner', value)
                with self.view.map(tagname):
                    decode_ifd(self, base + value, base)
            else:
                self.vset(tagname, value)

class TIFFDecoder(Decoder):
    def __init__(self, stream, view):
        ee = stream.read(2)
        if ee == b'II':
            super(TIFFDecoder,self).__init__(stream, view, big_endian=False)
        elif ee == b'MM':
            super(TIFFDecoder,self).__init__(stream, view, big_endian=True)
        else:
            raise ValueError('Invalid TIFF header: expected II or MM')
        vv = self.u2()
        if vv != 42:
            raise ValueError('Expected 42 after TIFF endian header')

    def run(self):
        ifdpos = self.u4('_ifdpos')
        self.vset('_at', self.stream.tell())
        # Must be >= 8, i.e. what we've read so far
        decode_ifd(self, ifdpos)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('-e','--ecd','--entropy-coded-data', action='store_true',
                    help='Dump entry-coded data')
    ap.add_argument('jpgfile',
                    help='JPEG file to dump')
    args = ap.parse_args()
    view = PlainViewer()
    with open(args.jpgfile,'rb') as f:
        dec = JpgDecoder(f, view, with_ecd=args.ecd)
        dec.run()

if __name__=='__main__':
    main()
