#!/bin/bash
# Compile-check an Apertar-UI tree on this x86_64 host (Qt 6.4, QML compiled ahead of time).
#   check_ui.sh <ui-source-dir> <tag>
SRC=${1:?source dir}; TAG=${2:?tag}; dir=/home/user/build/$TAG-ui
export CCACHE_DIR=/home/user/build/ccache CCACHE_BASEDIR="$SRC" CCACHE_NOHASHDIR=1
cmake -S "$SRC" -B "$dir" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache > "$dir.configure.log" 2>&1 || { echo "FAIL configure ui (see $dir.configure.log)"; exit 1; }
if nice -n 5 ninja -C "$dir" -j3 > "$dir.build.log" 2>&1; then echo "PASS build ui ($(grep -c 'warning:' "$dir.build.log") warnings; log $dir.build.log)"
else echo "FAIL build ui:"; grep -n -m10 -i 'error' "$dir.build.log" | cut -c1-240; exit 1; fi
