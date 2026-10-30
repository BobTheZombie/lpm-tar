#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
profile=${1:-generic}
if [ "$#" -gt 0 ]; then shift; fi
case "$profile" in
 generic|native|znver2|znver3|znver4|znver5) ;;
 *) echo 'Usage: lpm/build.sh [generic|native|znver2|znver3|znver4|znver5] [meson setup options]' >&2; exit 2 ;;
esac
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${LPM_BUILD_DIR:-"$source_dir/build-$profile"}
if [ -f "$build_dir/config.status" ]; then
 echo 'This directory contains an Autotools build. Set LPM_BUILD_DIR to a fresh directory.' >&2
 exit 2
fi
if [ -f "$build_dir/meson-private/coredata.dat" ]; then
 meson setup --reconfigure "$build_dir" "$source_dir" --backend=ninja --prefix=/usr -Dcpu_profile="$profile" "$@"
else
 meson setup "$build_dir" "$source_dir" --backend=ninja --prefix=/usr -Dcpu_profile="$profile" "$@"
fi
meson compile -C "$build_dir" -j"${JOBS:-$(getconf _NPROCESSORS_ONLN)}"
printf '\nBuilt %s/src/tar\n' "$build_dir"
