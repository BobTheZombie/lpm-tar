# Validation — 2026-10-30

Local host: Linux x86-64, AMD EPYC 9V74 virtual machine, 9 visible CPUs,
glibc 2.39. This is not a physical Ryzen system.

## Meson/Ninja build migration

* Meson setup followed by direct Ninja compilation built tar, rmt, support
  libraries, and Autotest helpers from individual C sources. Gnulib's shipped
  configure probes remain in setup; no GNU Make compilation wrapper is used.
* Configure probes explicitly use Meson's selected C standard and large-file
  mode. This avoids GCC 15/16 defaulting to C23 during probing but compiling as
  GNU C11, which otherwise leaves boolean compatibility definitions inconsistent.
* Four Meson core tests passed: dispatched/scalar checksums, extraction with
  injected write faults, and gzip/pigz integration.
* The upstream suite ran directly through Meson/Autotest with four workers:
  244 cases, 218 executed, 215 passed, 3 failed, 26 skipped. Failures remain
  90/104/106, the same baseline read-only-directory permission failures.
* Generic build installed tar, rmt, shipped manuals and translations into a
  temporary DESTDIR. A repeated Ninja compile reported no work to do.
* A znver2 build with LTO enabled, `assembly=false`, `nls=false`, `rmt=false`,
  `gzip_backend=gzip`, ACL/SELinux disabled, and upstream tests disabled built,
  passed all four core tests, and staged an install without rmt. No handwritten
  AVX2 kernel symbol remained. Its gzip default successfully bypassed a deliberately
  failing pigz executable.
* A failing `make` shim was placed first on PATH during configure/bootstrap,
  compilation, tests and the optional codec builder. It was never invoked.
  The bridge disables unused Make dependency generation and substitutes a no-op
  for configure's unused Make capability checks.
* The codec helper now uses CMake/Ninja for zlib-ng and a direct Meson/Ninja
  target for pigz. All 69 zlib-ng CTest cases and the pigz round-trip smoke test
  passed, including gzip, zlib, ZIP, block/thread settings and stream errors.
* The most recent preceding revision, `b3b5a7480a71596c8144b9e837c4833b3c4117a3`,
  passed GCC, Clang and accelerated-codec CI jobs:
  https://github.com/BobTheZombie/lpm-tar/actions/runs/41077726262

Current CI is migrated to Meson/Ninja and additionally covers required ACL/SELinux
features, staged installation, and minimal build options. Its results should be
checked separately from these local results. Cross builds are explicitly rejected;
this migration retains Autoconf feature probes rather than reimplementing gnulib.

## Second optimization pass: assembly and gzip pipeline

* Portable `-O3 -g -pthread` build and Zen 2 `-O3 -g -flto -pthread
  -march=znver2` build: passed.
* Existing differential extraction/fault suite: passed. This covers 1/2/4/32
  extraction workers, scalar/AVX2 dispatch, repeated paths, links, metadata,
  ring reuse, short writes, EINTR, ENOSPC, truncation and sparse fallback.
* Checksum reference comparison: 100,000 randomized unaligned headers passed
  with assembly dispatch and forced portable C. Guard-page tests passed for
  all-zero/all-high-bit headers ending exactly at an inaccessible page.
* Legacy signed-checksum archive accepted by the new cold fallback path.
* New gzip integration suite passed for the generic and znver2 tar builds:
  gzip/pigz round trips, `-z` and `--pigz`, automatic gzip magic detection,
  `-a` suffix selection, stdin/stdout, shared and separate thread settings,
  explicit gzip and `-I`, missing-pigz fallback, forced-pigz failure, permission
  errors, corrupt CRC and truncated gzip streams.
* Isolated pigz 2.8 + zlib-ng 2.3.3 build: passed zlib-ng's `make check` and
  pigz's `make test`. `pigz -vV` identifies zlib-ng. `ldd` shows no dynamic
  dependency on system libz; libc/libm remain dynamically linked.
* Disassembly confirms hand-written `vpsadbw`/`vpaddq`/`vzeroupper` in tar's
  header kernel and PCLMUL CRC instructions in the accelerated pigz binary.
* GNU tar suite with pigz/zlib-ng on PATH and `LPM_TAR_THREADS=4`: 244 cases,
  216 executed, 213 passed, 3 failed, 28 skipped. Failures remain 90/104/106,
  identical to the separately built unmodified GNU tar 1.35 baseline on this
  host (`Permission denied` extracting into read-only directories).
* Benchmark records: `benchmark-checksum-epyc.json` and
  `benchmark-gzip-epyc.json`; exact commands and qualifications are in README.

GitHub Actions now tests GCC, Clang and the optional accelerated-codec build.
Check the current commit's workflow run separately from these local results.
No physical Ryzen, non-x86, sanitizer, or durable-storage result is claimed.
Pigz's gzip inflate thread is still serial; helper threads pipeline I/O and CRC.

## Initial fork validation

The prior revision `d520b4f998829a8ec29f906f742f686bdde86760` passed both GCC
and Clang GitHub Actions jobs, including GNU tar and custom regression suites:
https://github.com/BobTheZombie/lpm-tar/actions/runs/41075206962

Its local GNU suite produced the same 213/3/28 result described above; the
three permission failures reproduce in unmodified upstream on this host.
Initial large-file extraction benchmark: `benchmark-epyc.json`.
The complete upstream import matches Git tree
`465273e5e38ff2ae94868287114752b2655bbe51`.
