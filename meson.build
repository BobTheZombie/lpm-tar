# SPDX-License-Identifier: GPL-3.0-or-later
project('lpm-tar', 'c', version: '1.35-lpm2', meson_version: '>=1.3.0',
  default_options: ['buildtype=release', 'c_std=gnu11', 'warning_level=1', 'b_lto=true'])
cc = meson.get_compiler('c')
py = import('python').find_installation('python3')
fs = import('fs')
if fs.exists(meson.project_build_root() / 'config.status')
  error('Use a fresh build directory, not an existing Autotools build directory.')
endif
if meson.is_cross_build() or host_machine.system() != 'linux'
  error('The initial Meson/gnulib bridge supports native Linux builds only.')
endif
threads = dependency('threads')
profile = get_option('cpu_profile')
cpu_args = []
if profile != 'generic'
  flag = '-march=' + profile
  if not cc.has_argument(flag)
    error('Compiler does not support CPU profile: ' + profile)
  endif
  cpu_args += flag
endif
feature_args = []
if not get_option('assembly')
  feature_args += '-DLPM_TAR_NO_ASM=1'
endif
backend = {'auto': 0, 'gzip': 1, 'pigz': 2}[get_option('gzip_backend')]
feature_args += '-DLPM_DEFAULT_GZIP_BACKEND=' + backend.to_string()
add_project_arguments(cpu_args + feature_args, language: 'c')
foreach feature : ['acl', 'selinux']
  opt = get_option(feature)
  mode = 'auto'
  if opt.enabled()
    mode = 'enabled'
  elif opt.disabled()
    mode = 'disabled'
  endif
  set_variable(feature + '_mode', mode)
  if opt.enabled()
    cc.find_library(feature, required: true)
    header = feature == 'acl' ? 'sys/acl.h' : 'selinux/selinux.h'
    if not cc.has_header(header)
      error('Requested feature header not found: ' + header)
    endif
  endif
endforeach
cfg = meson.project_build_root() / 'gnulib-config'
bridge = files('meson/gnulib-configure.py')
probe_flags = get_option('c_args') + cpu_args + ['-O2', '-pthread', '-D_FILE_OFFSET_BITS=64']
# Configure must see the same language mode as Ninja. New GCC defaults to C23,
# where bool is a keyword, while our selected GNU C11 needs gnulib's bool setup.
if get_option('c_std') != 'none'
  probe_flags += '-std=' + get_option('c_std')
endif
probe_ldflags = get_option('c_link_args')
run_command(py, bridge,
  '--source', meson.project_source_root(), '--build', meson.project_build_root(),
  '--cc', ' '.join(cc.cmd_array()), '--cflags=' + ' '.join(probe_flags),
  '--ldflags=' + ' '.join(probe_ldflags),
  '--prefix', get_option('prefix'), '--bindir', get_option('prefix') / get_option('bindir'),
  '--libdir', get_option('prefix') / get_option('libdir'),
  '--libexecdir', get_option('prefix') / get_option('libexecdir'),
  '--localedir', get_option('prefix') / get_option('localedir'),
  '--acl', acl_mode, '--selinux', selinux_mode,
  '--nls', get_option('nls').to_string(), '--xattrs', get_option('xattrs').to_string(),
  '--rmt', get_option('rmt').to_string(), '--gzip', get_option('gzip_program'),
  '--archive', get_option('default_archive'), '--blocking', get_option('blocking_factor').to_string(), check: true)
query = [py, bridge, '--source', meson.project_source_root(), '--build', meson.project_build_root()]
gnu_sources = run_command(query, '--query', 'gnu', check: true).stdout().strip().split('\n')
lib_sources = run_command(query, '--query', 'lib', check: true).stdout().strip().split('\n')
tar_sources = run_command(query, '--query', 'src', check: true).stdout().strip().split('\n')
extra_links = run_command(query, '--query', 'link_args', check: true).stdout().strip()
link_args = extra_links == '' ? [] : extra_links.split('\n')
# Register configure templates and gnulib snippets as regeneration dependencies.
foreach input : run_command(query, '--query', 'inputs', check: true).stdout().strip().split('\n')
  fs.read(input)
endforeach
inc = include_directories('.', 'gnu', 'lib', 'src')
common_args = ['-DHAVE_CONFIG_H', '-DLOCALEDIR="' + (get_option('prefix') / get_option('localedir')) + '"']
libgnu = static_library('gnulib', gnu_sources, include_directories: inc,
  c_args: common_args + cc.get_supported_arguments(['-Wno-unused-parameter', '-Wno-unused-function']),
  dependencies: threads, install: false)
libtar = static_library('tar-support', lib_sources, include_directories: inc,
  c_args: common_args, dependencies: threads, install: false)
subdir('src')
if get_option('rmt')
  subdir('rmt')
endif
if get_option('tests')
  subdir('tests')
endif
if get_option('docs')
  install_man('doc/tar.1')
  if get_option('rmt')
    install_man('doc/rmt.8')
  endif
  install_data('COPYING', 'README.md', install_dir: get_option('datadir') / 'doc' / 'lpm-tar')
  install_data('doc/tar.info', 'doc/tar.info-1', 'doc/tar.info-2', 'doc/tar.info-3', install_dir: get_option('infodir'))
endif
if get_option('nls')
  foreach catalog : run_command(query, '--query', 'translations', check: true).stdout().strip().split('\n')
    lang = fs.stem(catalog)
    install_data(catalog, install_dir: get_option('localedir') / lang / 'LC_MESSAGES', rename: 'tar.mo')
  endforeach
endif
summary({'CPU profile': profile, 'Checksum assembly': get_option('assembly'),
  'Default gzip backend': get_option('gzip_backend'), 'Gnulib configure log': cfg / 'configure-output.log',
  'Build engine': 'Ninja; no GNU Make invocation'}, section: 'LPM tar')
