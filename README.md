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
* A hand-written, runtime-dispatched AVX2 header-checksum kernel for capable
  x86-64 CPUs, including Ryzen. Four independent accumulators hide reduction
  latency. The common path computes only the POSIX unsigned checksum; the legacy
  signed checksum is computed only when needed. Unaligned loads are supported,
  exactly 512 bytes are read, and `vzeroupper` avoids AVX/SSE transition penalties.
  GCC/Clang manage the inline assembly ABI and clobbers. Other CPUs use portable C;
  generic builds do not require AVX2.
* Optional `znver2` through `znver5`, `native`, and portable build profiles with
  `-O3` and link-time optimization. `znver2` is suitable for the Ryzen 5 4500U.
  Compiler support is required for each selected architecture.
* Seamless pigz selection for `-z`, `--pigz`, gzip magic detection, and gzip
  filename suffixes with `-a`. Automatic mode falls back to gzip only when pigz
  is absent. Installed but broken codecs and stream errors are reported.
* An optional isolated pigz/zlib-ng build with CPU-dispatched CRC, match-finding
  and inflate kernels. Its static zlib-ng link avoids changing the system zlib.

This version parallelizes **large-file data writes**, not simultaneous archive
members. Small-file workloads remain serial. Pigz parallelizes compression and
pipelines gzip decoding with helper threads, but ordinary gzip inflate itself
remains single-threaded. Sparse files, stdout, command
output and non-regular output retain upstream behavior. One worker is the default;
parallelism is opt-in until more hardware and workload measurements are available.

## Build and install with Meson/Ninja

Tar requires Meson >= 1.3, Ninja, Python 3, a C compiler, POSIX shell, sed and
standard Unix build tools. GNU Make, Autoconf, Automake and Bison are not required
for a release-source build. Native Linux builds are supported; cross compilation
is explicitly rejected until the gnulib probe bridge supports cross files.

```sh
meson setup build-generic --prefix=/usr --buildtype=release -Db_lto=true
meson compile -C build-generic -j4
meson test -C build-generic --print-errorlogs
DESTDIR="$PWD/stage" meson install -C build-generic
# Or install to the configured system prefix when ready:
# meson install -C build-generic
```

For your Ryzen 5 4500U / Zen 2:

```sh
meson setup build-znver2 --prefix=/usr -Dcpu_profile=znver2
ninja -C build-znver2
build-znver2/src/tar --threads=4 --no-same-owner -xf archive.tar -C destination
# Equivalent convenience wrapper:
lpm/build.sh znver2
```

`lpm/build.sh` now performs Meson setup/reconfiguration and Ninja compilation.
Use a fresh directory when switching from Autotools. `LPM_BUILD_DIR` and `JOBS`
remain supported. Extra wrapper arguments are Meson setup options, not configure
options. For example:

```sh
lpm/build.sh generic -Dassembly=false -Dnls=false -Drmt=false
meson configure build-generic -Dgzip_backend=gzip
meson compile -C build-generic
```

The supplied [`meson_options.txt`](meson_options.txt) exposes:

| Option | Default | Purpose |
| --- | --- | --- |
| `cpu_profile` | `generic` | `generic`, `native`, `znver2` through `znver5` |
| `assembly` | `true` | Runtime AVX2 checksum kernel; false forces portable C |
| `gzip_backend` | `auto` | Default `auto`, `gzip`, or required `pigz` |
| `gzip_program` | `gzip` | Fallback gzip executable |
| `acl`, `selinux` | `auto` | Feature options: `auto`, `enabled`, `disabled` |
| `xattrs`, `nls` | `true` | Extended attributes / native language support |
| `rmt`, `docs`, `tests` | `true` | Build/install helper, manuals, and test targets |
| `upstream_tests` | `true` | Register GNU tar's full Autotest suite |
| `test_jobs` | `4` | Parallel workers inside the upstream test suite |
| `default_archive` | `-` | Default archive name |
| `blocking_factor` | `20` | Default archive blocking factor |

Standard Meson options such as `prefix`, `bindir`, `libdir`, `libexecdir`,
`buildtype`, `b_lto`, `b_sanitize`, `c_args` and `c_link_args` remain available.
Selected CPU profiles require compiler support and set the binary's CPU baseline;
use `generic` for portable packages. For Clang LTO, use matching LLVM archive tools
and linker, for example `CC=/usr/bin/clang AR=/usr/bin/llvm-ar
RANLIB=/usr/bin/llvm-ranlib LDFLAGS=-fuse-ld=/usr/bin/ld.lld` during setup.

Meson setup retains GNU tar's shipped `configure` script for gnulib feature
checks, preserving its platform-specific source selection. A small bridge expands
only the configure-produced compatibility-header recipes. Make capability checks
and dependency-file generation are disabled/no-ops; no GNU Make command is run.
Ninja then compiles and links individual C files directly, and Meson handles
tests and installation. This is a Meson/Ninja build with an Autoconf probe bridge,
not a complete rewrite of gnulib's feature tests. Probe logs live in
`build-*/gnulib-config/`. Changed probe inputs trigger Meson regeneration;
use `meson setup --reconfigure build-generic` to regenerate manually removed
compatibility headers.

`LPM_TAR_THREADS=4` is an alternative to the command-line flag.
`LPM_TAR_SCALAR=1` forces the portable checksum path for testing.

## Seamless gzip and pigz integration

If pigz is on PATH, ordinary commands use it automatically:

