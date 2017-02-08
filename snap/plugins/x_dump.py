import os
import re
import logging
from binaryornot.check import is_binary
import snapcraft.plugins.dump

logger = logging.getLogger(__name__)

def _replace(path, pattern, sub):
    cpat = re.compile(pattern)
    with open(path, 'r') as fo:
        filedata = fo.read()
    filedata, nsubs = (re.subn(cpat, sub, filedata))
    if nsubs:
        with open(path, 'w') as fo:
            fo.write(filedata)
        logger.info('Replaced "{}" in file {}'.format(pattern, path))

class XDumpPlugin(snapcraft.plugins.dump.DumpPlugin):

    def build(self):
        super().build()
        for root, dirs, files in os.walk(self.installdir):
            for f in files:
                fpath = os.path.join(root, f)
                if os.path.islink(fpath):
                    continue
                if is_binary(fpath):
                    continue
                if 'environment' in fpath:
                    _replace(fpath, '=/usr/', '=$SNAP/usr/')
                    _replace(fpath, ':/usr/', ':$SNAP/usr/')
                    _replace(fpath, '=/lib', '=$SNAP/lib')
                    _replace(fpath, ':/lib', ':$SNAP/lib')
                    with open(fpath, 'a') as fo:
                        if '.sh' in fpath:
                            export='export '
                        else:
                            export=''
                        fo.write(export + 'OPX_CFG_FILE_LOCATION=$SNAP/etc/opx\n')
                        fo.write(export + 'GOROOT=$SNAP/usr/lib/go-1.6\n')
                        fo.write(export + 'GOPATH=$SNAP\n')
                else:
                    _replace(fpath, '#!.*/usr/bin/', '#!/usr/bin/env ');
