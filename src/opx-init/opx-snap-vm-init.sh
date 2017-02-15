#!/usr/bin/env bash
set -e
set +x
shopt -s nullglob

$SNAP/usr/bin/opx-snap-init vm

source $SNAP/usr/bin/opx-init-env

[ -d $SNAP_DATA/etc/opx ] || mkdir -p $SNAP_DATA/etc/opx
/bin/cp $SNAP/etc/opx/sai_vm_db.cfg $SNAP_DATA/etc/opx
sed -i -e"s|/etc/opx|$SNAP_DATA/etc/opx|g" $SNAP_DATA/etc/opx/sai_vm_db.cfg
/bin/cp $SNAP/etc/opx/*.sql $SNAP_DATA/etc/opx/

[ -d $SNAP_DATA/etc/opx/sdi ] || mkdir -p $SNAP_DATA/etc/opx/sdi
/bin/cp $SNAP/etc/opx/sdi/*.sql $SNAP_DATA/etc/opx/sdi/

[ -d /etc/udev/rules.d/80-dn-virt-intf.rules ] || /bin/cp $SNAP/usr/bin/80-dn-virt-intf.rules /etc/udev/rules.d
