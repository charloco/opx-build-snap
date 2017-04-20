#!/usr/bin/env python

#
# Copyright (c) 2017 Extreme Networks, Inc.
#

#
# This module parses the services found in a snap and generates a snapcraft
# apps: section that can be used to launch the services. 
#

import os
import re
import signal
import re
import time
import sys
import glob
import subprocess
import argparse
from datetime import datetime
from operator import attrgetter


def snapify_line( line ):
    line = line.replace('/etc', '$SNAP/etc')
    line = line.replace('/usr', '$SNAP/usr')
    line = line.replace('/var', '$SNAP_DATA/var')
    return line

def service_name( service ):
    return service.split('.')[0]

def default_pidfile(name):
    return '{}/{}'.format(args.piddir, name)

def apps_write_command(cmdid, cmd, verbose, waitsfor=False, init='', daemon='',
                       follows='', after='', requires='', stop='', stoppost=''):
    global outf
    global nodaemon
    restart=''
    outf.write('  {}:\n    command: usr/bin/service-helper'.format(cmdid))
    if verbose:
        outf.write(' --verbose')
    if init:
        outf.write(' --init \\\"{}\\\"'.format(init))
    if follows:
        outf.write(' --follows {}'.format(re.sub('\.service$', '', follows)))
        waitsfor = True
    if (after != '') & (not args.noafter):
        outf.write(' --after {}'.format(re.sub('\.service$', '', after)))
        waitsfor = True
    if requires:
        outf.write(' --requires {}'.format(re.sub('\.service$', '', requires)))
        waitsfor = True
    if not daemon:
        daemon = 'simple'
    elif daemon == 'oneshot':
        outf.write(' --oneshot')
        if waitsfor:
            restart='never'
    # If we wait for some unit, we MUST have the helper notify!
    # Otherwise, systemd will hang if the unit we're waiting for has not
    # yet been started by systemd.
    if waitsfor:
        outf.write(' --notify')
        daemon = 'notify'
    outf.write(' {} {}\n'.format(cmd, cmdid))
    if daemon:
        if nodaemon:
            nodaemonize='#'
        else:
            nodaemonize=''
        outf.write('{}    daemon: {}\n'.format(nodaemonize, daemon))
        if restart:
            outf.write('{}    restart-condition: {}\n'.format(nodaemonize, restart))
    if stop:
        outf.write('{}    stop-command: {}\n'.format(nodaemonize, stop))
    if stoppost:
        outf.write('{}    post-stop-command: {}\n'.format('#', stoppost))
    outf.write('\n')

def shell_comment(comment):
     outf.write('\n#\n# {}\n#\n'.format(comment));

def shell_write_command(cmd):
    if cmd.startswith('-'):
        outf.write('{} || true\n'.format(cmd[1:]))
    else:
        outf.write('{}\n'.format(cmd))

def shell_write_helper(myid, cmd, exectype='simple', env='', pid=''):
    if args.delay:
        background = '&\nsleep {}'.format(args.delay)
    else:
        background = '&'
    outf.write('$SNAP/usr/bin/service-helper')
    if args.verbose:
        outf.write(' --verbose')
    if exectype == 'notify':
        outf.write(' --notify')
    elif exectype == 'forking':
        background = ''
    if env:
        outf.write(' --env {}'.format(env))
    if pid:
        outf.write(' --pidfile {}'.format(pid))
    outf.write(' --cmd "{}" {} {}\n'.format(cmd, myid, background))

