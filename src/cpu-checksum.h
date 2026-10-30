/* LPM tar header checksum dispatch. GPL-3.0-or-later. */
#if defined __x86_64__ && defined __GNUC__
#include <immintrin.h>
__attribute__ ((target ("avx2")))
static void
lpm_sum_avx2 (unsigned char const *p, int *u, int *s)
{
  __m256i sum = _mm256_setzero_si256 ();
  __m256i high = _mm256_setzero_si256 ();
  __m256i zero = _mm256_setzero_si256 ();
  unsigned long long a[4], b[4];
  unsigned i;
  for (i = 0; i < 512; i += 32) {
    __m256i v = _mm256_loadu_si256 ((void const *)(p+i));
    sum = _mm256_add_epi64 (sum, _mm256_sad_epu8 (v, zero));
    high = _mm256_add_epi64 (high, _mm256_sad_epu8 (
      _mm256_and_si256 (_mm256_cmpgt_epi8 (zero, v),
                        _mm256_set1_epi8 (1)), zero));
  }
  _mm256_storeu_si256 ((void *)a, sum);
  _mm256_storeu_si256 ((void *)b, high);
  *u = a[0]+a[1]+a[2]+a[3];
  *s = *u - 256 * (b[0]+b[1]+b[2]+b[3]);
}
#endif
static void
lpm_header_sum (unsigned char const *p, int *u, int *s)
{
  unsigned i;
#if defined __x86_64__ && defined __GNUC__
  /* Header parsing is serialized; cache dispatch outside the hot loop. */
  static int avx2 = -1;
  if (avx2 < 0)
    avx2 = !!__builtin_cpu_supports ("avx2") && !getenv ("LPM_TAR_SCALAR");
  if (avx2) {
    lpm_sum_avx2 (p, u, s);
    return;
  }
#endif
  *u = *s = 0;
  for (i = 0; i < 512; ++i) { *u += p[i]; *s += (signed char)p[i]; }
}
