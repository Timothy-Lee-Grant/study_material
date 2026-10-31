/*
 * 020_dedupe_list.c - lecture 020.
 * Remove every node whose value already appeared earlier in an unsorted singly linked list,
 * in C, with manual memory management, using a hash set we write ourselves (separate chaining,
 * grows when the load factor would pass 0.75).
 *
 * Build and check for leaks / bad frees:
 *   gcc -std=c11 -Wall -Wextra -g -fsanitize=address,undefined 020_dedupe_list.c -o dedupe && ./dedupe
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

/* ------------------------------------------------------------ the list */
typedef struct Node {
    int val;
    struct Node *next;
} Node;

static Node *push_back(Node **head, Node **tail, int val) {
    Node *n = malloc(sizeof *n);
    if (!n) { perror("malloc"); exit(1); }
    n->val = val; n->next = NULL;
    if (*tail) (*tail)->next = n; else *head = n;
    *tail = n;
    return n;
}

static void free_list(Node *head) {
    while (head) {
        Node *next = head->next;   /* read next BEFORE freeing: after free, head->next is gone */
        free(head);
        head = next;
    }
}

/* ------------------------------------------------------------ the hash set (separate chaining) */
typedef struct Entry {
    int key;
    struct Entry *next;            /* next entry in the same bucket (the "chain") */
} Entry;

typedef struct {
    Entry **buckets;               /* array of nbuckets chain heads */
    size_t nbuckets;               /* always a power of two, so "% nbuckets" is "& (nbuckets-1)" */
    size_t count;                  /* number of keys stored */
    size_t probes;                 /* statistics: entries compared during lookups */
    size_t resizes;
} HashSet;

static size_t hash_int(int key) {
    /* Mix the bits so keys like 0, 16, 32, ... don't all land in bucket 0
       (a multiplicative hash: multiply by a large odd constant, keep the high bits). */
    uint64_t x = (uint32_t)key;
    x *= 0x9E3779B97F4A7C15ull;
    return (size_t)(x >> 32);
}

static void set_init(HashSet *s, size_t nbuckets) {
    s->buckets = calloc(nbuckets, sizeof *s->buckets);
    if (!s->buckets) { perror("calloc"); exit(1); }
    s->nbuckets = nbuckets; s->count = 0; s->probes = 0; s->resizes = 0;
}

static int set_contains(HashSet *s, int key) {
    for (Entry *e = s->buckets[hash_int(key) & (s->nbuckets - 1)]; e; e = e->next) {
        s->probes++;
        if (e->key == key) return 1;
    }
    return 0;
}

static void set_grow(HashSet *s) {
    /* Double the bucket array and move every entry to its new bucket: O(n) for this one call,
       but it happens only after the count doubles, so the average cost per insert stays O(1). */
    size_t newn = s->nbuckets * 2;
    Entry **nb = calloc(newn, sizeof *nb);
    if (!nb) { perror("calloc"); exit(1); }
    for (size_t i = 0; i < s->nbuckets; i++) {
        Entry *e = s->buckets[i];
        while (e) {
            Entry *next = e->next;                 /* save before relinking */
            size_t j = hash_int(e->key) & (newn - 1);
            e->next = nb[j]; nb[j] = e;            /* move the entry, don't copy it */
            e = next;
        }
    }
    free(s->buckets);
    s->buckets = nb; s->nbuckets = newn; s->resizes++;
}

static void set_add(HashSet *s, int key) {         /* caller has checked it isn't present */
    if ((s->count + 1) * 4 > s->nbuckets * 3)      /* load factor would pass 0.75 -> grow first */
        set_grow(s);
    Entry *e = malloc(sizeof *e);
    if (!e) { perror("malloc"); exit(1); }
    size_t i = hash_int(key) & (s->nbuckets - 1);
    e->key = key; e->next = s->buckets[i]; s->buckets[i] = e;
    s->count++;
}

static void set_free(HashSet *s) {
    for (size_t i = 0; i < s->nbuckets; i++) {
        Entry *e = s->buckets[i];
        while (e) { Entry *next = e->next; free(e); e = next; }
    }
    free(s->buckets);
    s->buckets = NULL;
}

/* ------------------------------------------------------------ the problem */
/* Keeps the first occurrence of each value, frees every later one. Returns the (unchanged) head:
   the first node is always a first occurrence, so the head never changes. */
static Node *remove_later_duplicates(Node *head, HashSet *seen) {
    Node *prev = NULL;      /* last node we KEPT (NULL before the first node) */
    Node *cur = head;       /* node being examined */
    while (cur) {
        if (set_contains(seen, cur->val)) {
            /* duplicate: unlink it, remember what comes after it, then free it */
            Node *next = cur->next;   /* 1. save the rest of the list */
            prev->next = next;        /* 2. bypass cur (prev is not NULL: the first node is never a duplicate) */
            free(cur);                /* 3. now nothing points at cur, so freeing it is safe */
            cur = next;               /* 4. move on WITHOUT moving prev: prev is still the last kept node */
        } else {
            set_add(seen, cur->val);
            prev = cur;
            cur = cur->next;
        }
    }
    return head;
}

/* ------------------------------------------------------------ tests */
static int check(const int *in, size_t n, const int *want, size_t wn, const char *name) {
    Node *head = NULL, *tail = NULL;
    for (size_t i = 0; i < n; i++) push_back(&head, &tail, in[i]);
    HashSet seen; set_init(&seen, 8);
    head = remove_later_duplicates(head, &seen);
    size_t i = 0; int ok = 1;
    for (Node *p = head; p; p = p->next, i++)
        if (i >= wn || p->val != want[i]) ok = 0;
    if (i != wn) ok = 0;
    printf("%-28s %s\n", name, ok ? "ok" : "FAILED");
    set_free(&seen);
    free_list(head);
    return ok;
}

int main(void) {
    int ok = 1;
    { int in[] = {1, 2, 1, 3, 2, 4};  int w[] = {1, 2, 3, 4};  ok &= check(in, 6, w, 4, "mixed"); }
    { int in[] = {5, 5, 5, 5};        int w[] = {5};           ok &= check(in, 4, w, 1, "all the same"); }
    { int in[] = {1, 2, 3};           int w[] = {1, 2, 3};     ok &= check(in, 3, w, 3, "no duplicates"); }
    { int in[] = {7, 8, 8};           int w[] = {7, 8};        ok &= check(in, 3, w, 2, "duplicate at the tail"); }
    { int w[] = {0};                                           ok &= check(NULL, 0, w, 0, "empty list"); }

    /* Big run: 100,000 values from 0..9,999 -> 10,000 distinct kept. Shows the set's statistics. */
    Node *head = NULL, *tail = NULL;
    srand(1);
    size_t n = 100000;
    for (size_t i = 0; i < n; i++) push_back(&head, &tail, rand() % 10000);
    HashSet seen; set_init(&seen, 8);
    head = remove_later_duplicates(head, &seen);
    size_t kept = 0; for (Node *p = head; p; p = p->next) kept++;
    printf("big: kept %zu distinct, buckets %zu, load %.2f, resizes %zu, avg entries compared per lookup %.2f\n",
           kept, seen.nbuckets, (double)seen.count / seen.nbuckets, seen.resizes, (double)seen.probes / n);
    set_free(&seen); free_list(head);
    return ok ? 0 : 1;
}