# This class represents a systemctl service
class Service(object):

    def __append_cmd(self, cmds, newcmd):
        if not newcmd:
            while len(cmds) > 0:
                cmds.remove(cmds[0])
        else:
            cmds.append(newcmd)

    def __create_dir(self, cmds, newdir, mode=0711):
        if newdir.startswith("-"):
            newdir = newdir[1:]
            mycmd = '-'
        else:
            mycmd = ''
        mycmd += '/bin/mkdir -m 0{:o} -p {}'.format(mode, newdir)
        if newdir != '/':
            self.__append_cmd(cmds, mycmd) 

    # Parse each line in a service file.
    # This is an extremely lightweight service manager.  We only process
    # those lines that are relevant to a service running inside a Snap.
    def __parse_service_line( self, line ):
        line = line.strip()
        ciline = line.lower()
        line = snapify_line(line)
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
            self.__create_dir(self.mkdirs, line.split('=',1)[-1], 0555)
        elif ciline.startswith('readwritedirectories='):
            self.__create_dir(self.mkdirs, line.split('=',1)[-1])
        else:
            print '{}: Unrecognized "{}"'.format(self.svcid, line)

    def __parse_service( self, path ):
        with open(path) as f:
            for line in f:
                self.__parse_service_line(line)

    def __parse_dropins( self ):
        dropin_roots = [ snapdata + '/run/systemd/system',
                         snap + '/usr/lib/systemd/system',
                         snap + '/etc/systemd/system' ]
        for r in dropin_roots:
            ddir = os.path.join(r, self.svcid + '.d')
            if not os.path.isdir(ddir):
                continue
            for p in glob.glob(ddir + '/*.conf'):
                if args.debug:
                    print 'Process service dropin {}'.format(p)
                    self.__parse_service(p)

    def __create_pid_file(self, pid=0):
        with open(self.pidfile, 'w') as fo:
            if pid != 0:
                fo.write('{}\n'.format(pid))
            else:
                fo.write('\n')
            if args.debug:
                print 'Create {} with pid {}'.format(self.pidfile,pid)

    def __init__(self, path):
        self.svcid = os.path.basename(path)
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
        self.mkdirs = [ ]
        self.__parse_service(path)
        self.__parse_dropins()
        self.name = service_name(self.svcid)
        if (self.after == '') & (self.before == ''):
            self.sort_dont_care = 0
        else:
            self.sort_dont_care = 1
        if len(self.execstart) < 1:
            print 'Service {} has no ExecStart.'.format(self.svcid)
            sys.exit(1)
        elif len(self.execstart) > 1:
            print 'Service {} has more than one ExecStart.'.format(self.svcid)
            sys.exit(1)
        if self.requires != '':
            if self.after == '':
                self.after = self.requires
            elif self.requires != self.after:
                print 'Service {} Requires {} conflicts with After: {}'.format(self.svcid,
                                                                               self.requires,
                                                                               self.after)
                sys.exit(1)
        if self.before:
            print 'Service {} Before {} - not supported.'.format(self.svcid,
                                                                 self.before)
            sys.exit(1)
        if self.execstoppre:
            print 'Ignoring ExecStopPre command(s) for {}.'.format(self.svcid)
        if self.execstoppost:
            print 'Ignoring ExecStopPost command(s) for {}.'.format(self.svcid)

    def dump(self):
        print 'Service {}: After "{}" Before "{}" PIDfile {}'.format(self.svcid,
                                                                     self.after,
                                                                     self.before,
                                                                     self.pidfile)

    def apps_command(self, verbose, initcmd):
        mycmd = ''
        dtype = ''
        stop = ''
        waits = False
        if self.envfile:
            mycmd += ' --env {}'.format(self.envfile)
        for newdir in self.mkdirs:
            mycmd += ' --precmd \\\"{} \\\"'.format(newdir)
        for precmd in self.execstartpre:
            mycmd += ' --precmd \\\"{} \\\"'.format(precmd)
        if self.exectype:
            dtype = self.exectype
        mycmd += ' --cmd \\\"{} \\\"'.format(self.execstart[0])
        for cmd in self.execstop:
            if stop:
                stop += ' && '
            stop += cmd
        apps_write_command(self.name, mycmd, verbose, init=initcmd, daemon=dtype,
                           waitsfor=waits, after=self.after, requires=self.requires,
                           stop=stop)

        if self.execstartpost:
            mycmd = '--requires {} '.format(self.name)
            lastix = len(self.execstartpost) - 1
            for ix, postcmd in enumerate(self.execstartpost):
                if ix < lastix:
                    mycmd += ' --precmd \\\"{} \\\"'.format(postcmd)
                else:
                    mycmd += ' --cmd \\\"{} \\\"'.format(postcmd)
            apps_write_command('{}-post'.format(self.name), mycmd, verbose,
                               waitsfor=True, daemon='oneshot')

    def shell_service_start(self):
        shell_comment(self.svcid)
        if not args.nodaemon:
            shell_write_command('systemd-notify --status="Starting {}..."'.format(self.svcid))
        for newdir in self.mkdirs:
            shell_write_command(newdir)
        for precmd in self.execstartpre:
            shell_write_command(precmd)
        if self.exectype == 'oneshot':
            shell_write_command(self.execstart[0])
        else:
            if self.pidfile:
                pidfile = self.pidfile
            else:
                pidfile = default_pidfile(self.name)
            shell_write_helper(self.name, self.execstart[0],
                               exectype=self.exectype,
                               env=self.envfile,
                               pid=pidfile)
        for postcmd in self.execstartpost:
            shell_write_command(postcmd)

    def shell_service_stop(self, indent=''):
        if self.exectype == 'oneshot':
            return
        if not args.nodaemon:
            shell_write_command('{}systemd-notify status="Stopping {}"'.format(indent,self.svcid))
        for precmd in self.execstoppre:
            if indent:
                outf.write(indent)
            shell_write_command(precmd)
        if self.execstop:
            if indent:
                outf.write(indent)
            if self.execstop[0].startswith('-'):
                shell_write_command(self.execstop[0])
            else:
                shell_write_command('-' + self.execstop[0])
        else:
            if indent:
                outf.write(indent)
            if self.pidfile:
                pidfile = self.pidfile
            else:
                pidfile = default_pidfile(self.name)
            shell_write_command('-kill -SIGTERM $(cat {})'.format(pidfile))       
        for postcmd in self.execstoppost:
            if indent:
                outf.write(indent)
            shell_write_command(postcmd)

