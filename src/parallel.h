/* LPM tar parallel regular-file writer. GPL-3.0-or-later. */
#include <pthread.h>
#define LPM_CHUNK (1024 * 1024)
#define LPM_MAX_THREADS 32
struct lpm_slot {
  pthread_t thread;
  int fd, error;
  off_t offset;
  size_t used;
  bool active, stop, started;
  pthread_mutex_t lock;
  pthread_cond_t changed;
  char *data;
};
struct lpm_writer {
  struct lpm_slot slots[LPM_MAX_THREADS];
  unsigned threads, next;
  off_t offset;
};
static unsigned
lpm_threads (void)
{
  char const *s = getenv ("LPM_TAR_THREADS");
  char *end;
  unsigned long n;
  if (!s) return 1;
  errno = 0;
  n = strtoul (s, &end, 10);
  if (errno || !*s || *end || n < 1 || n > LPM_MAX_THREADS)
    FATAL_ERROR ((0, 0, "LPM_TAR_THREADS must be between 1 and 32"));
  return n;
}
static void *
lpm_write_chunk (void *arg)
{
  struct lpm_slot *s = arg;
  size_t done = 0;
  while (done < s->used) {
    ssize_t n = pwrite (s->fd, s->data + done, s->used - done,
                        s->offset + done);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) { s->error = n < 0 ? errno : EIO; break; }
    done += n;
  }
  return NULL;
}
static void *
lpm_worker (void *arg)
{
  struct lpm_slot *s = arg;
  pthread_mutex_lock (&s->lock);
  for (;;) {
    while (!s->active && !s->stop)
      pthread_cond_wait (&s->changed, &s->lock);
    if (s->stop) break;
    pthread_mutex_unlock (&s->lock);
    lpm_write_chunk (s);
    pthread_mutex_lock (&s->lock);
    s->active = false;
    pthread_cond_signal (&s->changed);
  }
  pthread_mutex_unlock (&s->lock);
  return NULL;
}
static void
lpm_join (struct lpm_slot *s)
{
  if (!s->started) return;
  pthread_mutex_lock (&s->lock);
  while (s->active) pthread_cond_wait (&s->changed, &s->lock);
  pthread_mutex_unlock (&s->lock);
}
static void
lpm_dispatch (struct lpm_writer *w, struct lpm_slot *s)
{
  s->offset = w->offset;
  w->offset += s->used;
  if (s->started) {
    pthread_mutex_lock (&s->lock);
    s->active = true;
    pthread_cond_signal (&s->changed);
    pthread_mutex_unlock (&s->lock);
  } else lpm_write_chunk (s);
  w->next = (w->next + 1) % w->threads;
}
static void
lpm_submit (struct lpm_writer *w, char const *data, size_t length)
{
  while (length) {
    struct lpm_slot *s = &w->slots[w->next];
    size_t n;
    if (s->used == LPM_CHUNK) { lpm_join (s); s->used = 0; }
    n = LPM_CHUNK - s->used;
    if (n > length) n = length;
    memcpy (s->data + s->used, data, n);
    s->used += n; data += n; length -= n;
    if (s->used == LPM_CHUNK) {
      lpm_dispatch (w, s);

    }
  }
}
static int
lpm_finish (struct lpm_writer *w)
{
  unsigned i;
  int error = 0;
  struct lpm_slot *s = &w->slots[w->next];
  if (s->used && s->used < LPM_CHUNK) lpm_dispatch (w, s);
  for (i = 0; i < w->threads; ++i) {
    lpm_join (&w->slots[i]);
    s = &w->slots[i];
    if (s->started) {
      pthread_mutex_lock (&s->lock);
      s->stop = true;
      pthread_cond_signal (&s->changed);
      pthread_mutex_unlock (&s->lock);
      if (pthread_join (s->thread, NULL)) abort ();
    }
    pthread_cond_destroy (&s->changed);
    pthread_mutex_destroy (&s->lock);
    if (s->error) error = s->error;
    free (w->slots[i].data);
  }
  return error;
}
