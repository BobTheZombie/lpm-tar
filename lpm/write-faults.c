/* SPDX-License-Identifier: GPL-3.0-or-later
   Test-only interposer: short writes, EINTR, and ENOSPC. */
#define _GNU_SOURCE
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>
#include <dlfcn.h>
ssize_t pwrite(int fd,const void *data,size_t size,off_t offset) {
  static _Thread_local unsigned calls;
  ssize_t (*real_write)(int,const void*,size_t,off_t)=dlsym(RTLD_NEXT,"pwrite");
  if(getenv("LPM_TEST_ENOSPC")) {errno=ENOSPC;return -1;}
  if((++calls % 7)==1) {errno=EINTR;return -1;}
  if(size>4096) size=4096;
  return real_write(fd,data,size,offset);
}
