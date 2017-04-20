#!/usr/bin/env bash
set -e
set +x

dest=$1

if [ ! -e $dest ] ; then
    sed "s|logfile \/var\/log\/redis\/redis-server.log|logfile ${SNAP_DATA}\/var\/log\/redis\/redis-server.log|g" $SNAP/etc/redis/redis.conf > $dest
    sed -i -e"s|\/var\/lib\/redis|${SNAP_DATA}\/var\/lib\/redis|g" $dest
fi
