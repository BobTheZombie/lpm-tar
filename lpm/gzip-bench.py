#!/usr/bin/env python3
"""Reproducible warm-cache gzip pipeline benchmark; does not measure fsync."""
import argparse,hashlib,json,os,pathlib,platform,random,shutil,statistics,subprocess,tempfile,time
p=argparse.ArgumentParser();p.add_argument('tar');p.add_argument('--mib',type=int,default=128);p.add_argument('--runs',type=int,default=3);p.add_argument('--threads',type=int,default=4);p.add_argument('--optimized-pigz',default=shutil.which('pigz'));p.add_argument('--stock-pigz');a=p.parse_args()
binary=str(pathlib.Path(a.tar).resolve());rows=[]
with tempfile.TemporaryDirectory() as td:
 root=pathlib.Path(td);source=root/'source';source.mkdir();payload=source/'payload'
 rng=random.Random(47021);unit=rng.randbytes(32768)+(b'LPM Linux tar pipeline '+bytes(range(64)))*512;unit=unit[:65536]
 with payload.open('wb') as f:
  left=a.mib*1024*1024
  while left:n=min(left,len(unit));f.write(unit[:n]);left-=n
 expected=hashlib.sha256(payload.read_bytes()).hexdigest()
 cases=[('gzip','gzip',None)]
 if a.stock_pigz:cases.append(('pigz-system-zlib','pigz',a.stock_pigz))
 if a.optimized_pigz:cases.append(('pigz-zlib-ng','pigz',a.optimized_pigz))
 for name,backend,codec in cases:
  env=os.environ.copy()
  if codec:
   bindir=root/name;bindir.mkdir();os.symlink(str(pathlib.Path(codec).resolve()),bindir/'pigz');env['PATH']=str(bindir)+os.pathsep+env['PATH']
  compress=[];decompress=[];sizes=[]
  for i in range(a.runs):
   archive=root/f'{name}-{i}.gz';dest=root/f'{name}-{i}';dest.mkdir()
   args=[binary,f'--threads={a.threads}',f'--compression-threads={a.threads}',f'--gzip-backend={backend}']
   start=time.perf_counter();subprocess.run([*args,'-czf',str(archive),'-C',str(source),'payload'],env=env,check=True);compress.append(time.perf_counter()-start)
   start=time.perf_counter();subprocess.run([*args,'-xzf',str(archive),'-C',str(dest)],env=env,check=True);decompress.append(time.perf_counter()-start)
   assert hashlib.sha256((dest/'payload').read_bytes()).hexdigest()==expected
   sizes.append(archive.stat().st_size);(dest/'payload').unlink();dest.rmdir();archive.unlink()
  rows.append(dict(backend=name,compression_seconds=compress,decompression_seconds=decompress,compressed_bytes=sizes,median_compression=statistics.median(compress),median_decompression=statistics.median(decompress)))
print(json.dumps(dict(platform=platform.platform(),cpu=next((x.split(':',1)[1].strip() for x in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),''),mib=a.mib,runs=a.runs,threads=a.threads,workload='64 KiB repeated units, half deterministic random bytes, half repeated text/binary; warm cache, no fsync',results=rows),indent=2))
