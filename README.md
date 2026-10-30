# LPM tar

An experimental GNU tar fork for LPM Linux, based on the complete GNU tar
1.35 release source. Upstream authorship, GNU tar behavior, archive formats,
manuals, translations and licensing are retained. This is a source fork, not
an official GNU release or a GitHub fork-network mirror.

## Implemented optimizations

* `--threads=N` (1–32): bounded pthread workers write independent 1 MiB chunks
  of a regular file using `pwrite`. Files smaller than 8 MiB retain the original
  path. Workers persist for the duration of a qualifying file, avoiding thread
  creation per chunk. The ring uses at most N MiB of payload buffers.
* Archive parsing, file opening, pathname security checks, member ordering,
  sparse-file handling and metadata application remain on the original thread.
  All workers finish before metadata changes or another member is processed.
  Repeated filenames and hard-link dependencies therefore retain archive order.
* Runtime-dispatched AVX2 header checksums on capable x86-64 CPUs, including
  Ryzen. The vector reduction computes both POSIX unsigned and legacy signed
  checksums. Unaligned loads are supported. GCC/Clang intrinsics generate
  `vpsadbw`/`vpcmpgtb` assembly; the compiler manages ABI and register allocation.
  Other CPUs use portable C. There is no global AVX2 requirement in generic builds.
* Optional `znver2` through `znver5`, `native`, and portable build profiles with
  `-O3` and link-time optimization. `znver2` is suitable for the Ryzen 5 4500U.
  Compiler support is required for each selected architecture.

This version parallelizes **large-file data writes**, not simultaneous archive
members. Small-file workloads remain serial. Compressed input can use the writer,
but this does not parallelize the decompressor. Sparse files, stdout, command
output and non-regular output retain upstream behavior. One worker is the default;
parallelism is opt-in until more hardware and workload measurements are available.

## Build and run

```sh
lpm/build.sh generic
# Ryzen 5 4500U / Zen 2; binary requires this CPU feature baseline:
lpm/build.sh znver2
build-znver2/src/tar --threads=4 --no-same-owner -xf archive.tar -C destination
```

Use an absolute archive path when appropriate for `-C`. `LPM_TAR_THREADS=4`
is an alternative to the command-line flag. Invalid values are rejected.
`LPM_TAR_SCALAR=1` forces the portable checksum path for testing.
No installation is performed by the build script. Build as an ordinary user;
GNU configure requires `FORCE_UNSAFE_CONFIGURE=1` if building as root.
Profiles above Zen 2 should not be used for packages intended for the 4500U.

## Tests

```sh
make -C build-generic -j4 check
cc -O3 lpm/checksum-test.c -o /tmp/checksum-test
/tmp/checksum-test
LPM_TAR_SCALAR=1 /tmp/checksum-test
cc -shared -fPIC lpm/write-faults.c -ldl -o /tmp/write-faults.so
LPM_TEST_INTERPOSER=/tmp/write-faults.so python3 lpm/test.py build-generic/src/tar
python3 lpm/benchmark.py build-generic/src/tar
```

Local outcomes and environment limitations are recorded in `lpm/VALIDATION.md`.

The differential tests compare against system GNU tar, exercise 1/2/4/32 workers,
multiple ring rotations, exact and partial chunks, empty files, Unicode names,
duplicate members, hard and symbolic links, mode/time preservation, piped and gzip
input, truncated archives, short writes, interrupted writes, and ENOSPC failures.
The checksum test compares 100,000 randomized unaligned headers in each dispatch
mode against scalar reference sums. CI runs the upstream and custom suites with
GCC and Clang. CI status must be checked separately; configuring CI is not a pass.

## Measurement

An initial run on AMD EPYC 9V74 (9 visible virtual CPUs), 256 MiB regular member,
three trials per worker count, produced these warm-cache median times:

| Workers | Seconds | MiB/s |
| --- | ---: | ---: |
| 1 | 0.11157 | 2295 |
| 2 | 0.06551 | 3908 |
| 4 | 0.05193 | 4930 |
| 8 | 0.05629 | 4548 |

Four workers were approximately 2.15× faster than this fork's serial path in this
specific run. These timings do not include `fsync`, do not measure durable disk
throughput, and are not a Ryzen benchmark. HDDs, SSDs, tiny files and compressed
archives can behave differently. The checksum optimization has correctness tests
but no isolated performance claim. Raw data: `lpm/benchmark-epyc.json`.

## Source provenance and license

Imported from `https://ftp.gnu.org/gnu/tar/tar-1.35.tar.xz`.
SHA-256: `4d62ff37342ec7aed748535323930c7cf94acf71c3591882b26a7ea50f3edc16`.
The release signature was not independently verified in this environment.
The import is preserved in its own commit for auditing and upstream comparisons.

GNU tar and the LPM changes are GPL-3.0-or-later; see `COPYING` and the individual
source notices. Documentation retains its original GNU FDL terms. New LPM files
are marked with GPL-3.0-or-later notices. This experimental optimization fork does
not imply an independent security audit or a comprehensive backport of fixes
published after the upstream release.
