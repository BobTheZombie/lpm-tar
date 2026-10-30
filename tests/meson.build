# SPDX-License-Identifier: GPL-3.0-or-later
checksum_test = executable('checksum-test', '../lpm/checksum-test.c')
test('checksum-dispatch', checksum_test, suite: 'core')
test('checksum-scalar', checksum_test, env: ['LPM_TAR_SCALAR=1'], suite: 'core')
write_faults = shared_module('write-faults', '../lpm/write-faults.c',
  dependencies: cc.find_library('dl', required: false), name_prefix: '')
test('extraction-and-write-faults', py, args: [files('../lpm/test.py'), tar],
  env: ['LPM_TEST_INTERPOSER=' + write_faults.full_path()], depends: write_faults,
  timeout: 120, suite: 'core')
if find_program('pigz', required: false).found() and find_program('gzip', required: false).found()
  test('gzip-pigz-integration', py, args: [files('../lpm/gzip-test.py'), tar], timeout: 120, suite: 'core')
else
  warning('pigz/gzip unavailable: gzip-pigz-integration is not registered')
endif
if get_option('upstream_tests')
  genfile = executable('genfile', ['genfile.c', 'argcv.c'], include_directories: inc,
    c_args: common_args, link_with: libgnu, dependencies: threads, link_args: link_args)
  checkseekhole = executable('checkseekhole', 'checkseekhole.c', include_directories: inc,
    c_args: common_args, link_with: libgnu, dependencies: threads, link_args: link_args)
  ckmtime = executable('ckmtime', 'ckmtime.c', include_directories: inc,
    c_args: common_args, link_with: libgnu, dependencies: threads, link_args: link_args)
  test('gnu-tar-regression', find_program('sh'),
    args: [files('testsuite'), '-j' + get_option('test_jobs').to_string()],
    workdir: meson.current_build_dir(), depends: [tar, genfile, checkseekhole, ckmtime],
    timeout: 900, suite: 'upstream')
endif
