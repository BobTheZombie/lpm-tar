# Local validation — 2026-10-30

Host: Linux x86-64, AMD EPYC 9V74 virtual machine, 9 visible CPUs, glibc 2.39.
This is not a physical Ryzen system.

* Portable `-O3 -g -pthread` build: passed. Upstream developer `-Werror`
  was disabled because optional ACL/xattr stubs have unused parameters on this
  host. The provided build script uses `--disable-gcc-warnings` for release builds.
* Ryzen/Zen 2 profile: `lpm/build.sh znver2`, `-O3 -g -flto -pthread
  -march=znver2`: built and executed successfully on the available EPYC CPU.
* Custom differential extraction suite: passed at 1, 2, 4, and 32 workers,
  scalar/AVX2 dispatch; pipe/gzip input; repeated paths; hard/symbolic links;
  mode/mtime; truncated input; invalid thread counts; GNU sparse fallback.
* Fault injection: passed with 4 KiB short `pwrite` calls, repeated EINTR,
  and ENOSPC. Extraction returns failure for ENOSPC and truncated archives.
* Randomized checksum reference comparison: 100,000 unaligned headers passed
  in each of runtime AVX2 and forced scalar modes.
* Disassembly: AVX2 checksum function contains `vpsadbw` and `vpcmpgtb`.
* GNU tar regression suite: 244 cases, 216 executed, 213 passed, 3 failed,
  28 skipped. Same result with `LPM_TAR_THREADS=4`.
* The three failures (90, 104, 106) reproduce with **unmodified GNU tar 1.35**
  built separately using the same compiler/host: read-only directory extraction
  reports `Permission denied`. They are recorded, not hidden or marked passing.
* Initial extraction benchmark: see `benchmark-epyc.json` and README.
* Imported upstream Git tree exactly matches the local release import:
  `465273e5e38ff2ae94868287114752b2655bbe51`.

GitHub Actions is configured for GCC/Clang and is separate from these local
results. No Clang, physical Ryzen, non-x86, sanitizer, physical-disk, or isolated
checksum speed result is claimed. This is an experimental first optimization
release; large-file write parallelism does not make archive parsing or ordinary
single-stream decompression parallel.
