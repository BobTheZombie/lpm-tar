#!/usr/bin/env python3
"""Exercise real codecs plus observable backend selection and failure handling."""
import gzip, hashlib, io, json, os, pathlib, shutil, subprocess, sys, tarfile, tempfile
binary=str(pathlib.Path(sys.argv[1]).resolve())
pigz=shutil.which('pigz')
gzip_bin=shutil.which('gzip')
assert pigz and gzip_bin, 'Put pigz and gzip on PATH for integration tests'
def run(args, *, env, data=None, good=True):
    r=subprocess.run([binary,*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    assert (r.returncode==0)==good,(args,r.returncode,r.stderr.decode(errors='replace'))
    return r
with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td); source=root/'source';source.mkdir()
    payload=(bytes(range(256))*32768)+b'partial'
    (source/'large').write_bytes(payload)
    real_bin=root/'codec';real_bin.mkdir(); log=root/'calls.jsonl'
    os.symlink(gzip_bin,real_bin/'gzip')
    wrapper=real_bin/'pigz'
    wrapper.write_text(f'#!{sys.executable}\nimport os,sys,json\nwith open({str(log)!r},"a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\nos.execv({pigz!r},["pigz",*sys.argv[1:]])\n')
    wrapper.chmod(0o755)
    env=os.environ.copy();env['PATH']=str(real_bin)
    env.pop('LPM_TAR_THREADS',None)
    def calls():return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    # Creation flags and suffix inference all select the same gzip pipeline.
    for index,opts in enumerate([['-czf'],['--pigz','-cf'],['-caf']]):
        archive=root/f'output{index}.tar.gz'
        before=len(calls())
        run([*opts,str(archive),'--threads=3','--compression-threads=2','-C',str(source),'large'],env=env)
        assert calls()[before:]==[['-p','2']]
        with tarfile.open(archive,'r:gz') as tf:assert tf.extractfile('large').read()==payload
        dest=root/f'dest{index}';dest.mkdir();before=len(calls())
        run(['--threads=4','-xf',str(archive),'-C',str(dest)],env=env)
        assert calls()[before:]==[['-p','4','-d']]
        assert (dest/'large').read_bytes()==payload
    # Streaming input and stdin/stdout creation retain the pigz pipeline.
    dest=root/'stream';dest.mkdir()
    run(['--threads=2','-xz','-C',str(dest)],env=env,data=archive.read_bytes())
    assert (dest/'large').read_bytes()==payload
    stream=run(['--pigz','-cf','-','-C',str(source),'large'],env=env).stdout
    with tarfile.open(fileobj=io.BytesIO(stream),mode='r:gz') as tf:assert tf.extractfile('large').read()==payload
    # A forced gzip backend and -I explicitly bypass pigz.
    for opts in [['--gzip-backend=gzip','-czf'],['-I','gzip','-cf']]:
        before=len(calls());run([*opts,str(root/'explicit.gz'),'-C',str(source),'large'],env=env)
        assert len(calls())==before
    # Absent pigz falls back in auto mode for both creation and extraction.
    wrapper.rename(real_bin/'pigz.disabled')
    fallback=root/'fallback.gz'
    run(['-czf',str(fallback),'-C',str(source),'large'],env=env)
    dest=root/'fallback';dest.mkdir()
    run(['-xf',str(fallback),'-C',str(dest)],env=env)
    assert (dest/'large').read_bytes()==payload
    run(['--pigz','-tf',str(fallback)],env=env,good=False)
    # An installed but non-executable pigz must not silently fall back.
    wrapper.write_text('denied');wrapper.chmod(0o644)
    run(['-tzf',str(fallback)],env=env,good=False)
    wrapper.unlink();(real_bin/'pigz.disabled').rename(wrapper)
    # Corrupt CRC and truncated streams propagate codec failure.
    data=bytearray(fallback.read_bytes());data[-8]^=0xff
    bad=root/'bad.gz';bad.write_bytes(data)
    run(['-tzf',str(bad)],env=env,good=False)
    bad.write_bytes(fallback.read_bytes()[:-8])
    run(['-tzf',str(bad)],env=env,good=False)
    # Legacy Sun signed checksums remain accepted; unsigned path remains common.
    h=bytearray(512);h[:4]=b'\xffabc';h[100:108]=b'0000644\0';h[108:116]=b'0000000\0';h[116:124]=b'0000000\0';h[124:136]=b'00000000000\0';h[136:148]=b'00000000000\0';h[148:156]=b'        ';h[156]=ord('0')
    signed=sum(x if x<128 else x-256 for x in h)
    h[148:156]=(f'{signed:06o}\0 ').encode()
    legacy=root/'signed.tar';legacy.write_bytes(h+bytes(1024))
    run(['-tf',str(legacy)],env=env)
    for arg in ['--gzip-backend=wrong','--compression-threads=0','--compression-threads=33','--compression-threads=2x']:
        run([arg,'--help'],env=env,good=False)
print('PASS: gzip/pigz round trips, auto detection, suffixes, pipes, thread arguments, explicit filters, fallback, denied execution, CRC/truncation, legacy signed checksums')