```sh
build-znver2/src/tar --threads=4 -czf archive.tar.gz files
build-znver2/src/tar --threads=4 -xf archive.tar.gz -C destination
# Separate extraction and codec budgets:
build-znver2/src/tar --threads=4 --compression-threads=2 -xzf archive.tar.gz
# Require pigz; missing executable is an error:
build-znver2/src/tar --pigz --threads=4 -cf archive.tar.gz files
# Retain gzip explicitly:
build-znver2/src/tar --gzip-backend=gzip -czf archive.tar.gz files
```

`--gzip-backend=auto|gzip|pigz` defaults to auto and selects the backend only for
**gzip** archives; it does not turn other formats into gzip. `--pigz` selects gzip
format and requires pigz. `--threads=N`/`LPM_TAR_THREADS` also supplies pigz's `-p`
value unless `--compression-threads=N` overrides it. With no thread setting,
pigz gets the online CPU count capped at 32; extraction remains serial by default.
The two thread pools are separate budgets. Pigz `-p` is not an inflate-worker count;
`-p 1` disables its decompression helper threads. Explicit `-I` filters are preserved,
including their arguments, rather than rewritten. Existing system pigz works;
zlib-ng is optional. Gzip-format errors propagate to tar's exit status.

To build an accelerated codec without replacing system libraries:

```sh
lpm/build-pigz.sh znver2
export PATH="$PWD/build-codecs-znver2/prefix/bin:$PATH"
build-znver2/src/tar --threads=4 -czf archive.tar.gz files
```

The script downloads pinned pigz 2.8 and zlib-ng 2.3.3 sources, verifies SHA-256,
builds and tests both, and retains their license notices under the local prefix.
Zlib-ng uses its upstream CMake build with the Ninja generator; pigz uses the
small Meson project supplied under `meson/pigz/`. This helper needs CMake, Meson,
Ninja, a C compiler, curl, sha256sum, gzip and tar; it no longer invokes Make. Use `generic` for a
portable build or the same optional architecture profiles as tar. This does not
add hand-written DEFLATE code to tar: codec acceleration lives in zlib-ng, while
new tar assembly handles archive-header checksums.

Pigz's limitations are described in its [upstream manual](https://github.com/madler/pigz/blob/master/pigz.1).
Zlib-ng's [upstream documentation](https://github.com/zlib-ng/zlib-ng/tree/2.3.3)
describes CPU optimizations and runtime dispatch.

## Tests

```sh
meson test -C build-generic --print-errorlogs
cc -O3 lpm/checksum-test.c -o /tmp/checksum-test
/tmp/checksum-test
LPM_TAR_SCALAR=1 /tmp/checksum-test
meson test -C build-generic --suite core --print-errorlogs
meson test -C build-generic --suite upstream --print-errorlogs
python3 lpm/benchmark.py build-generic/src/tar
python3 lpm/gzip-test.py build-generic/src/tar  # requires pigz on PATH
python3 lpm/gzip-bench.py build-generic/src/tar
cc -O3 lpm/checksum-bench.c -o /tmp/checksum-bench
/tmp/checksum-bench
```

Local outcomes and environment limitations are recorded in `lpm/VALIDATION.md`.

The differential tests compare against system GNU tar, exercise 1/2/4/32 workers,
multiple ring rotations, exact and partial chunks, empty files, Unicode names,
duplicate members, hard and symbolic links, mode/time preservation, piped and gzip
input, truncated archives, short writes, interrupted writes, and ENOSPC failures.
The checksum test compares 100,000 randomized unaligned headers in each dispatch
mode against scalar reference sums. CI runs the upstream and custom suites through Meson with
GCC and Clang, stages installs, and checks minimal build options. CI status must be checked separately; configuring CI is not a pass.

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
archives can behave differently. Raw data: `lpm/benchmark-epyc.json`.

### Second optimization pass

Same EPYC host, four extraction workers and four pigz threads, 128 MiB mixed
random/text payload, three trials, default compression levels, warm cache, no fsync:

| Backend | Compress seconds | Extract seconds | Archive bytes |
| --- | ---: | ---: | ---: |
| gzip | 1.9463 | 0.6664 | 67,903,343 |
| pigz + system zlib | 0.5147 | 0.2482 | 67,843,197 |
| pigz + zlib-ng | 0.4345 | 0.2082 | 68,057,214 |

The accelerated pipeline was about **4.48× faster compressing** and **3.20× faster
extracting** than gzip on this workload, and about 1.18×/1.19× faster than pigz
with system zlib. Its archive was about 0.23% larger than gzip's. This is an
end-to-end pipeline comparison, not proof of parallel inflate or pure assembly
speedup. Raw data: `lpm/benchmark-gzip-epyc.json`.

The checksum microbenchmark's median over three trials of 10 million unaligned
headers was 7.28 ns/header for the new common path, versus 16.95 ns/header for the
previous always-dual-checksum SIMD path (about **2.33× faster**). This combines
assembly and avoiding unnecessary signed reductions, and does not imply a 2.33×
whole-archive speedup. Raw data: `lpm/benchmark-checksum-epyc.json`. To reproduce the
previous-path comparison, save the prior header with
`git show d520b4f998829a8ec29f906f742f686bdde86760:src/cpu-checksum.h > /tmp/lpm-checksum-v1.h`
and compile `lpm/checksum-bench.c` with
`-DLPM_PREVIOUS_HEADER='"/tmp/lpm-checksum-v1.h"'`.

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
