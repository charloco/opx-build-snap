#!/usr/bin/env python

#
# Copyright (c) 2017 Extreme Networks, Inc.
#

import os
import sys
import time
import re
import glob
import subprocess

# This class represents a systemctl service
class Service(object):

    def __service_name(self, service):
        return service.split('.')[0]

    def __snapify_line(self, line):
        line = line.replace('/etc', self.snap + '/etc')
        line = line.replace('/usr', self.snap + '/usr')
        line = line.replace('/var', self.snapdata + '/var')
        return line

    def __expand_line(self, line):
        line = line.replace('$SNAP_DATA', self.snapdata)
        line = line.replace('$SNAP', self.snap)
        return line

    def __create_dir(self, newdir, mode=0777):
        if newdir.startswith("-"):
            newdir = newdir[1:]
        if not os.path.isdir(newdir):
            if self.debug:
                print 'Creating dir {} with mode 0{:o}'.format(newdir, mode)
            os.makedirs(newdir, mode)

    def __append_cmd(self, cmds, newcmd):
        if not newcmd:
            while len(cmds) > 0:
                cmds.remove(cmds[0])
        else:
            cmds.append(newcmd)

    # Parse each line in a service file.
    # This is an extremely lightweight service manager.  We only process
    # those lines that are relevant to a service running inside a Snap.
    def __parse_service_line( self, line ):
        line = line.strip()
        ciline = line.lower()
        line = self.__snapify_line(line)
        if not line:
            return
        elif line.startswith('#'):
            return
        elif bool(re.search('\[(unit|service|install)\].*', ciline, re.IGNORECASE)):
            return
        elif ciline.startswith('limitnofile='):
            return
        elif ciline.startswith('defaultdependencies='):
            return
        elif ciline.startswith('successexitstatus='):
            return
        elif ciline.startswith('wantedby='):
            return
        elif ciline.startswith('limitcore='):
            return
        elif ciline.startswith('documentation='):
            return
        elif ciline.startswith('remainafterexit='):
            return
        elif ciline.startswith('timeoutstopsec='):
            return
        elif ciline.startswith('restart='):
            return
        elif ciline.startswith('user='):
            return
        elif ciline.startswith('group='):
            return
        elif ciline.startswith('protectsystem='):
            return
        elif ciline.startswith('privatetmp='):
            return
        elif ciline.startswith('privatedevices='):
            return
        elif ciline.startswith('protecthome='):
            return
        elif ciline.startswith('capabilityboundingset='):
            return
        elif ciline.startswith('description='):
            self.descr = line.split('=',1)[-1]
        elif ciline.startswith('after='):
            self.after = line.split('=',1)[-1]
            if self.after == 'systemd-modules-load.service':
                self.after = ''
            elif self.after == 'network.target':
                self.after = ''
        elif ciline.startswith('before='):
            self.before = line.split('=',1)[-1]
        elif ciline.startswith('wants='):
            self.wants = line.split('=',1)[-1]
        elif ciline.startswith('requires='):
            self.requires = line.split('=',1)[-1]
        elif ciline.startswith('killsignal='):
            self.killsig = '-' + line.split('=',1)[-1]
        elif ciline.startswith('environmentfile='):
            self.envfile = line.split('=',1)[-1]
        elif ciline.startswith('execstart='):
            self.__append_cmd(self.execstart, line.split('=',1)[-1])
        elif ciline.startswith('execstartpre='):
            self.__append_cmd(self.execstartpre, line.split('=',1)[-1])
        elif ciline.startswith('execstartpost='):
            self.__append_cmd(self.execstartpost, line.split('=',1)[-1])
        elif ciline.startswith('execstop='):
            self.__append_cmd(self.execstop, line.split('=',1)[-1])
        elif ciline.startswith('execstoppre='):
            self.__append_cmd(self.execstoppre, line.split('=',1)[-1])
        elif ciline.startswith('execstoppost='):
            self.__append_cmd(self.execstoppost, line.split('=',1)[-1])
        elif ciline.startswith('type='):
            self.exectype = line.split('=',1)[-1]
        elif ciline.startswith('pidfile='):
            self.pidfile = line.split('=',1)[-1]
        elif ciline.startswith('alias='):
            self.alias = line.split('=',1)[-1]
        elif ciline.startswith('readonlydirectories='):
            self.__create_dir(line.split('=',1)[-1], 0555)
        elif ciline.startswith('readwritedirectories='):
            self.__create_dir(line.split('=',1)[-1])
        else:
            print '{}: Unrecognized "{}"'.format(self.svcid, line)

    def __parse_service( self, path ):
        with open(path) as f:
            for line in f:
                self.__parse_service_line(line)

    def __parse_dropins( self ):
        dropin_roots = [ self.snapdata + '/run/systemd/system',
                         self.snap + '/usr/lib/systemd/system',
                         self.snap + '/etc/systemd/system' ]
        for r in dropin_roots:
            ddir = os.path.join(r, self.svcid + '.d')
            if not os.path.isdir(ddir):
                continue
            for p in glob.glob(ddir + '/*.conf'):
                if self.debug:
                    print 'Process service dropin {}'.format(p)
                    self.__parse_service(p)

    def __create_pid_file(self, pid=0):
        with open(self.pidfile, 'w') as fo:
            if pid != 0:
                fo.write('{}\n'.format(pid))
            else:
                fo.write('\n')
            if self.debug:
                print 'Create {} with pid {}'.format(self.pidfile,pid)

    def __import_env_file(self):
        with open(self.envfile) as f:
            for line in f:
                line = line.lstrip()
                line = line.rstrip()
                if line.startswith("#"):
                    continue
                if "=" in line:
                    line = self.__expand_line(line)
                    words=line.split('=')
                    self.svcenv[words[0].strip()] = words[1].strip()
                    if self.debug:
                        print '{} ENV : {}={}'.format(self.name,
                                                      words[0].strip(),
                                                      words[1].strip())

    def __run_commands(self, cmd_list, exectype='oneshot'):
        for cmd in cmd_list:
            if cmd.startswith("-"):
                cmd = cmd[1:]
                noerr=True
            else:
                noerr=False
            if self.debug:
                print 'Exec: {} {}'.format(exectype, cmd)
            if self.prompt:
                raw_input("Press Enter to continue...")
            if exectype == 'oneshot':
                if not self.nostart:
                    subprocess.call(cmd.split(), env=self.svcenv)
            else:
                if not self.nostart:
                    e = subprocess.Popen(cmd.split(), env=self.svcenv)
                    pid = e.pid
                else:
                    pid = 0
                if exectype == 'forking':
                    self.__create_pid_file()
                else:
                    self.__create_pid_file(pid)
                if pid:
                    time.sleep(1)
        if self.quitafter == self.svcid:
            sys.exit(0)

    def __init__(self, path, debug=0, quitafter='', prompt='', nostart=0, piddir=''):
        self.svcid = os.path.basename(path)
        self.debug = debug
        self.quitafter = quitafter
        self.prompt = prompt
        self.nostart = nostart
        self.piddir = piddir
        self.after = ''
        self.before = ''
        self.requires = ''
        self.pidfile = ''
        self.envfile = ''
        self.svcenv = os.environ.copy()
        self.exectype = 'simple'
        self.killsig = '-SIGTERM'
        self.execstart = [ ]
        self.execstartpre = [ ]
        self.execstartpost = [ ]
        self.execstop = [ ]
        self.execstoppre = [ ]
        self.execstoppost = [ ]
        self.snap = os.getenv('SNAP', './test')
        self.snapdata = os.getenv('SNAP_DATA', './test')
        self.__parse_service(path)
        self.__parse_dropins()
        self.name = self.__service_name(self.svcid)
        if (self.after == '') & (self.before == ''):
            self.sort_dont_care = 0
        else:
            self.sort_dont_care = 1
        if self.requires != '':
            if self.after == '':
                self.after = self.requires
            elif self.requires != self.after:
                print 'Service {} Requires {} conflicts with After: {}'.format(self.svcid,
                                                                               self.requires,
                                                                               self.after)
                sys.exit(1)
        if not self.pidfile:
            self.pidfile = self.piddir + '/' + self.name + '.pid'
        if self.envfile:
            self.__import_env_file()

    def dump(self):
        print 'Service {}: After "{}" Before "{}" PIDfile {}'.format(self.svcid,
                                                                     self.after,
                                                                     self.before,
                                                                     self.pidfile)

    def start(self):
        if self.debug:
            print 'Starting {}'.format(self.svcid)
        if self.execstartpre:
            self.__run_commands(self.execstartpre)
        self.__run_commands(self.execstart, self.exectype)
        if self.execstartpost:
            self.__run_commands(self.execstartpost)

    def stop(self):
        if self.debug:
            print 'Stopping {}'.format(self.svcid)
        if self.execstoppre:
            self.__run_commands(self.execstoppre)

        if self.execstop:
            self.__run_commands(self.execstop)
        else:
            pid = '0'
            if os.path.isfile(self.pidfile):
                with open(self.pidfile, 'r') as fo:
                    pid = fo.readline()
                    pid = pid.lstrip()
                    pid = pid.rstrip()
                    if not self.nostart:
                        rc = -1
                        if (pid != '') & (pid != '0'):
                            if self.debug:
                                print 'Stop {} using kill {}'.format(self.svcid, pid)
                            try:
                                subprocess.check_call(['kill', self.killsig, pid])
                                rc = 0
                            except subprocess.CalledProcessError as e:
                                rc = e.returncode
                        if (rc != 0) & (len(self.execstart) > 0):
                            ix = len(self.execstart) - 1
                            if self.debug:
                                print 'Stop {} using pkill -f "{}"'.format(self.svcid,
                                                                        self.execstart[ix])
                            try:
                                subprocess.check_call(['pkill', self.killsig, '-f',
                                                       '"' + self.execstart[ix] + '"'])
                            except subprocess.CalledProcessError as e:
                                rc = e.returncode

        if os.path.isfile(self.pidfile):
            os.remove(self.pidfile)

        if self.execstoppost:
            self.__run_commands(self.execstoppost)
