#!/usr/bin/env python

#
# Copyright (c) 2017 Extreme Networks, Inc.
#

import os
import signal
import re
import time
import sys
import glob
import subprocess
import argparse
from datetime import datetime
from operator import attrgetter
from snap_service_class import Service
from snap_service_class import SortServices

priorities = { }

def out_file(name, outdir=''):
    path = os.path.join(outdir, name)
    try:
        outf = open(path, 'w')
    except:
        print 'Cannot open output file {}'.format(args.outfile)
        sys.exit(1)
    os.chmod(path, 0o755)
    return outf

def shell_comment(outf, comment, cchar='#'):
     outf.write('\n{0}\n{0} {1}\n{0}\n'.format(cchar, comment));

def common_header(outf, cchar='#'):
    shell_comment(outf, 'Copyright (c) {} Extreme Networks, Inc.'.\
                  format(datetime.now().strftime("%Y")), cchar)
    outf.write('{0} This file was generated {1} by the command:\n{0}\n'.\
               format(cchar, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    outf.write('{0}  {1}'.format(cchar, os.path.basename(__file__)))
    for arg in sys.argv[1:]:
        outf.write(' {}'.format(arg))
    outf.write('\n{}\n'.format(cchar))    

def bash_common_header(outf):
    if args.verbose:
        setx = '-x'
    else:
        setx = '+x'
    outf.write('#!/usr/bin/env bash\nset -e\nset {}\n'.format(setx))
    common_header(outf)

def conf_common_header(outf):
    common_header(outf, cchar=';')
    outf.write('\n[unix_http_server]\nfile=%(ENV_SNAP_DATA)s/var/run/supervisor/supervisor.sock\n')
    outf.write('\n[supervisord]\nlogfile=%(ENV_SNAP_DATA)s/var/run/supervisor/supervisord.log\n')
    outf.write('pidfile=%(ENV_SNAP_DATA)s/var/run/supervisor/supervisord.pid\n')
    outf.write('directory= %(ENV_SNAP)s/\n')
    outf.write('\n[rpcinterface:supervisor]\nsupervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface\n')
    outf.write('\n[supervisorctl]\nserverurl=unix://%(ENV_SNAP_DATA)s/var/run/supervisor/supervisor.sock\n')

def ignore_return(cmd):
    if cmd.startswith('-'):
        return '{} || true'.format(cmd[1:])
    else:
        return cmd

def bash_supervisor_wrapper(name, env='', start=[ ], stop=[ ], remain='', forkit=False, specific=''):
    valid = ''
    tab = '    '
    outf = out_file(name, args.wrapperdir)
    bash_common_header(outf)
    if specific:
        outf.write('\nif [ ! -e {1} ] ; then\n{0}while true ; do\n{0}{0}sleep 60\n{0}done\nfi\n'.\
                   format(tab,specific))
    if env:
        outf.write('\nset -o allexport\n. {0}\nset +o allexport\n'.format(env))
    if forkit:
        outf.write('\nfunction kill_app() {{\n{0}$SNAP/usr/bin/pkill {1}\n{0}exit 0\n}}\n'.format(tab, remain))
        outf.write('trap "kill_app" SIGINT SIGTERM\n')
    outf.write('\ncase $1 in\n')
    if len(start) > 0:
        outf.write('{0}start)\n'.format(tab))
        for line in start:
            line = ignore_return(line)
            outf.write('{0}{0}{1}\n'.format(tab,line))
        outf.write('{0}{0};;\n'.format(tab))
        if valid:
            valid = valid + '|'
        valid = valid + 'start'
    if len(stop) > 0:
        outf.write('{0}stop)\n'.format(tab))
        for line in stop:
            line = ignore_return(line)
            outf.write('{0}{0}{1}\n'.format(tab,line))
        outf.write('{0}{0};;\n'.format(tab))
        if valid:
            valid = valid + '|'
        valid = valid + 'stop'
    tab = '    '
    outf.write('{0}*)\n{0}{0}echo "usage: $0 {{{1}}}"\n{0}{0};;\n'.format(tab, valid))
    outf.write('esac\n')
    if forkit:
        outf.write('\npid=$(pidof {})\n'.format(remain))
        outf.write('while kill -0 $pid ; do \n{0}sleep 1\ndone\n'.format(tab))
        outf.write('\nexit 1000\n')
    elif remain:
        outf.write('\nwhile true ; do\n{0}sleep 60\ndone\n'.format(tab))
        outf.write('\nexit 0\n')
    else:
        outf.write('\nexit 0\n')
    outf.close()

def service_to_supervisor(svc, cfg):
    wrapper = '{}.supervisord-wrapper'.format(svc.name)

    #
    # Create the wrapper file
    #
    if svc.exectype == 'forking':
        forkit = True
        remain = svc.processname
        startsecs = 3
    elif (svc.exectype == 'oneshot') | (svc.remainafterexit == 'yes'):
        forkit = False
        remain = svc.processname
        startsecs = 0
    else:
        forkit = False
        remain = ''
        startsecs = 5
    envfile = svc.envfile
    start = svc.mkdirs + svc.execstartpre
    if forkit:
        start.append('{} &'.format(svc.execstart[0]))
        start.append('sleep 2')
    elif remain:
        start.append(svc.execstart[0])
    else:
        start.append('exec {}'.format(svc.execstart[0]))
    start += svc.execstartpost
    stop = svc.execstoppre + svc.execstop + svc.execstoppost
    if svc.svcid in args.specific:
        specific = svc.execstart[0].split()[0]
    else:
        specific = ''
    bash_supervisor_wrapper(wrapper, envfile, start, stop, remain, forkit, specific)

    #
    # Figure out the priority
    #
    if svc.after:
        precursor = svc.after
    elif svc.requires:
        precursor = svc.requires
    else:
        precursor = ''

    if precursor:
        mypri = priorities[precursor] + 1
    else:
        mypri = 1
    priorities[svc.svcid] = mypri

    #
    # Create the config entry
    #
    cfg.write('\n[program:{}]\n'.format(svc.name))
    cfg.write('command=%(ENV_SNAP)s/usr/bin/{} start\n'.format(wrapper))
    cfg.write('priority={}\n'.format(mypri))
    cfg.write('redirect_stderr=true\n')
    cfg.write('stdout_logfile=%(ENV_SNAP_DATA)s/var/log/supervisor/{}.log\n'.format(svc.name))
    if startsecs > 0:
        cfg.write('startsecs={}\n'.format(startsecs))

#
# Main
#

parser = argparse.ArgumentParser()
parser.add_argument('root', help='root of snap filesystem')
parser.add_argument('outfile', help='The name of the output file.')
parser.add_argument('--supervisor', help='Output files for Supervisor', action='store_true')
parser.add_argument('--wrapperdir', help='Place wrappers in this dir.')
parser.add_argument('--init', help='init cmd')
parser.add_argument('--exclude', help='Exclude service(s).', action='append')
parser.add_argument('--specific', help='Platform-specific service(s).', action='append')
parser.add_argument('--verbose', help='Verbose apps section.', action='store_true')
parser.add_argument('--debug', help='Enable Debug', action='store_true')
parser.add_argument('--debugsort', help='Enable Sort Debug', action='store_true')
args = parser.parse_args()

snap = args.root
snapdata = args.root + '/var'

services = [ ]
service_dirs = [ snap + '/lib/systemd/system' ]

# Find all the services in the snap
for sdirs in service_dirs:
    for s in glob.glob(sdirs + '/*.service'):
        svc = Service(s, args.debug, snap='$SNAP', snapdata='$SNAP_DATA',
                      root=args.root, noenvimport=True)
        if (args.exclude != None):
            if svc.svcid in args.exclude:
                if args.debug:
                    print 'Excluding {}'.format(svc.svcid)
                continue
        services.append(svc)

# Sort so 'dont care' come first
services.sort(key=attrgetter('sort_dont_care'))

# Sort for before/after
services = SortServices(services, debug=args.debugsort)
if args.debug:
    print
    print 'Managing the following services...'
    for svc in services:
            svc.dump()

# Output dir
if args.wrapperdir:
    if not os.path.exists(args.wrapperdir):
        try:
            os.makedirs(args.wrapperdir)
        except:
            print 'Cannot create output directory {}'.format(args.wrapperdir)
            sys.exit(1)

if args.supervisor:
    if args.init:
        start = [ args.init ]
    else:
        start = [ ]
    start += [ '/bin/rm -rf $PIDDIR',
               '/bin/rm -rf $SNAP_DATA/var/run/supervisor',
               'mkdir -p $SNAP_DATA/var/run/supervisor',
               '/bin/rm -rf $SNAP_DATA/var/log/supervisor',
               'mkdir -p $SNAP_DATA/var/log/supervisor',
               'exec $SNAP/bin/supervisord -c $SNAP/etc/supervisor/supervisord.conf' ]
    bash_supervisor_wrapper('supervisord.supervisord-wrapper',
                            env = '$SNAP/usr/bin/opx-init-env',
                            start = start,
                            stop = [ '$SNAP/usr/bin/pkill -SIGTERM supervisord' ] )
    cfg = out_file(args.outfile)
    conf_common_header(cfg)
    for svc in services:
        service_to_supervisor(svc, cfg)
    cfg.close()
