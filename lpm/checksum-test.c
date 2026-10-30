/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
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
    lpm_header_sum(bytes+1,&a,&b);
    if(a!=u || b!=s) return 1;
  }
  puts("PASS: 100000 unaligned randomized signed/unsigned checksums");
  return 0;
}
