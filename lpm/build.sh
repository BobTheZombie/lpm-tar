#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
profile=${1:-generic}
if [ "$#" -gt 0 ]; then shift; fi
case "$profile" in
 generic) architecture= ;;
 native|znver2|znver3|znver4|znver5) architecture="-march=$profile" ;;
 *) echo 'Usage: lpm/build.sh [generic|native|znver2|znver3|znver4|znver5]' >&2; exit 2 ;;
esac
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${LPM_BUILD_DIR:-"$source_dir/build-$profile"}
# Git checkouts do not preserve the release tarball timestamp ordering.
# Generated build files are shipped; avoid requiring obsolete autotool versions.
touch "$source_dir/aclocal.m4"
touch "$source_dir/configure" "$source_dir/config.h.in"
find "$source_dir" -name Makefile.in -not -path '*/build-*/*' -exec touch {} +
touch "$source_dir/doc/stamp-vti" "$source_dir/doc/version.texi" "$source_dir/tests/testsuite"
find "$source_dir/doc" -name '*.info*' -exec touch {} +
mkdir -p "$build_dir"
cd "$build_dir"
# Native/znver builds are deliberately opt-in; generic retains runtime AVX2 dispatch.
"$source_dir/configure" --disable-gcc-warnings --prefix=/usr \
 CFLAGS="${CFLAGS:--O3 -g -flto -pthread} $architecture" \
 LDFLAGS="${LDFLAGS:--flto}" "$@"
make -j"${JOBS:-$(getconf _NPROCESSORS_ONLN)}"
printf '\nBuilt %s/src/tar\n' "$build_dir"
