# SPDX-License-Identifier: GPL-3.0-or-later
# Copied into the verified pigz release tree by lpm/build-pigz.sh.
project('lpm-pigz', 'c', version: '2.8', meson_version: '>=1.3.0',
  default_options: ['buildtype=release', 'c_std=gnu11'])
cc = meson.get_compiler('c')
py = import('python').find_installation('python3')
prefix = get_option('zlib_prefix')
if prefix == ''
  error('zlib_prefix must name the isolated zlib-ng installation')
endif
profile = get_option('cpu_profile')
if profile != 'generic'
  flag = '-march=' + profile
  if not cc.has_argument(flag)
    error('Compiler does not support ' + flag)
  endif
  add_project_arguments(flag, language: 'c')
endif
zlib = cc.find_library('z', dirs: prefix / 'lib', static: true, required: true)
math = cc.find_library('m', required: false)
sources = files('pigz.c', 'yarn.c', 'try.c',
  'zopfli/src/zopfli/deflate.c', 'zopfli/src/zopfli/blocksplitter.c',
  'zopfli/src/zopfli/tree.c', 'zopfli/src/zopfli/lz77.c',
  'zopfli/src/zopfli/cache.c', 'zopfli/src/zopfli/hash.c',
  'zopfli/src/zopfli/util.c', 'zopfli/src/zopfli/squeeze.c',
  'zopfli/src/zopfli/katajainen.c', 'zopfli/src/zopfli/symbols.c')
pigz = executable('pigz', sources, include_directories: include_directories(prefix / 'include'),
  dependencies: [zlib, math, dependency('threads')], install: true)
test('pigz-codec-roundtrips', py, args: [files('smoke.py'), pigz], timeout: 120)
