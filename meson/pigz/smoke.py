#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import gzip, io, pathlib, subprocess, sys, zipfile, zlib
pigz=str(pathlib.Path(sys.argv[1]).resolve())
data=bytes(range(256))*1024+b'partial'
def run(args,data,ok=True):
    r=subprocess.run([pigz,*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert (r.returncode==0)==ok,(args,r.returncode,r.stderr)
    return r.stdout
for args in [[],['-b','32'],['-p','1'],['-p','4']]:
    packed=run(['-c',*args],data)
    assert gzip.decompress(packed)==data
    assert run(['-dc'],packed)==data
    run(['-t'],packed)
assert zlib.decompress(run(['-cz'],data))==data
with zipfile.ZipFile(io.BytesIO(run(['-cK'],data))) as z:
    assert z.read(z.namelist()[0])==data
for raw in [b'',b'x',b'xy',b'xyz']:
    assert run(['-cdf'],raw)==raw
    assert run(['-cdf'],gzip.compress(b'w')+raw)==b'w'+raw
run(['-t'],gzip.compress(data)[:-8],ok=False)
print('PASS: pigz gzip/zlib/zip, block/thread options, stream checking and forced-copy cases')
