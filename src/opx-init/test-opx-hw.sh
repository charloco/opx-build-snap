#!/usr/bin/env bash

set -e
set +x

read -n 1 -s -p "Press any key to continue..."
echo
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
