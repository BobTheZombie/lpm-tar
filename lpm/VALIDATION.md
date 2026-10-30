# Validation — 2026-10-30

Local host: Linux x86-64, AMD EPYC 9V74 virtual machine, 9 visible CPUs,
glibc 2.39. This is not a physical Ryzen system.

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
