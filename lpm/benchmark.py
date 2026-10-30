#!/usr/bin/env python3
"""Warm-cache extraction timings; these are not durable-storage throughput."""
import argparse,json,pathlib,statistics,subprocess,tempfile,time,tarfile,io,os,platform
p=argparse.ArgumentParser();p.add_argument('tar');p.add_argument('--mib',type=int,default=256);p.add_argument('--runs',type=int,default=3);a=p.parse_args();binary=str(pathlib.Path(a.tar).resolve())
with tempfile.TemporaryDirectory() as td:
 r=pathlib.Path(td); archive=r/'input.tar'
 with tarfile.open(archive,'w') as tf:
  h=tarfile.TarInfo('payload');h.size=a.mib*1024*1024
  class Source:
   def read(self,n):return bytes(range(256))*(n//256)+bytes(range(n%256))
  tf.addfile(h,Source())
 rows=[]
 for n in [1,2,4,8]:
  times=[]
  for i in range(a.runs):
   dest=r/f'out-{n}-{i}';dest.mkdir();start=time.perf_counter()
   subprocess.run([binary,f'--threads={n}','--no-same-owner','-xf',str(archive),'-C',str(dest)],check=True)
   times.append(time.perf_counter()-start)
   (dest/'payload').unlink();dest.rmdir()
  rows.append(dict(threads=n,seconds=times,median_seconds=statistics.median(times),MiB_per_second=a.mib/statistics.median(times)))
 print(json.dumps(dict(platform=platform.platform(),cpu=next((x.split(':',1)[1].strip() for x in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),''),mib=a.mib,runs=a.runs,cache='warm; no fsync; virtualized filesystem',results=rows),indent=2))
