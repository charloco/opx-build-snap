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
[ -e $SNAP_DATA/var/run ] || ln -s $SNAP_DATA/run $SNAP_DATA/var/run

# Add the OPX users if they don't exists
test -d /var/lib/extrausers && EXTRA="--extrausers"

# NOTE: Having problems with the --extrausers and groups.
# See https://bugs/launchpad.net/ubuntu/+source/adduser/+bug/1647333
if [ -z "$EXTRA" ] ; then
    if ! getent group _opx_cps > /dev/null; then
        addgroup $EXTRA --quiet --system --force-badname _opx_cps
    fi
    if ! getent passwd  _opx_cps> /dev/null; then
        adduser $EXTRA --quiet --system  --force-badname --no-create-home _opx_cps
    fi
else
    if ! getent group _opx_cps > /dev/null; then
        groupadd $EXTRA --system  _opx_cps
    fi
    if ! getent passwd  _opx_cps > /dev/null; then
        useradd $EXTRA  --system --no-create-home --gid _opx_cps _opx_cps
    fi
fi

# This MUST be the last thing we do as part of init since all other
# start up scripts look for this directory to flag init complete.
[ -d $PIDDIR ] || mkdir -p $PIDDIR
