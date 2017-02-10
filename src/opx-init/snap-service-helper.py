#!/usr/bin/env python

#
# Copyright (c) 2017 Extreme Networks, Inc.
#

#
# This module manages systemctl services found in a snap.
#

import os
import signal
import re
import time
import sys
import glob
import subprocess
import argparse
from operator import attrgetter

def expand_line( line ):
    line = line.replace('$SNAP_DATA', snapdata)
    line = line.replace('$SNAP', snap)
    return line

def snapify_line( line ):
    line = line.replace('/etc', snap + '/etc')
    line = line.replace('/usr', snap + '/usr')
    line = line.replace('/var', snapdata + '/var')
    return line

def service_name( service ):
    return service.split('.')[0]

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

class Service(object):

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
        elif ciline.startswith('killsignal='):
            self.killsig = '-' + line.split('=',1)[-1]
        elif ciline.startswith('environmentfile='):
            self.envfile = line.split('=',1)[-1]
        elif ciline.startswith('execstart='):
            self.execstart = line.split('=',1)[-1]
        elif ciline.startswith('type='):
            self.exectype = line.split('=',1)[-1]
        elif ciline.startswith('pidfile='):
            self.pidfile = line.split('=',1)[-1]
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

    def __import_env_file(self):
        with open(self.envfile) as f:
            for line in f:
                line = line.lstrip()
                line = line.rstrip()
                if line.startswith("#"):
                    continue
                if "=" in line:
                    line = expand_line(line)
                    words=line.split('=')
                    self.svcenv[words[0].strip()] = words[1].strip()
                    if args.debug:
                        print '{} ENV : {}={}'.format(self.name,
                                                      words[0].strip(),
                                                      words[1].strip())

    def __init__(self, path):
        self.svcid = os.path.basename(path)
        self.name = service_name(self.svcid)
        self.after = ''
        self.before = ''
        self.pidfile = ''
        self.envfile = ''
        self.svcenv = os.environ.copy()
        self.exectype = 'simple'
        self.killsig = '-SIGTERM'
        self.__parse_service(path)
        self.__parse_dropins()
        if (self.after == '') & (self.before == ''):
            self.sort_dont_care = 0
        else:
            self.sort_dont_care = 1
        if not self.pidfile:
            self.pidfile = piddir + '/' + self.name + '.pid'
        if self.envfile:
            self.__import_env_file()

    def dump(self):
        print 'Service {}: After "{}" Before "{}" PIDfile {}'.format(self.svcid,
                                                                     self.after,
                                                                     self.before,
                                                                     self.pidfile)
    def start(self):
        if (self.exectype == 'oneshot'):
            if args.debug:
                print 'ExecStart: oneshot {}'.format(self.execstart)
            if not args.nostart:
                subprocess.call(self.execstart.split(), env=self.svcenv)
        else:
            if not args.nostart:
                e = subprocess.Popen(self.execstart.split(), env=self.svcenv)
                pid = e.pid
            else:
                pid = 0
            self.__create_pid_file(pid)
            if args.debug:
                print 'ExecStart {}: {} pid = {}'.format(self.exectype,
                                                         self.execstart, pid)
            if pid:
                time.sleep(1)

    def stop(self):
        if args.debug:
            print 'Stopping {}'.format(self.svcid)
        pid = '0'
        if os.path.isfile(self.pidfile):
            with open(self.pidfile, 'r') as fo:
                pid = fo.readline()
                pid = pid.lstrip()
                pid = pid.rstrip()
                if args.debug:
                    print 'Obtained pid "{}" from {}'.format(pid,self.pidfile)
            if not args.nostart:
                rc = -1
                if (pid != '') & (pid != '0'):
                    try:
                        subprocess.check_call(['kill', self.killsig, pid])
                        rc = 0
                    except subprocess.CalledProcessError as e:
                        rc = e.returncode
                if rc != 0:
                    try:
                        subprocess.check_call(['pkill', self.killsig, self.name])
                    except subprocess.CalledProcessError as e:
                        rc = e.returncode

            os.remove(self.pidfile)

# NOTE WELL!  This is not a robust/correct sort of before/after.
#             It's an interim until I find something better.
#             This sort assumes the "don't care" are sorted first
def sort_services(services):
    sorted = [ ]
    while len(services) > 0:
        svc = services.pop()
        inserted = False
        if (svc.after != '') & (svc.before != ''):
            print 'Service {} sorts both After and Before.'.format(svc.name)
            os.exit(1)

        # Don't care, put it as early as possible
        elif (svc.after == '') & (svc.before == ''):
            sorted.insert(0,svc)

        # After - put it as late as possible
        elif svc.after != '':
            for ix in range(len(sorted)):
                if sorted[ix].after == svc.svcid:
                    sorted.insert(ix,svc)
                    inserted = True
                    break
            if not inserted:
                sorted.append(svc)

        # Before, put it as early as possible
        else:
            for ix in range(len(sorted)-1,0,-1):
                if sorted[ix].before == svc.svcid:
                    if ix == (len(sorted)-1):
                        sorted.append(svc)
                        inserted = True
                    else:
                        sorted.insert(ix+1,svc)
                        inserted = True
            if not inserted:
                sorted.insert(0,svc)

    return sorted

def stop_services(services):
    for svc in reversed(services):
        svc.stop()

def start_services(services):
    for svc in services:
        svc.start()

def term_handler(signum, frame):
    stop_services(services)
    if args.postcmd:
        for cmd in args.postcmd:
            try:
                subprocess.check_call(cmd.split())
                rc = 0
            except subprocess.CalledProcessError as e:
                rc = e.returncode

#
# Main
#

snap = os.getenv('SNAP', './test')
snapdata = os.getenv('SNAP_DATA', './test')
parser = argparse.ArgumentParser()
parser.add_argument('action', help='action to perform', choices=['start', 'stop', 'restart'])
parser.add_argument('--debug', help='Enable Debug', action='store_true')
parser.add_argument('--nostart', help='Don\'t start tasks', action='store_true')
parser.add_argument('--env', help='Supplemental environment file.')
parser.add_argument('--exclude', help='Exclude service(s).', action='append')
parser.add_argument('--piddir',  help='PID directory', default=snapdata+'/var/run/opx/pids')
parser.add_argument('--precmd',  help='Command(s) to run before starting services', action='append')
parser.add_argument('--postcmd',  help='Command(s) to run after stopping services', action='append')
args = parser.parse_args()
if args.env:
     process_env_file(args.env)
piddir = os.getenv('PIDDIR', args.piddir)

services = [ ]
service_dirs = [ snap + '/lib/systemd/system' ]

# Find all the services
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

signal.signal(signal.SIGTERM, term_handler)
signal.signal(signal.SIGINT, term_handler)
signal.signal(signal.SIGABRT, term_handler)

if args.precmd:
    for cmd in args.precmd:
        try:
            subprocess.check_call(cmd.split())
            rc = 0
        except subprocess.CalledProcessError as e:
            rc = e.returncode
    if rc:
        os.exit(rc)

# Start the services
if (args.action == 'stop') | (args.action == 'restart'):
    stop_services(services)
    os.exit(0)
if (args.action == 'start') | (args.action == 'restart'):
    start_services(services)

# wait for termination
signal.pause()
