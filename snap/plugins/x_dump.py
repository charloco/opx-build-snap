import os
import logging
from binaryornot.check import is_binary
import snapcraft.plugins.dump

logger = logging.getLogger(__name__)

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
                fo = open(fpath, 'r')
                try:
                    line = fo.readline()
                    if '#!' not in line:
                        continue
                finally:
                    fo.close()
                logger.info('Translate shebangs in ' + fpath)
                with open(fpath, 'r') as fo:
                    filedata = fo.read()
                filedata = filedata.replace('#! /usr/bin/python', '#!/usr/bin/env python')
                filedata = filedata.replace('#!/usr/bin/python', '#!/usr/bin/env python')
                filedata = filedata.replace('#! /usr/bin/bash', '#!/usr/bin/env bash')
                with open(fpath, 'w') as fo:
                    fo.write(filedata)