# NOTE WELL!  This is not a robust/correct sort of before/after.
#             It's an interim until I come up with something better.
#
#             This sort assumes that any service listed in 'before' or
#             'after' is a member of the set being sorted.
#             This sort assumes there are no loops or logic errors in
#             the 'before' and 'after' assertions.
#
#             This sort assumes that if 'Requires' is used, then
#             it matches the 'after' clause.
def sort_services(services):
    sorted = [ ]
    iteration = 0
    lastlen = 0
    while len(services) > 0:
        if lastlen != len(services):
            lastlen = len(services)
            iteration = 0
        else:
            iteration += 1
            if iteration > len(services):
                print 'Unable to sort list - infinite loop.'
                sys.exit(1)
        svc = services.pop(0)
        if args.debugsort:
            print 'Sorting service {}... Before "{}" After "{}"'.format(svc.svcid,
                                                                        svc.before,
                                                                        svc.after)
        inserted = False
        if (svc.after != '') & (svc.before != ''):
            print 'Service {} specifies both After and Before.'.format(svc.svcid)
            sys.exit(1)
        elif len(svc.after.split()) > 1:
            print 'Service {} specifies multiple After: {}'.format(svc.svcid,
                                                                   svc.after)
            sys.exit(1)
        elif len(svc.before.split()) > 1:
            print 'Service {} specifies multiple Before: {}'.format(svc.svcid,
                                                                    svc.before)
            sys.exit(1)

        # Don't care, put it as early as possible
        elif (svc.after == '') & (svc.before == ''):
            if args.debugsort:
                print '    Insert {} at head of list.'.format(svc.svcid)
            sorted.insert(0,svc)

        # After - put it as late as possible
        elif svc.after != '':
            insertix = -1
            afterix = -1
            for ix in range(len(sorted)):
                if args.debugsort:
                    print '  check {}/{} before "{}" After "{}"'.format(ix,
                                                                        sorted[ix].svcid,
                                                                        sorted[ix].before,
                                                                        sorted[ix].after)
                if (insertix < 0) & (sorted[ix].after == svc.svcid):
                    insertix = ix
                elif sorted[ix].svcid == svc.after:
                    afterix = ix

            if afterix < 0:
                if (len(services)) <= 0:
                    print "{}: cannot find \'after\' service {}".format(svc.svcid,
                                                                        svc.after)
                    sys.exit(1)
                if args.debugsort:
                    print '    {}: cannot be sorted yet; will try later.'.format(svc.svcid)
                services.append(svc)
            elif insertix < 0:
                if args.debugsort:
                    print '    {}: placed at tail of list.'.format(svc.svcid)
                sorted.append(svc)
            else:
                if args.debugsort:
                    print '    {}: placed at {}/{}.'.format(svc.svcid,
                                                            ix, len(sorted))
                sorted.insert(ix,svc)

        # Before, put it as early as possible
        else:
            insertix = -1
            beforeix = -1
            for ix in range(len(sorted)):
                if args.debugsort:
                    print '  check {}/{} Before "{}" after "{}"'.format(ix,
                                                                        sorted[ix].svcid,
                                                                        sorted[ix].before,
                                                                        sorted[ix].after)
                if sorted[ix].before == svc.svcid:
                    insertix = ix
                elif sorted[ix].svcid == svc.before:
                    beforeix = ix
            if beforeix < 0:
                if (len(services)) <= 0:
                    print "{}: cannot find \'before\' service {}".format(svc.svcid,
                                                                         svc.before)
                    sys.exit(1)
                if args.debugsort:
                    print '{}: cannot be sorted yet; will try later.'.format(svc.svcid)
                services.append(svc)
            elif insertix < (len(sorted) - 1):
                if args.debugsort:
                    print '    {}: placed at {}/{}.'.format(svc.svcid,
                                                            insertix+1,
                                                            len(sorted))
                sorted.insert(insertix+1,svc)
            else:
                if args.debugsort:
                    print '    {}: placed at tail of list.'.format(svc.svcid)
                sorted.append(svc)

    if args.debugsort:
        print
        print 'Sorted list...'
        for ix in range(len(sorted)):
            print '{}/{}: before "{}" after "{}"'.format(ix,
                                                         sorted[ix].svcid,
                                                         sorted[ix].before,
                                                         sorted[ix].after)
    return sorted

