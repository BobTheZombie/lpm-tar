/* SPDX-License-Identifier: GPL-3.0-or-later
   Build with -DLPM_PREVIOUS_HEADER='"/path/to/previous/cpu-checksum.h"'
   to compare the v1 dual-reduction implementation as well. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include "../src/cpu-checksum.h"
#ifdef LPM_PREVIOUS_HEADER
#include LPM_PREVIOUS_HEADER
__attribute__((noinline)) static int previous(unsigned char const *p) {
  int u,s; lpm_header_sum(p,&u,&s); return u;
}
#endif
__attribute__((noinline)) static int portable(unsigned char const *p) {
  int u=0;for(unsigned i=0;i<512;++i)u+=p[i];return u;
}
static double now(void) {
  struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);
  return ts.tv_sec+ts.tv_nsec/1e9;
}
static void measure(char const *name,int (*fn)(unsigned char const *),unsigned char *data) {
  volatile unsigned sink=0;double start=now();unsigned count=10000000;
  for(unsigned i=0;i<count;++i)sink+=(unsigned)fn(data+(i%4096)*512+1);
  double elapsed=now()-start;
  printf("%s %.9f seconds %.3f ns/header (sink %u)\n",name,elapsed,elapsed*1e9/count,sink);
}
int main(void) {
  unsigned char *data=malloc(4096*512+1);uint32_t seed=7;
  if(!data)return 2;
  for(unsigned i=0;i<4096*512+1;++i){seed=seed*1664525+1013904223;data[i]=seed>>24;}
#ifdef LPM_PREVIOUS_HEADER
  measure("previous-dual-simd",previous,data);
#endif
  measure("portable-unsigned",portable,data);
  measure("dispatched-unsigned-asm",lpm_header_unsigned,data);
  free(data);return 0;
}
