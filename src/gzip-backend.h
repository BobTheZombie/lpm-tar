/* LPM tar pigz integration. GPL-3.0-or-later.
   Try exec in the already-forked filter process: no PATH probing or shell. */
static void
lpm_try_pigz (char const *program, bool decompress)
{
  char count[32];
  char *args[6];
  unsigned threads = lpm_compression_threads_option;
  if (lpm_explicit_filter_option || lpm_gzip_backend_option == 1
      || strcmp (program, GZIP_PROGRAM) != 0)
    return;
  if (!threads)
    {
      char const *env = getenv ("LPM_TAR_THREADS");
      if (env)
        {
          char *end;
          unsigned long n;
          errno = 0;
          n = strtoul (env, &end, 10);
          if (errno || !*env || *end || n < 1 || n > 32)
            FATAL_ERROR ((0, 0, "LPM_TAR_THREADS must be between 1 and 32"));
          threads = n;
        }
      else
        {
          long n = sysconf (_SC_NPROCESSORS_ONLN);
          threads = n < 1 ? 1 : n > 32 ? 32 : n;
        }
    }
  snprintf (count, sizeof count, "%u", threads);
  args[0] = (char *)"pigz";
  args[1] = (char *)"-p";
  args[2] = count;
  args[3] = decompress ? (char *)"-d" : NULL;
  args[4] = NULL;
  execvp (args[0], args);
  /* Never mask permission/format errors or a running filter's failure. */
  if (lpm_gzip_backend_option == 2 || errno != ENOENT)
    exec_fatal ("pigz");
}
