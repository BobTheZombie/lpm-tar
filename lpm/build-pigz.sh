#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Build an isolated pigz with statically linked, runtime-dispatched zlib-ng.
set -eu
profile=${1:-generic}
case "$profile" in
 generic) architecture= ;;
 native|znver2|znver3|znver4|znver5) architecture="-march=$profile" ;;
 *) echo 'Usage: lpm/build-pigz.sh [generic|native|znver2|znver3|znver4|znver5]' >&2; exit 2 ;;
esac
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=${LPM_CODEC_BUILD_DIR:-"$source_dir/build-codecs-$profile"}
mkdir -p "$work_dir"
work_dir=$(CDPATH= cd -- "$work_dir" && pwd)
prefix="$work_dir/prefix"
jobs=${JOBS:-$(getconf _NPROCESSORS_ONLN)}
fetch () {
  if [ ! -f "$work_dir/$1" ]; then
    curl --fail --location --retry 2 "$2" -o "$work_dir/$1"
  fi
  printf '%s  %s\n' "$3" "$work_dir/$1" | sha256sum -c -
}
fetch pigz-2.8.tar.gz https://zlib.net/pigz/pigz-2.8.tar.gz \
 eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0
fetch zlib-ng-2.3.3.tar.gz https://github.com/zlib-ng/zlib-ng/archive/refs/tags/2.3.3.tar.gz \
 f9c65aa9c852eb8255b636fd9f07ce1c406f061ec19a2e7d508b318ca0c907d1
if [ ! -d "$work_dir/pigz-2.8" ]; then
 tar --no-same-owner -xf "$work_dir/pigz-2.8.tar.gz" -C "$work_dir"
fi
if [ ! -d "$work_dir/zlib-ng-2.3.3" ]; then
 tar --no-same-owner -xf "$work_dir/zlib-ng-2.3.3.tar.gz" -C "$work_dir"
fi
mkdir -p "$prefix/bin" "$prefix/share/licenses/pigz-zlib-ng"
cmake -S "$work_dir/zlib-ng-2.3.3" -B "$work_dir/zlib-ninja" -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
 -DZLIB_COMPAT=ON -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON -DWITH_GTEST=OFF \
 -DWITH_OPTIM=ON -DWITH_RUNTIME_CPU_DETECTION=ON \
 -DCMAKE_C_FLAGS="${CFLAGS:--O3 -g} $architecture"
cmake --build "$work_dir/zlib-ninja" --parallel "$jobs"
ctest --test-dir "$work_dir/zlib-ninja" --output-on-failure --parallel "$jobs"
cmake --install "$work_dir/zlib-ninja"
# Pigz has no upstream Meson files; provide a direct target for its C sources.
cp "$source_dir/meson/pigz/meson.build" "$work_dir/pigz-2.8/meson.build"
cp "$source_dir/meson/pigz/meson_options.txt" "$work_dir/pigz-2.8/meson_options.txt"
cp "$source_dir/meson/pigz/smoke.py" "$work_dir/pigz-2.8/smoke.py"
if [ -f "$work_dir/pigz-ninja/meson-private/coredata.dat" ]; then
 meson setup --reconfigure "$work_dir/pigz-ninja" "$work_dir/pigz-2.8" \
  --backend=ninja --prefix="$prefix" -Dzlib_prefix="$prefix" -Dcpu_profile="$profile"
else
 meson setup "$work_dir/pigz-ninja" "$work_dir/pigz-2.8" \
  --backend=ninja --prefix="$prefix" -Dzlib_prefix="$prefix" -Dcpu_profile="$profile"
fi
meson compile -C "$work_dir/pigz-ninja" -j"$jobs"
meson test -C "$work_dir/pigz-ninja" --print-errorlogs
meson install -C "$work_dir/pigz-ninja"
cd "$work_dir/pigz-2.8"
cp README "$prefix/share/licenses/pigz-zlib-ng/pigz-README"
cp "$work_dir/zlib-ng-2.3.3/LICENSE.md" "$prefix/share/licenses/pigz-zlib-ng/zlib-ng-LICENSE.md"
printf '\nBuilt %s/bin/pigz\nUse: PATH="%s/bin:$PATH" tar -czf archive.tar.gz files\n' "$prefix" "$prefix"
