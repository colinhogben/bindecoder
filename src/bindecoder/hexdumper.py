#=======================================================================
"""
Render bytes as hexadecimal plus ASCII
"""
#=======================================================================
import sys

class HexDumper(object):
    """Render a block of bytes as hexadecimal plus ASCII"""
    def __init__(self, data, chunk=4, offset=0):
        self.data = data
        self.chunksize = chunk
        self.offset = offset

    def iter_hunks(self):
        """Iterate over hunks of up to 16 bytes"""
        if hasattr(self.data, 'read'):
            while True:
                hunk = self.data.read(16)
                if not hunk:
                    break
                yield hunk
        else:
            for pos in range(0, len(self.data), 16):
                yield self.data[pos:pos+16]

    def iter_lines(self):
        """Iterate over 16-byte hunks rendered as hex+ASCII lines"""
        pos = 0
        for hunk in self.iter_hunks():
            bhunk = [ord(hunk[i:i+1])  for i in range(len(hunk))]
            # Compromise on field size; get shift after a megabyte
            spos = '%5x' % (self.offset + pos)
            sbytes = ''
            for i in range(16):
                if i % self.chunksize == 0:
                    sbytes += ' '
                if i < len(hunk):
                    sbytes += '%02x ' % bhunk[i]
                else:
                    sbytes += '   '
            ascii = ''
            for b in bhunk:
                ascii += chr(b) if 32 <= b < 127 else '.'
            line = '%s: %s %s' % (spos, sbytes, ascii)
            yield line
            pos += 16

    def write(self, file=sys.stdout):
        """Write as hex+ASCII to a file-like object (default: stdout)"""
        for line in self.iter_lines():
            print(line, file=file)

if __name__=='__main__':
    if len(sys.argv) > 2:
        print('Usage: %s [file]' % sys.argv[0],
              file=sys.stderr)
        sys.exit(2)
    if len(sys.argv) == 2:
        with open(sys.argv[1],'rb') as f:
            hd = HexDumper(f)
            hd.write()
    else:
        import os
        with os.fdopen(sys.stdin.fileno(), 'rb') as f:
            hd = HexDumper(f)
            hd.write()
