import os
import re
import logging
from binaryornot.check import is_binary
import snapcraft.plugins.dump

logger = logging.getLogger(__name__)

def _replace(path, pattern, sub, ignore_if_file_contains=''):
    with open(path, 'r') as fo:
        filedata = fo.read()
    if ignore_if_file_contains:
        if re.search(ignore_if_file_contains, filedata) != None:
            return
    cpat = re.compile(pattern)
    filedata, nsubs = (re.subn(cpat, sub, filedata))
    if nsubs:
        with open(path, 'w') as fo:
            fo.write(filedata)
        logger.warn('Replaced {} of "{}" in file {}'.format(nsubs, pattern, path))

class XDumpPlugin(snapcraft.plugins.dump.DumpPlugin):

    def build(self):
        super().build()
        for root, dirs, files in os.walk(self.installdir):
            for f in files:
                fpath = os.path.join(root, f)
                if os.path.islink(fpath):
                    continue
                if is_binary(fpath):
                    if ((self.name == 'opx-broadcom-sai') &
                        fpath.endswith('libsai.so.1.0') &
                        (not os.path.islink(fpath[:-2]))):
                        os.symlink('libsai.so.1.0', fpath[:-2])
                        logger.warn('Add symlink {} ==> {}'.format('libsai.so.1', fpath))
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
                        fo.write(export + 'OPX_INSTALL_PATH=$SNAP\n')
                        fo.write(export + 'OPX_DATA_PATH=$SNAP_DATA\n')
                        fo.write(export + 'OPX_CFG_FILE_LOCATION=$SNAP/etc/opx\n')
                        fo.write(export + 'CPS_API_METADATA_PATH=$SNAP/usr/lib/opx/cpsmetadata\n')
                        fo.write(export + 'GOROOT=$SNAP/usr/lib/go-1.6\n')
                        fo.write(export + 'GOPATH=$SNAP\n')
                        logger.warn('Add Snap-specific environment vars to {}'.format(fpath))
                else:
                    _replace(fpath, '^#!.*?/usr/bin/bash', '#!/usr/bin/env bash')
                    _replace(fpath, '^#!.*?/usr/bin/python', '#!/usr/bin/env python')
                    if fpath.endswith('.sh') or fpath.endswith('base_ip'):
                        _replace(fpath, '/usr/bin/', '$SNAP/usr/bin/', '\$SNAP/usr/bin/')
                        _replace(fpath, '/etc/opx/', '$SNAP/etc/opx/', '\$SNAP/etc/opx/')
                        _replace(fpath, '/usr/lib/', '$SNAP/usr/lib/', '\$SNAP/usr/lib/')
                        _replace(fpath, '/var/run/', '$SNAP_DATA/var/run/', '\$SNAP_DATA/var/run/')
