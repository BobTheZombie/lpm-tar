/* LPM tar header checksums. GPL-3.0-or-later.
   The assembly reads exactly one 512-byte header, including unaligned input. */
#if defined __x86_64__ && defined __GNUC__ && !defined LPM_TAR_NO_ASM
__attribute__ ((target ("avx2"), noinline))
static int
lpm_unsigned_avx2 (unsigned char const *p)
{
  int sum, loops = 4;
  __asm__ (
    "vpxor %%ymm0, %%ymm0, %%ymm0\n\t"
    "vpxor %%ymm1, %%ymm1, %%ymm1\n\t"
    "vpxor %%ymm2, %%ymm2, %%ymm2\n\t"
    "vpxor %%ymm3, %%ymm3, %%ymm3\n\t"
    "vpxor %%ymm4, %%ymm4, %%ymm4\n\t"
    "1:\n\t"
    "vpsadbw 0(%[p]), %%ymm0, %%ymm5\n\t"
    "vpaddq %%ymm5, %%ymm1, %%ymm1\n\t"
    "vpsadbw 32(%[p]), %%ymm0, %%ymm5\n\t"
    "vpaddq %%ymm5, %%ymm2, %%ymm2\n\t"
    "vpsadbw 64(%[p]), %%ymm0, %%ymm5\n\t"
    "vpaddq %%ymm5, %%ymm3, %%ymm3\n\t"
    "vpsadbw 96(%[p]), %%ymm0, %%ymm5\n\t"
    "vpaddq %%ymm5, %%ymm4, %%ymm4\n\t"
    "add $128, %[p]\n\t"
    "dec %[loops]\n\t"
    "jnz 1b\n\t"
    "vpaddq %%ymm2, %%ymm1, %%ymm1\n\t"
    "vpaddq %%ymm4, %%ymm3, %%ymm3\n\t"
    "vpaddq %%ymm3, %%ymm1, %%ymm1\n\t"
    "vextracti128 $1, %%ymm1, %%xmm2\n\t"
    "vpaddq %%xmm2, %%xmm1, %%xmm1\n\t"
    "vpsrldq $8, %%xmm1, %%xmm2\n\t"
    "vpaddq %%xmm2, %%xmm1, %%xmm1\n\t"
    "vmovd %%xmm1, %[sum]\n\t"
    "vzeroupper"
    : [sum] "=r" (sum), [p] "+r" (p), [loops] "+r" (loops)
    : : "ymm0", "ymm1", "ymm2", "ymm3", "ymm4", "ymm5", "cc", "memory");
  return sum;
}
#endif
static int
lpm_header_unsigned (unsigned char const *p)
{
  unsigned i;
  int sum = 0;
#if defined __x86_64__ && defined __GNUC__ && !defined LPM_TAR_NO_ASM
  /* Only the serialized archive parser calls this dispatch function. */
  static int avx2 = -1;
  if (avx2 < 0)
    avx2 = !!__builtin_cpu_supports ("avx2") && !getenv ("LPM_TAR_SCALAR");
  if (avx2) return lpm_unsigned_avx2 (p);
#endif
  for (i = 0; i < 512; ++i) sum += p[i];
  return sum;
}
static int
lpm_header_signed (unsigned char const *p)
{
  unsigned i;
  int sum = 0;
  for (i = 0; i < 512; ++i) sum += (signed char)p[i];
  return sum;
}
