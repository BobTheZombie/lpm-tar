# SPDX-License-Identifier: GPL-3.0-or-later
rmt = executable('rmt', 'rmt.c', include_directories: inc, c_args: common_args,
  link_with: libgnu, dependencies: threads, link_args: link_args,
  install: true, install_dir: get_option('libexecdir'))
