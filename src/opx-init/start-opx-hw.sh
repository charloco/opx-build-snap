#!/usr/bin/env bash
set -e
set +x
shopt -s nullglob

if [ -z "$1" ] ; then
    action="start"
else
    action="$1"
fi

# Set up the OPX environment file for Snappy
source $SNAP/etc/opx/opx-environment.sh
source $SNAP/usr/bin/opx-init-env

services=( opx-cps.service opx-cps-db.service opx-platform-init.service opx-pas.service opx-tmpctl.service )

case $action in
    start|daemonize)
        $SNAP/usr/bin/opx-snap-init
        waitforopxinit
        $SNAP/usr/bin/start-redis-server start
        for s in "${services[@]}" ; do
            $SNAP/usr/bin/snap-service-helper --env $SNAP/usr/bin/opx-init-env $SNAP/lib/systemd/system/$s start
        done
        ;;
    stop)
        for ((i=${#services[@]}-1; i>=0; i--)); do
            $SNAP/usr/bin/snap-service-helper --env $SNAP/usr/bin/opx-init-env $SNAP/lib/systemd/system/${services[$i]} stop
        done
        $SNAP/usr/bin/start-redis-server stop
        ;;
    *)
        echo "Unknow action"
        exit 1
        ;;
esac

if [ $action == "daemonize" ] ; then
    # Due to bug https://bugs.launchpad.net/snappy/+bug/1647169, we have to
    # hang around forever if started by 
    set +x
    while [ 1 ] ; do
        sleep 60
    done
fi
