#!/usr/bin/env bash

# Environment for opx-init

PIDDIR=$SNAP_DATA/var/opx/pids
BINDIR=$SNAP/usr/bin
LIBOPXDIR=$SNAP/usr/lib/opx

function waitforopxinit {
    while [ ! -d $PIDDIR ] ; do
        sleep 1
    done
}
