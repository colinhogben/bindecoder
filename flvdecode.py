#!/usr/bin/python3
#=======================================================================
#       Decode FLV file
#
#       https://en.wikipedia.org/wiki/Flash_Video
#       https://www.adobe.com/content/dam/acom/en/devnet/flv/video_file_format_spec_v10.pdf
#=======================================================================
from decoder import Decoder, PlainViewer
import struct
from hexdumper import HexDumper

class FLVDecoder(Decoder):
    def __init__(self, file, view):
        super(FLVDecoder,self).__init__(file, view, big_endian=True)

    def run(self):
        # FLV header
        sig = self.read(3)
        if sig != b'FLV':
            raise ValueError('Not a FLV file')
        self.putv('Version', self.u1())
        tf = self.u1()
        assert (tf & 0b11111010) == 0
        self.putv('AudioTags', (tf & 4) != 0)
        self.putv('VideoTags', (tf & 1) != 0)
        doff = self.u4()
        self.putv('DataOffset', doff)
        self.read(doff - self.pos)
        with self.view.array('Tag'):
            i = 0
            while True:
                with self.view.map(i):
                    # Sequence of back-pointers
                    self.putv('PreviousTagSize', self.u4())
                    self.tag()
                    #break
                i += 1

    def tag(self):
        tagtype = self.u1()
        if tagtype == 8:
            self.putv('TagType', 'audio')
        elif tagtype == 9:
            self.putv('TagType', 'video')
        elif tagtype == 18:
            self.putv('TagType', 'script data')
        else:
            self.putv('TagType', tagtype)
        dsize = self.ui24()
        self.putv('DataSize', dsize)
        self.putv('Timestamp', self.ui24())
        self.putv('TimestampExtended', self.u1())
        self.putv('StreamID', self.ui24())
        with self.substream(dsize):
            if tagtype == 18:
                self.script_data()
            elif tagtype == 9:
                self.video_data()
            self.hexdump(self.read())

    frametype_map = {1:'keyframe',
                     2:'inter frame',
                     3:'disposable inter frame',
                     4:'generated keyframe',
                     5:'video info/command frame'}
    codecid_map = {1:'JPEG',
                   2:'Sorenson H.263',
                   3:'Screen video',
                   4:'On2 VP6',
                   5:'On2 VP6 with alpha channel',
                   6:'Screen video version 2',
                   7:'AVC'}

    def video_data(self):
        with self.view.map('VideoData'):
            tid = self.u1()
            ftype = tid >> 4
            codecid = tid & 0xf
            self.putv('FrameType', self.frametype_map.get(ftype,ftype))
            self.putv('CodecID', self.codecid_map.get(codecid,codecid))
            
    def script_data(self):
        with self.view.array('ScriptData'):
            i = 0
            while True:
                nt = self.u1()
                if nt == 0:
                    endval = self.u2()
                    assert endval == 9
                    break
                if nt != 2:
                    raise ValueError('Expected 2 SCRIPTDATANAME')
                nlen = self.u2()
                name = self.read(nlen).decode('ascii')
                with self.view.map(i):
                    if nt not in (2, 12):
                        raise ValueError('Unexpected type %d for name' % nt)
                    self.putv('Name', name)
                    vt, value = self.obj()
                    if vt == 8: # ECMAarray
                        alen = value
                        with self.view.map('Value'):
                            for i in range(alen):
                                klen = self.u2()
                                key = self.read(klen).decode('ascii')
                                xt, xvalue = self.obj()
                                self.putv(key, xvalue)
                    else:
                        self.putv('Value', value)
                #nlen = self.u2()
                #if nlen == 0:
                #    # 00 00 09 = SCRIPTDATAOBJECTEND

    def obj(self):
        otype = self.u1()
        if otype == 0:          # Number
            value = self.double()
            if value == int(value):
                value = int(value)
        elif otype == 1:        # Boolean
            value = self.u1()
        elif otype == 2:        # String
            nlen = self.u2()
            value = self.read(nlen).decode('ascii')
        elif otype == 8:        # ECMA array
            value = self.u4()   # Length
        else:
            raise NotImplementedError('Value type %d' % otype)
        return otype, value

    # Output methods
    def hexdump(self, data, limit=256):
        for line in HexDumper(data[:limit]).iter_lines():
            offset, _, dump = line.partition(': ')
            self.putv(offset[1:].replace(' ','0'), dump)
        if len(data) > limit:
            self.putv('dump_size', len(data))
                      
    def putv(self, name, value):
        self.view.set(name, value)

    # FLV-specific low-level items
    def ui24(self):
        hi = self.u1()
        lo = self.u2()
        return (hi << 16) | lo

    def double(self):
        value, = struct.unpack('>d', self.read(8))
        return value

    def s4(self):
        """Read a 4-byte string (fourcc)"""
        b4 = self.read(4)
        return b4.decode('iso-8859-1')

def main():
    import sys
    view = PlainViewer()
    with open(sys.argv[1],'rb') as f:
        dec = FLVDecoder(f, view)
        dec.run()

main()
