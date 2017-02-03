#!/usr/bin/env bash
set -e
set -x
shopt -s nullglob

# "hw" == Hardware
# "vm" == Virtual Machine
OPXTYPE="hw"

# Local variables
PIDDIR="$SNAP_DATA/var/run/opx/pids"
BINDIR="$SNAP/usr/bin"
LIBOPXDIR="$SNAP/usr/lib/opx"

# Required for GO
export GOROOT=$SNAP/usr/lib/go-1.6
export GOPATH=$SNAP

# Setup /var/run, /run and /var/log
/usr/bin/test -d $SNAP_DATA/run || mkdir -p $SNAP_DATA/run
/usr/bin/test -d $SNAP_DATA/var || mkdir -p $SNAP_DATA/var
/usr/bin/test -d $SNAP_DATA/var/log || mkdir -p $SNAP_DATA/var/log
/usr/bin/test -L $SNAP_DATA/var/run || ln -s $SNAP_DATA/run $SNAP_DATA/var/run
/usr/bin/test -d $PIDDIR ||  mkdir -p $PIDDIR

if [ $OPXTYPE == "vm" ] ; then
    /usr/bin/test -d $SNAP_DATA/etc || mkdir -p $SNAP_DATA/etc
else
    /usr/bin/test -d $SNAP_DATA/etc/opx || (mkdir -p $SNAP_DATA/etc/opx && cp -r $SNAP/etc/opx/* $SNAP_DATA/etc/opx/)
fi

# Set up the OPX environment file for Snappy
for i in $SNAP_DATA/etc/opx/*environment* ; do
    if ! grep -Fq "\$SNAP" "$i" ; then
        sed -i 's/=\/usr\/lib/=$SNAP\/usr\/lib/g' $i
        sed -i 's/:\/usr\/lib/:$SNAP\/usr\/lib/g' $i
        sed -i 's/=\/lib/=$SNAP\/lib/g' $i
        sed -i 's/:\/lib/:$SNAP\/lib/g' $i
        if grep -Fq "export" "$i" ; then
            exp="export "
        fi 
        echo "${exp}OPX_CONFIG_ROOT=$SNAP" >> $i
    fi
done
source $SNAP_DATA/etc/opx/opx-environment.sh

# Setup _opx_cps user
if [ $OPXTYPE == "hw" ] ; then
    EXTRA="--extrausers"
# Having problems with the --extrausers and groups.
# see https://bugs/launchpad.net/ubuntu/+source/adduser/+bug/1647333
# if ! getent group _opx_cps > /dev/null; then
#    addgroup $EXTRA --quiet --system --force-badname _opx_cps
# fi
# if ! getent passwd  _opx_cps> /dev/null; then
#    adduser $EXTRA --quiet --system  --force-badname --no-create-home _opx_cps
#fi
else
    if ! getent group _opx_cps > /dev/null; then
        addgroup --quiet --system --force-badname _opx_cps
    fi
    if ! getent passwd  _opx_cps> /dev/null; then
        adduser --quiet --system  --force-badname --no-create-home _opx_cps
    fi
fi

echo STARTING: Redis Server
if [ ! -d $SNAP_DATA/var/run/redis.conf ]
then
    mkdir -p $SNAP_DATA/var/log/redis
    mkdir -p $SNAP_DATA/var/lib
    mkdir -p $SNAP_DATA/var/lib/redis
    sed "s|logfile \/var\/log\/redis\/redis-server.log|logfile ${SNAP_DATA}\/var\/log\/redis\/redis-server.log|g" $SNAP/etc/redis/redis.conf > $SNAP_DATA/var/run/redis.conf
    sed -i -e"s|\/var\/lib\/redis|$SNAP_DATA\/var\/lib\/redis|g" $SNAP_DATA/var/run/redis.conf
fi

pushd $SNAP_DATA/run
/bin/run-parts --verbose $SNAP/etc/redis/redis-server.pre-up.d
redis-server $SNAP_DATA/var/run/redis.conf &
echo $! > $PIDDIR/redis-server.pid
/bin/run-parts --verbose $SNAP/etc/redis/redis-server.post-up.d
popd

echo STARTING: Platform-Specific initialization
for m in $SNAP/etc/modules-load.d/* ; do
    while read mod ; do
        modprobe $mod 2>/dev/null 1>&2 || true
    done < $m
done
$BINDIR/opx_platform_init.sh

echo STARTING: OPX 
pushd $SNAP_DATA/run
$BINDIR/opx_cps_service &
sleep 1
echo $! > $PIDDIR/opx-cps.pid
$BINDIR/python $LIBOPXDIR/cps_db_stunnel_manager.py &
echo $! > $PIDDIR/cps_db_stunnel_manager.pid
sleep 2
$BINDIR/opx_pas_service &
echo $! > $PIDDIR/opx_pas_service.pid
sleep 1
$BINDIR/opx_env_tmpctl_svc &
echo $! > $PIDDIR/opx_env_tmpctl_svc.pid
# $BINDIR/base_nas_monitor_phy_media.sh &
# $BINDIR/base_nas_phy_media_config.sh &
# $BINDIR/opx_nas_daemon &
# $BINDIR/base_nas_front_panel_ports.sh &
# $BINDIR/base-nas-shell.sh &
# $BINDIR/base_nas_create_interface.sh &
# $BINDIR/base_nas_fanout_init.sh && $BINDIR/network_restart.sh &
# $BINDIR/base_ip &
# $BINDIR/base_acl_copp_svc.sh &
# $BINDIR/base_nas_default_init.sh &
# $BINDIR/base_qos_init.sh &
popd
echo ENDING: OPX

