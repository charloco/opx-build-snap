#!/usr/bin/env bash
set -e
set +x
shopt -s nullglob

# "hw" == Hardware
# "vm" == Virtual Machine
if [ -z $1 ] ; then
    MACHINETYPE="hw"
else
    MACHINETYPE=$1
fi

if [ $MACHINETYPE == "hw" ] ; then
    # Start platform-specific modules
    # NOTE: There are problems with Ubuntu-Core running custom kernel.
    #       The path to kernel modules is not set up correctly
    #       See https://bugs.launchpad.net/snapcraft/+bug/1658177
    set +e
    for m in $SNAP/etc/modules-load.d/* ; do
        while read mod ; do
            modprobe $mod 2>/dev/null 1>&2
        done < $m
    done
    set -e
fi

source $SNAP/usr/bin/opx-init-env

[ -d $SNAP_DATA/run ] || mkdir -p $SNAP_DATA/run
[ -d $SNAP_DATA/var ] || mkdir -p $SNAP_DATA/var
[ -d $SNAP_DATA/var/log ] || mkdir -p $SNAP_DATA/var/log
[ -L $SNAP_DATA/var/run ] || ln -s $SNAP_DATA/run $SNAP_DATA/var/run

if [ $MACHINETYPE == "vm" ] ; then
    /usr/bin/test -d $SNAP_DATA/etc || mkdir -p $SNAP_DATA/etc
    for f in $SNAP_DATA/etc/opx/opx-environment $SNAP_DATA/etc/opx/opx-environment.sh ; do
        sed -i 's/\$SNAP\/etc/\$SNAP_DATA\/etc/g' $f
    done
fi

# Add the OPX users if they don't exists
# NOTE: Having problems with the --extrausers and groups.
# See https://bugs/launchpad.net/ubuntu/+source/adduser/+bug/1647333
set +e
if [ -e /var/lib/extrausers ] ; then
    EXTRA="--extrausers"
fi
if ! getent group _opx_cps > /dev/null; then
    addgroup $EXTRA --quiet --system --force-badname _opx_cps
fi
if ! getent passwd  _opx_cps> /dev/null; then
    adduser $EXTRA --quiet --system  --force-badname --no-create-home _opx_cps
fi
set -e

# This MUST be the last thing we do as part of init since all other
# start up scripts look for this directory to flag init complete.
[ -d $PIDDIR ] || mkdir -p $PIDDIR
