#!/usr/bin/env python

#
# Copyright (c) 2017 Extreme Networks, Inc.
#
# This module attempts to fill in some of the holes that snappy
# leaves when dealing with service files.
#

import os
import re
import time
import sys
import glob
import subprocess
import argparse

wait_timeout = 10.0
wait_pause = 0.25
snap = ''
snapdata = ''
descr = ''
after = ''
before = ''
wants = ''
env = ''
execstart = ''
execpre = ''
execpost = ''
killsig = '-SIGKILL'
exectype=''

def expand_line( line ):
    line = line.replace('$SNAP_DATA', snapdata)
    line = line.replace('$SNAP', snap)
    return line

def snapify_line( line ):
    line = line.replace('/etc', snap + '/etc')
    line = line.replace('/usr', snap + '/usr')
    return line

def parse_service_line( line ):
    global descr, after, before, wants, env, execstart, execpre, execpost, exectype, killsig

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
    elif ciline.startswith('description='):
        descr = line.split('=',1)[-1]
    elif ciline.startswith('after='):
        after = line.split('=',1)[-1]
    elif ciline.startswith('before='):
        before = line.split('=',1)[-1]
    elif ciline.startswith('wants='):
        wants = line.split('=',1)[-1]
    elif ciline.startswith('killsignal='):
        killsig = '-' + line.split('=',1)[-1]
    elif ciline.startswith('environmentfile='):
        env = line.split('=',1)[-1]
    elif ciline.startswith('execstart='):
        execstart = line.split('=',1)[-1]
    elif ciline.startswith('type='):
        exectype = line.split('=',1)[-1]
    else:
        print 'Unrecognized: {}'.format(line)
        return
    parts = line.split()

def parse_service( path ):
    with open(path) as f:
        for line in f:
            parse_service_line(line)

def parse_dropins( service ):
    dropin_roots = [ snapdata + '/run/systemd/system',
                    snap + '/usr/lib/systemd/system',
                    snap + '/etc/systemd/system' ]
    for r in dropin_roots:
        ddir = os.path.join(r, service + '.d')
        if not os.path.isdir(ddir):
            continue
        for p in glob.glob(ddir + '/*.conf'):
            if args.debug:
                print 'Process service dropin {}'.format(p)
            parse_service(p)

def process_env_file( env ):
    if args.debug:
        print 'ENV: using file {}'.format(env)
    with open(env) as f:
        for line in f:
            line = line.lstrip()
            line = line.rstrip()
            if line.startswith("#"):
                continue
            if "=" in line:
                line = expand_line(line)
                words=line.split('=')
                os.environ[words[0].strip()] = words[1].strip()
                if args.debug:
                    print 'ENV:    {} = {}'.format(words[0].strip(), words[1].strip())

def service_name( service ):
    return service.split('.')[0]

def pidfile_name( service ):
    svcname = service_name(service)
    svcname = svcname + '.pid'
    return os.path.join(piddir, svcname)

def create_pid_file( service, pid=0 ):
    pidfile = pidfile_name( service )
    with open(pidfile, 'w') as fo:
        if pid != 0:
            fo.write('{}\n'.format(pid))
        else:
            fo.write('\n')
        if args.debug:
            print 'Create {} with pid {}'.format(pidfile,pid)

def pid_exists( service ):
    pidfile = pidfile_name(service)
    if os.path.isfile(pidfile):
        return True
    else:
        return False

def stop_service( service ):
    pidfile = pidfile_name(service)
    svcname = service_name(service)
    pid = '0'
    if os.path.isfile(pidfile):
        with open(pidfile, 'r') as fo:
            pid = fo.readline()
            pid = pid.lstrip()
            pid = pid.rstrip()
        if args.debug:
            print 'Obtained pid {} from {}'.format(pid,pidfile)
    rc = -1
    if (pid != '') & (pid != '0'):
        try:
            subprocess.check_call(['kill', killsig, pid])
            rc = 0
        except subprocess.CalledProcessError as e:
            rc = e.returncode
    if rc != 0:
        try:
           subprocess.check_call(['pkill', killsig, svcname])
        except subprocess.CalledProcessError as e:
            rc = e.returncode
    if os.path.isfile(pidfile):
        os.remove(pidfile)

def wait_for_service( service ):
    if args.debug:
        print 'Waiting for service {}'.format(service)
    if service == 'systemd-modules-load.service':
        return
    if service == 'network.target':
        return
    timeout=wait_timeout
    while timeout > 0:
        if pid_exists(service):
            break
        time.sleep(wait_pause)
        timeout = timeout - wait_pause
    if (timeout <= 0):
        print 'Timed out waiting for {}'.format(service)
        sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('service', help='The service to help.')
parser.add_argument('action', help='The action to take.',
                    choices=['start','stop','restart'])
parser.add_argument('--debug', help='Enable Debug', action='store_true')
parser.add_argument('--env', help='Supplemental environment file.')
parser.add_argument('--piddir', help='PID directory')
args = parser.parse_args()

snap = os.getenv('SNAP', './tmp')
snapdata = os.getenv('SNAP_DATA', './tmp')

if args.env:
     process_env_file(args.env)
if args.piddir:
    piddir = args.piddir
else:
    piddir = os.getenv('PIDDIR', os.path.join(snapdata, 'pids'))
if args.debug:
    print '$SNAP = {}'.format(snap)
    print '$SNAP_DATA = {}'.format(snapdata)
    print '$PIDDIR = {}'.format(piddir)

parse_service(args.service)
my_service = os.path.basename(args.service)
parse_dropins(my_service)

if env:
    process_env_file(env)

if ((args.action == 'stop') | (args.action == 'restart')):
    stop_service(my_service)
    if args.debug:
        print 'Stop: {} stopped.'.format(my_service)    
    if args.action == 'stop':
        sys.exit(0)

if after:
    wait_for_service(after)
    if args.debug:
        print 'After: {} started.'.format(after)

if wants:
    if not pid_exists(wants):
        print '{} does not exists.'.format(wants)
        sys.exit(1)
    elif args.debug:
        print 'Wants: {} started.'.format(wants)

if before:
    if pid_exists(before):
        print '{} has already started.'.format(before)
        sys.exit(1)
    elif args.debug:
        print 'Before: {} has not yet started.'.format(before)

if execstart:
    if exectype == 'oneshot':
        subprocess.call(execstart.split())
        if args.debug:
            print 'ExecStart: oneshot {}'.format(execstart)
    else:
        e = subprocess.Popen(execstart.split())
        if exectype == 'forking':
            create_pid_file(my_service)
        else:
            create_pid_file(my_service, e.pid)
        if args.debug:
            print 'ExecStart: {} pid = {}'.format(execstart, e.pid)
