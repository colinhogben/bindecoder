#!/usr/bin/python3
#=======================================================================
#       Decode AVI file
#
#       https://en.wikipedia.org/wiki/Resource_Interchange_File_Format
#       http://msdn2.microsoft.com/en-us/library/ms779636(VS.85).aspx
#=======================================================================
from decoder import Decoder, PlainViewer
from hexdumper import HexDumper

class AVIDecoder(Decoder):
    def __init__(self, file, view):
        super(AVIDecoder,self).__init__(file, view, big_endian=False)
        self.streamtype = None

    def run(self):
        self.chunk('RIFF')

    def chunks(self):
        while self.chunk():
            pass

    def chunk(self, expected=None):
        try:
            ckid = self.s4()
        except EOFError:
            return False
        if expected and ckid != expected:
            raise ValueError('Found %s chunk, expected %s' % (ckid, expected))
        size = self.u4()
        with self.substream(size):
            if ckid == 'LIST':
                ltype = self.s4()
                with self.view.map(ltype):
                    self.vset('_size', size)
                    method = getattr(self, 'do_'+ltype, None)
                    if method:
                        method()
                    self.chunks()
            else:
                with self.view.map(ckid):
                    self.vset('_size', size)
                    method = getattr(self, 'do_'+ckid, None)
                    if method:
                        method()
                    rest = self.read()
                    if rest:
                        self.view.blob('_rest', rest)
        return True

    # Chunk types
    def do_RIFF(self):
        ftype = self.s4()
        self.vset('type', ftype)
        self.chunks()

    def do_avih(self):
        self.u4('MicroSecPerFrame')
        self.u4('MaxBytesPerSec')
        self.u4('PaddingGranularity')
        self.u4('Flags')
        self.u4('TotalFrames')
        self.u4('InitialFrames')
        self.u4('Streams')
        self.u4('SuggestedBufferSize')
        self.u4('Width')
        self.u4('Height')
        self.read(16) # dwReserved[4]

    def do_strh(self):
        """Decode AVISTREAMHEADER"""
        self.streamtype = self.s4()
        self.vset('Type', self.streamtype)
        self.vset('Handler', self.s4())
        self.u4('Flags')
        self.u2('Priority')
        self.u2('Language')
        self.u4('InitialFrames')
        self.u4('Scale')
        self.u4('Rate')
        self.u4('Start')
        self.u4('Length')
        self.u4('SuggestedBufferSize')
        self.u4('Quality')
        self.u4('SampleSize')
        with self.view.map('Frame'):
            self.u2('left')
            self.u2('top')
            self.u2('right')
            self.vset('bottom', self.u2())

    def do_strf(self):
        if self.streamtype == 'vids':
            self.do_strf_video()
        elif self.streamtype == 'auds':
            self.do_strf_audio()

    def do_strf_video(self):
        """http://martchus.no-ip.biz/doc/tagparser/bitmapinfoheader_8h_source.html"""
        self.u4('size')
        self.u4('width')
        self.u4('height')
        self.u2('planes')
        self.u2('bitCount')
        self.vset('compression', self.s4())
        self.u4('imageSize')
        self.u4('horizontalResolution')
        self.u4('vertitalResolution')
        self.u4('clrUsed')
        self.u4('clrImportant')

    def do_strf_audio(self):
        """WAVEFORMATEX
        https://docs.microsoft.com/en-gb/previous-versions/dd757713(v=vs.85)
        """
        ftag = self.u2('FormatTag')
        self.u2('Channels')
        self.u4('SamplesPerSec')
        self.u4('AvgBytesPerSec')
        self.u2('BlockAlign')
        self.u2('BitsPerSample')
        self.u2('Size')

    movi_map = dict(db='Uncompressed video frame',
                    dc='Compressed video frame',
                    pc='Palette change',
                    wb='Audio data')

    def do_movi(self):
        snty = self.s4()
        sn, ty = snty[:2], snty[2:]
        self.vset('stream', int(sn))
        self.vset('type', '%s (%s)' % (ty, self.movi_map.get(ty, '?')))
        size = self.u4()
        self.vset('_size', size)
        self.hexdump(self.read())

    def do_idx1(self):
        """Decode AVIOLDINDEX"""
        with self.view.array('Index'):
            i = 0
            while True:
                try:
                    ChunkId = self.s4()
                except EOFError:
                    break
                with self.view.map(i):
                    self.vset('ChunkId', ChunkId)
                    self.u4('Flags')
                    self.u4('Offset')
                    self.u4('Size')
                i += 1

    def do_vprp(self):
        self.u4('VideoFormatToken')
        self.u4('VideoStandard')
        self.u4('VerticalRefreshRate')
        self.u4('HTotalInT')
        self.u4('VTotalInLines')
        #self.u4('FrameAspectRatio')
        ary = self.u2()
        arx = self.u2()
        self.vset('FrameAspectRatio', '%d:%d' % (arx,ary))
        self.u4('FrameWidthInPixels')
        self.u4('FrameHeightInLines')
        fpf = self.u4('FieldPerFrame')
        # VIDEO_FIELD_DESC FieldInfo[FieldPerFrame]
        with self.view.array('FieldInfo'):
            for f in range(fpf):
                with self.view.map(f):
                    self.u4('CompressedBMHeight')
                    self.u4('CompressedBMWidth')
                    self.u4('ValidBMHeight')
                    self.u4('ValidBMWidth')
                    self.u4('ValidBMXOffset')
                    self.u4('ValidBMYOffset')
                    self.u4('VideoXOffsetInT')
                    self.u4('VideoYValidStartLine')

    # Output methods
    def hexdump(self, data, limit=256):
        for line in HexDumper(data[:limit]).iter_lines():
            offset, _, dump = line.partition(': ')
            self.vset(offset[1:].replace(' ','0'), dump)
        if len(data) > limit:
            self.vset('dump_size', len(data))

    # AVI-specific low-level items
    def s4(self):
        """Read a 4-byte string (fourcc)"""
        b4 = self.read(4)
        return b4.decode('iso-8859-1')

def main():
    import sys
    view = PlainViewer()
    with open(sys.argv[1],'rb') as f:
        dec = AVIDecoder(f, view)
        dec.run()

main()
