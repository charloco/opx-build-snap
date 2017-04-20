#!/usr/bin/env bash

set -e
set +x

source $SNAP/etc/opx/opx-environment.sh

# Interactive sanity tests...
function doSanityCheck {
    read -n 1 -s -p "Press any key to continue..."
    echo
    opx-show-env
    echo
    echo "###########################################"
    echo
    echo "The previous command should show data about Chassis, Power Supplies, Fan Trays, and fans."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    cps_model_info
    echo
    echo "###########################################"
    echo
    echo "The previous command should show several CPS model types."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    cps_model_info base-pas
    echo
    echo "###########################################"
    echo
    echo "The previous command should show many types of registered records."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    cps_get_oid.py observed base-pas/psu
    echo
    echo "###########################################"
    echo
    echo "The previous command should show data for power supplies."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    cps_get_oid.py observed base-pas/temperature
    echo
    echo "###########################################"
    echo
    echo "The previous command should show data for temperature sensors."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    cps_get_oid.py observed base-pas/fan-tray
    echo
    echo "###########################################"
    echo
    echo "The previous command should show data for fan trays."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    cps_get_oid.py observed base-pas/fan
    echo
    echo "###########################################"
    echo
    echo "The previous command should show data for fans."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    opx-show-transceivers summary
    echo
    echo "###########################################"
    echo
    echo "The previous command should list all the transceivers in the switch."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    cps_get_oid.py base-ip/ipv4/address
    echo
    echo "###########################################"
    echo
    echo "The previous command should show information about the loopback and management interfaces."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    cps_get_oid.py base-if-phy/hardware-port
    echo
    echo "###########################################"
    echo
    echo "The previous command should show information about the hardware ports."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    cps_get_oid.py base-if-phy/front-panel-port
    echo
    echo "###########################################"
    echo
    echo "The previous command should show information about the front-panel ports."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    opx-show-stats if_stat e101-001-0
    echo
    echo "###########################################"
    echo
    echo "The previous command should show I/O stats for port e101-001-0."
    echo
    read -n 1 -s -p "Press any key to continue..."
    echo
    echo
    cps_get_oid.py observed dell-base-if-cmn/if/interfaces-state/interface if/interfaces-state/interface/type=ianaift:ethernetCsmacd  if/interfaces-state/interface/name=e101-001-0
    echo 
    echo "###########################################"
    echo
    echo "The previous command should show ethernet information for port e101-001-0."

    if [ ! -z "$FLEX" ] ; then
        echo
        read -n 1 -s -p "Press any key to continue..."
        echo
        echo
        curl -X GET --header 'Content-Type: application/json' --header 'Accept: apllication/json' 'http://localhost:8080/public/v1/state/SystemSwVersion' | python -m json.tool
        echo
        echo "###########################################"
        echo
        echo "The previous command should show all FlexSwitch version info."
        echo
        read -n 1 -s -p "Press any key to continue..."
        echo
        echo
        curl -X GET --header 'Content-Type: application/json' --header 'Accept: application/json' 'http://localhost:8080/public/v1/state/SystemStatus' | python -m json.tool
        echo
        echo "###########################################"
        echo
        echo "The previous command should show all FlexSwitch daemons as healthy."
        echo
        read -n 1 -s -p "Press any key to continue..."
        echo
        echo
        curl -X GET --header 'Content-Type: application/json' --header 'Accept: application/json' 'http://localhost:8080/public/v1/state/Ports' | python -m json.tool
        echo
        echo "###########################################"
        echo
        echo "The previous command should show the state of the ports."
    fi
}

#
# Main
#

doSanityCheck
