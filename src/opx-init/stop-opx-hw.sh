#!/usr/bin/env bash
set +e
set -x
shopt -s nullglob

PIDDIR="$SNAP_DATA/var/run/opx/pids"

for i in $PIDDIR/*.pid ; do
    pid=`cat $i`
    n=${i##*/}
    kill -9 $pid || pkill -9 ${n%.pid*}
    rm -f $i
done

# The management interface daemon, ops_mgmtintfcfg, messes with
# /etc/resolv.conf and causes the system to lose access to DNS. Therefore
# when stopping the SNAP run resolvconf again on the management port to enable
# the eth0 management port to be fully used again after the SNAP has
# exited.
/bin/resolvconf -u > /dev/null 2>&1
