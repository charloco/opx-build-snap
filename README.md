* Building a OpenSwitch Snap for Ubuntu-Core.

This repository includes files necessary to generate Ubuntu Snaps for OpenSwitch.

The Snaps are platform-specific, so there will be one Snap for each supported platform.

The process to build a Snap follows.

1. Perform the "normal" build of OpenSwitch on a Ubuntu Xenial system or VM.
   Use 'opx-build/scripts/opx_build all' to build then OpenSwitch .deb files.

2. Create a symbolic link snapcraft.yaml to the platform-specific yaml file.

3. snapcraft clean && snapcraft
   This will generate a platform-specific Snap that can be installed on a target running Ubuntu-Core.
