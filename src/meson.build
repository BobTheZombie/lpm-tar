# SPDX-License-Identifier: GPL-3.0-or-later
tar = executable('tar', tar_sources, include_directories: inc, c_args: common_args,
  link_with: [libtar, libgnu], dependencies: threads, link_args: link_args, install: true)
