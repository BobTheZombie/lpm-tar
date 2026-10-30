#!/usr/bin/env python3
"""Differential extraction checks. Usage: test.py /absolute/path/to/new/tar"""
import hashlib, io, os, pathlib, subprocess, sys, tarfile, tempfile
binary = str(pathlib.Path(sys.argv[1]).resolve())
def run(*args, **kw):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
def snapshot(root):
    result = {}
    for p in sorted(root.rglob('*')):
        s = p.lstat()
        result[str(p.relative_to(root))] = (s.st_mode, s.st_mtime_ns, os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else '')
    return result
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    archive = root/'input.tar'
    # Cross multiple complete ring rotations, plus partial chunks and empty files.
    with tarfile.open(archive, 'w', format=tarfile.PAX_FORMAT) as tf:
        for name, length in [('large', 37*1024*1024+513), ('exact', 8*1024*1024), ('empty',0), ('small',511), ('unicodé',1025), ('large',9*1024*1024+7)]:
            data = (bytes(range(256))*((length+255)//256))[:length]
            h=tarfile.TarInfo(name); h.size=length; h.mode=0o640; h.mtime=1234567890
            tf.addfile(h, io.BytesIO(data))
        for name, target, kind in [('hard','large',tarfile.LNKTYPE), ('sym','large',tarfile.SYMTYPE)]:
            h=tarfile.TarInfo(name); h.type=kind; h.linkname=target; h.mtime=1234567890; tf.addfile(h)
    ref=root/'ref'; ref.mkdir()
    run('/usr/bin/tar','--no-same-owner','-xf',str(archive),'-C',str(ref))
    expected=snapshot(ref)
    for threads in [1,2,4,32]:
        for scalar in [False,True]:
            dest=root/f'out-{threads}-{scalar}'; dest.mkdir()
            env=os.environ.copy()
            if scalar: env['LPM_TAR_SCALAR']='1'
            run(binary,f'--threads={threads}','--no-same-owner','-xf',str(archive),'-C',str(dest), env=env)
            assert snapshot(dest)==expected, (threads,scalar)
            assert (dest/'hard').stat().st_ino == (dest/'large').stat().st_ino
    # Pipe input and compressed archives still use ordered parsing.
    for compressed in [False, True]:
        dest=root/f'pipe-{compressed}'; dest.mkdir()
        payload=archive.read_bytes()
        if compressed:
            import gzip
            payload=gzip.compress(payload)
        run(binary,'--threads=4','--no-same-owner','-xz' if compressed else '-x','-C',str(dest),input=payload)
        assert snapshot(dest)==expected
    # LD_PRELOAD interposer is optional; CI builds it to exercise error paths.
    if os.environ.get('LPM_TEST_INTERPOSER'):
        env=os.environ.copy(); env['LD_PRELOAD']=env['LPM_TEST_INTERPOSER']
        dest=root/'short-writes'; dest.mkdir()
        run(binary,'--threads=4','--no-same-owner','-xf',str(archive),'-C',str(dest),env=env)
        assert snapshot(dest)==expected
        env['LPM_TEST_ENOSPC']='1'
        result=subprocess.run([binary,'--threads=4','--no-same-owner','-xf',str(archive),'-C',str(dest)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode != 0 and b'No space left' in result.stderr
    # GNU sparse members retain the upstream sparse path and allocation behavior.
    sparse_source=root/'sparse-source'; sparse_source.mkdir()
    with (sparse_source/'holes').open('wb') as f:
        f.write(b'begin'); f.seek(32*1024*1024); f.write(b'end')
    sparse_archive=root/'sparse.tar'
    run('/usr/bin/tar','-S','-cf',str(sparse_archive),'-C',str(sparse_source),'holes')
    sparse_out=root/'sparse-out'; sparse_out.mkdir()
    run(binary,'--threads=4','--no-same-owner','-xf',str(sparse_archive),'-C',str(sparse_out))
    assert (sparse_out/'holes').read_bytes()==(sparse_source/'holes').read_bytes()
    assert (sparse_out/'holes').stat().st_blocks < 128
    # Truncated large member must produce a failure, joining workers first.
    result=subprocess.run([binary,'--threads=4','--no-same-owner','-x','-C',str(root/'pipe-False')],input=archive.read_bytes()[:9*1024*1024],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert result.returncode != 0
    for bad in ['0','33','-1','abc','2x']:
        assert subprocess.run([binary,f'--threads={bad}','--help'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode != 0
print('PASS: differential extraction, ring reuse, duplicate paths, links, metadata, pipes, gzip, truncation, invalid threads, sparse fallback')