def shell_common_header():
    if args.verbose:
        setx = '-x'
    else:
        setx = '+x'
    outf.write('#!/usr/bin/env bash\nset -e\nset {}\n\n'.format(setx))
    shell_comment('Copyright (c) {} Extreme Networks, Inc.'.\
               format(datetime.now().strftime("%Y")))
    outf.write('# This shell script generated {} by the command:\n#\n'.\
               format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    outf.write('#  {}'.format(os.path.basename(__file__)))
    for arg in sys.argv[1:]:
        outf.write(' {}'.format(arg))
    outf.write('\n#\n')

def shell_common_footer():
    shell_comment('End of auto-generated shell script.')

def shell_start_header():
    shell_common_header()
    shell_comment('snapcraft.yaml apps: command...')
    outf.write('#  {}:\n'.format(os.path.basename(args.outfile)))
    outf.write('#    command: usr/bin/{}\n'.format(os.path.basename(args.outfile)))
    if args.nodaemon:
        outf.write('#\n')
    else:
        outf.write('#    daemon: notify\n')
        outf.write('#    stop-command: usr/bin/{}\n#\n'.\
                   format(os.path.basename(stopfile)))

    shell_comment('Set a new process group id.')
    shell_write_command('pgid=$(ps -o pgid= $$ | grep -o [0-9]*)')
    shell_write_command('pid=$$')
    shell_write_command('if [ "$pid" != "$pgid" ] ; then')
    shell_write_command('    exec setsid $(readlink -f $0) $@')
    shell_write_command('fi')
    shell_write_command('test -d {0} || mkdir -p {0}'.format(args.piddir))
    shell_write_command('echo $$ > {}/{}'.\
                        format(args.piddir, os.path.basename(args.outfile)))

    shell_comment('Initialization')
    shell_write_command('cd $SNAP')
    if args.init:
        shell_write_command(args.init)

def shell_start_footer():
    shell_comment('Handle shell exit.')
    outf.write('function finish {\n')
#    for svc in reversed(services):
#        outf.write('\n')
#        svc.shell_service_stop('  ')
    outf.write('  . $SNAP/usr/bin/{}\n'.format(stopfile))
    outf.write('}\ntrap finish EXIT\n\n')
    if not args.nodaemon:
        shell_comment('Notify Snap that we are up and running.')
        shell_write_command('systemd-notify --ready')
    shell_comment('Monitor the children.')
    shell_write_command('set +x')
    shell_write_command('while true ; do sleep 1 ; done')
    shell_common_footer()

def shell_stop_header():
    shell_common_header()

def shell_stop_footer():
    shell_comment('Sweep up any stragglers.')
    shell_write_command('kill -SIGKILL -$(cat {}/{})'.\
                        format(args.piddir, os.path.basename(args.outfile)))
    shell_common_footer()

#
# Main
#
parser = argparse.ArgumentParser()
parser.add_argument('root', help='root of snap filesystem')
parser.add_argument('outfile', help='place output in this file')
parser.add_argument('--apps', help='Generate a snapcraft.yaml apps section.',
                    action='store_true')
parser.add_argument('--shell', help='Generate a shell file.', action='store_true')
parser.add_argument('--piddir', help='Pid file location.', default='$SNAP_DATA/var/run/opx/pids')
parser.add_argument('--init', help='init cmd')
parser.add_argument('--delay', help='Seconds delay after spwaning service.')
parser.add_argument('--exclude', help='Exclude service(s).', action='append')
parser.add_argument('--verbose', help='Verbose apps section.', action='store_true')
parser.add_argument('--nodaemon', help='No daemonization', action='store_true')
parser.add_argument('--noafter', help='No after.', action='store_true')
parser.add_argument('--debug', help='Enable Debug', action='store_true')
parser.add_argument('--debugsort', help='Enable Sort Debug', action='store_true')
args = parser.parse_args()
nodaemon = args.nodaemon
snap = args.root
snapdata = args.root + '/var'
stopfile = args.outfile + '-stop'

services = [ ]
service_dirs = [ args.root + '/lib/systemd/system' ]

# Find all the services in the snap
for sdirs in service_dirs:
    for s in glob.glob(sdirs + '/*.service'):
        svc = Service(s)
        if (args.exclude != None):
            if svc.svcid in args.exclude:
                if args.debug:
                    print 'Excluding {}'.format(svc.svcid)
                continue
        services.append(svc)

# Sort so 'dont care' come first
services.sort(key=attrgetter('sort_dont_care'))

# Sort for before/after
services = sort_services(services)

if args.debug:
    print
    print 'Managing the following services...'
    for svc in services:
            svc.dump()
try:
    outf = open(args.outfile, 'w')
except:
    print 'Cannot open output file {}'.format(args.outfile)
    sys.exit(1)

if args.apps:
    outf.write('#\n# This section generated {} by {}\n'.\
               format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      os.path.basename(__file__)))
    outf.write('# Do not modify the apps: section manually.\n#\n\napps:\n\n')

    for svc in services:
        svc.apps_command(args.verbose, args.init)

    outf.write('#\n# END of auto-generated apps: section.\n#\n')
    outf.close()

elif args.shell:
    shell_start_header()
    for svc in services:
        svc.shell_service_start()
    shell_start_footer()
    outf.close()
    os.chmod(args.outfile, 0755)

    if args.nodaemon:
        try:
            outf = open(stopfile, 'w')
        except:
            print 'Cannot open output file {}'.format(stopfile)
            sys.exit(1)
        shell_stop_header()
        for svc in reversed(services):
            svc.shell_service_stop()
        shell_stop_footer()
        outf.close()
        os.chmod(stopfile, 0755)
