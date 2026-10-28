#!/bin/bash
# Host syntax check of the Core sources touched by T33/T34, with libcamera headers (libcamera-apertar 6b0b49f3, meson-generated).
# Usage: hostcheck-core.sh <core tree>
C=${1:-/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/t34/core}
F="-std=c++20 -fsyntax-only -Wall -Wextra -Wno-unused-parameter -I$C/src -I$C/include -I/home/user/tiramisioux/libcamera-apertar/include -I/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/lcbuild/include -DAPERTARCORE_HAS_LIBCAMERA=1 -DAPERTARCORE_HAS_JPEG=1 -DAPERTARCORE_HAS_TURBOJPEG=0 -DAPERTARCORE_HAS_LIBAV=0"
rc=0
for f in src/camera/CameraController.cpp src/ApertarCoreApp.cpp src/web/WebControlPage.cpp; do
  out=$(g++ $F $C/$f 2>&1); n=$(printf '%s\n' "$out" | grep -c 'error:'); w=$(printf '%s\n' "$out" | grep -c 'warning:')
  echo "$f: errors=$n warnings=$w"; [ "$n" = 0 ] || { printf '%s\n' "$out" | grep -A3 'error:' | head -40; rc=1; }
done
exit $rc
