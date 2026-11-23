#!/bin/bash
# Compile-check and host-test an Apertar-Core tree on this x86_64 host.
#   check_core.sh <core-source-dir> <tag> [lc|nolc|both] [tests]
# Builds into /home/user/build/<tag>-lc (with the locally built libcamera fork) and /home/user/build/<tag>-nolc.
# Uses ccache, so a tree that differs in a few files rebuilds in seconds. Prints one PASS/FAIL line per step.
SRC=${1:?source dir}; TAG=${2:?tag}; WHAT=${3:-both}; TESTS=${4:-}
export CCACHE_DIR=/home/user/build/ccache CCACHE_BASEDIR="$SRC" CCACHE_NOHASHDIR=1
rc=0
build() {   # $1 = lc|nolc
  local dir=/home/user/build/$TAG-$1 opt=ON
  [ "$1" = nolc ] && opt=OFF
  PKG_CONFIG_PATH=/home/user/opt/libcamera/lib/x86_64-linux-gnu/pkgconfig cmake -S "$SRC" -B "$dir" -G Ninja \
    -DAPERTARCORE_ENABLE_LIBCAMERA=$opt -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-Wall -Wextra" \
    -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache > "$dir.configure.log" 2>&1 || { echo "FAIL configure $1 (see $dir.configure.log)"; rc=1; return; }
  if nice -n 5 ninja -C "$dir" -j3 > "$dir.build.log" 2>&1; then
    echo "PASS build $1 ($(grep -c 'warning:' "$dir.build.log") warnings; log $dir.build.log)"
  else
    echo "FAIL build $1:"; grep -n -m8 'error' "$dir.build.log" | cut -c1-240; rc=1
  fi
}
case "$WHAT" in lc) build lc;; nolc) build nolc;; *) build lc; build nolc;; esac
if [ -n "$TESTS" ]; then
  OUT=/home/user/build/$TAG-tests; mkdir -p "$OUT"; cd "$SRC" || exit 2
  pass=0; fail=0
  for t in tools/*_test.cpp; do
    name=$(basename "$t" .cpp); [ "$name" = dng_payload_write_test ] && continue
    extra=""; case "$name" in tuning_tdn_strip_test) extra="$(pkg-config --cflags --libs yaml-0.1)";; esac
    srcs=$(grep -m3 -E '^\s*//\s+(c\+\+|g\+\+) ' "$t" | grep -oE '(src|third_party)/[A-Za-z0-9_/.]+\.(cpp|c)' | tr '\n' ' ')
    libs=$(grep -m3 -E '^\s*//\s+(c\+\+|g\+\+) ' "$t" | grep -oE ' -l[a-z0-9_+-]+' | tr '\n' ' ')
    if ccache g++ -std=c++20 -O2 -Wall -Wextra -I src -I include -I third_party/liblj92 "$t" $srcs -o "$OUT/$name" $extra $libs > "$OUT/$name.build.log" 2>&1 \
       && (cd "$OUT" && TMPDIR="$OUT" "./$name" > "$name.run.log" 2>&1); then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL host test $name: $(tail -2 "$OUT/$name.run.log" "$OUT/$name.build.log" 2>/dev/null | cut -c1-200 | tr '\n' ' ')"; fi
  done
  for s in tools/*_test.sh; do
    name=$(basename "$s" .sh)
    if TMPDIR="$OUT" sh "$s" > "$OUT/$name.run.log" 2>&1; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL host test $name: $(tail -2 "$OUT/$name.run.log" | cut -c1-200)"; fi
  done
  [ "$fail" = 0 ] && echo "PASS host tests ($pass)" || { echo "FAIL host tests ($fail of $((pass+fail)))"; rc=1; }
fi
exit $rc
