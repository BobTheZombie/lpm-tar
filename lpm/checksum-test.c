/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#ifdef __linux__
#include <sys/mman.h>
#include <unistd.h>
#include <string.h>
#endif
#include "../src/cpu-checksum.h"
int main (void) {
  unsigned char bytes[513];
  uint32_t seed=1;
  int a,b,u,s;
  for (unsigned round=0;round<100000;round++) {
    u=s=0;
    for (unsigned i=0;i<512;i++) {
      seed=seed*1664525+1013904223;
      bytes[i+1]=seed>>24; u+=bytes[i+1]; s+=(signed char)bytes[i+1];
    }
    a=lpm_header_unsigned(bytes+1); b=lpm_header_signed(bytes+1);
    if(a!=u || b!=s) return 1;
  }
#ifdef __linux__
  long page=sysconf(_SC_PAGESIZE);
  unsigned char *guard=mmap(NULL,2*page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if(guard==MAP_FAILED || mprotect(guard+page,page,PROT_NONE)) return 2;
  for(unsigned value=0;value<=255;value+=255) {
    memset(guard+page-512,value,512);
    if(lpm_header_unsigned(guard+page-512)!=(int)value*512) return 3;
    if(lpm_header_signed(guard+page-512)!=(int)(signed char)value*512) return 4;
  }
  munmap(guard,2*page);
#endif
  puts("PASS: 100000 unaligned randomized signed/unsigned checksums and guard-page bounds");
  return 0;
}
