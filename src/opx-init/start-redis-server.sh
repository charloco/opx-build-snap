#!/usr/bin/env bash
set -e
set +x

if [ -z $1 ] ; then
    action="start"
else
    action=$1
fi

source $SNAP/usr/bin/opx-init-env

if [ $action == "stop" ] ; then
    if [ -e $PIDDIR/redis-server.pid ] ; then
        pushd $SNAP_DATA/run
        /bin/run-parts --verbose $SNAP/etc/redis/redis-server.pre-down.d
        pkill redis-server --signal SIGTERM
        /bin/run-parts --verbose $SNAP/etc/redis/redis-server.post-down.d
        popd
        rm -f $PIDDIR/redis-server.pid
    fi
    exit 0
fi

waitforopxinit

[ -d $SNAP_DATA/var/log/redis ] || mkdir -p $SNAP_DATA/var/log/redis
[ -d $SNAP_DATA/var/lib/redis ] || mkdir -p $SNAP_DATA/var/lib/redis
[ -d $SNAP_DATA/var/run/redis ] || mkdir -p $SNAP_DATA/var/run/redis
if [ ! -e $SNAP_DATA/var/run/redis.conf ] ; then
    sed "s|logfile \/var\/log\/redis\/redis-server.log|logfile ${SNAP_DATA}\/var\/log\/redis\/redis-server.log|g" $SNAP/etc/redis/redis.conf > $SNAP_DATA/var/run/redis.conf
    sed -i -e"s|\/var\/lib\/redis|$SNAP_DATA\/var\/lib\/redis|g" $SNAP_DATA/var/run/redis.conf
fi

pushd $SNAP_DATA/run
/bin/run-parts --verbose $SNAP/etc/redis/redis-server.pre-up.d
redis-server $SNAP_DATA/var/run/redis.conf
touch $PIDDIR/redis-server.pid
/bin/run-parts --verbose $SNAP/etc/redis/redis-server.post-up.d
popd

exit 0
