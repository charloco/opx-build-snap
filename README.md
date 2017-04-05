# OPX on Snappy

This repository includes files necessary to generate Ubuntu Snaps for OpenSwitch.

The Snaps are platform-specific, so there will be one Snap for each supported platform.

## Vagrant File

The directory opxUbuntuDevel contains a Vagrantfile that can be used to create a development machine on Ubuntu/Xenial.

## Building a OpenSwitch Snap for Ubuntu-Core.

The process to build a Snap follows.

  1. Perform the "normal" build of OpenSwitch on a Ubuntu Xenial system or VM.
     NOTE: The target distro for pbuilder muxt be 'xenial'.

  2. Create a symbolic link snapcraft.yaml to the platform-specific yaml file.

  3. snapcraft clean && snapcraft
     This will generate a platform-specific Snap that can be installed on a target running Ubuntu-Core.

## Installing

  * sudo snap install openswitch-<platform>_*.snap

## Testing

  * sudo /snap/bin/openswitch-dell-vm.test-opx


## Notes

  * opx-build-snap/snap/plugins/x_dump.py
    * This is a custom plugin derived from the _dump_ plugin.
    * It "snapifies" some files at install time.
      * Prepends $SNAP to the directories in opx-environment
      * Appends some Snap-specific enviornment vars to opx-environment
      * Fixes up the python and bash shebangs to something acceptable by Ubuntu
  * opx-build-snap/src/opx-init/dropins
    * Service file dropins to enhance some service files for teh Snap
  * opx-build-snap/src/opx-init/snap-service-helper.py
    * This command does all the heavy lifting to start/stop OPX in the snap
    * It uses the existing service files and the local dropins to start the OPX services.

