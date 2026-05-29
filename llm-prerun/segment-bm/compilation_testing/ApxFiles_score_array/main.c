/*
 * segment-bm — Pattern Segmentation benchmark for CheckMate
 *
 * A loop over a slowly-varying / piecewise-constant input array,
 * applying a weighted convolution-like scoring + thresholding on
 * each element.  Adjacent elements are deliberately correlated so
 * that segmented reuse is a valid approximation.
 *
 * Target function for approximation: score_array()
 *   - Original: computes a weighted score for every element.
 *   - Approximated: computes only at representative indices per
 *     segment and fills the rest (Pattern Segmentation, Technique #30).
 *
 * Output: single unsigned hash of the output buffer, printed to stdout.
 */

#include <stdio.h>
#include <stdlib.h>

#ifndef LOCAL_RUN
#include "support/msp430-support.h"
#endif

#define ARRAY_LEN 64
#define NUM_ROUNDS 50

/* ---- score_array: TARGET FUNCTION for approximation ---- */
void score_array(const int *input, int *output, int n) {
  for (int i = 0; i < n; i++) {
    int val = input[i];
    int score = 0;
    /* Weighted convolution-like scoring with neighbors */
    if (i > 0) score += (input[i-1] * 3) >> 2;
    score += (val * 5) >> 2;
    if (i < n - 1) score += (input[i+1] * 3) >> 2;
    /* Thresholding */
    if (score < 0) score = 0;
    if (score > 1000) score = 1000;
    output[i] = score;
  }
}

/* ---- simple djb2-style hash over int array ---- */
static unsigned int hash_array(const int *arr, int n) {
  unsigned int h = 5381;
  for (int i = 0; i < n; i++) {
    h = ((h << 5) + h) + (unsigned int)arr[i];
  }
  return h;
}

/* ---- deterministic slowly-varying input generator ---- */
static void generate_input(int *buf, int n, unsigned int seed) {
  /* Piecewise-constant with small noise — ideal for segmentation */
  int base = (int)(seed % 200);
  for (int i = 0; i < n; i++) {
    /* Change base every ~8 elements */
    if (i > 0 && (i % 8) == 0) {
      seed = seed * 1103515245u + 12345u;
      base = (int)((seed >> 16) % 200);
    }
    /* Small noise: ±3 around base */
    seed = seed * 1103515245u + 12345u;
    int noise = (int)((seed >> 16) % 7) - 3;
    buf[i] = base + noise;
  }
}

#ifdef LOCAL_RUN
int main() {
#else
void main() {
#endif
  int input[ARRAY_LEN];
  int output[ARRAY_LEN];
  unsigned int total_hash = 0;

  for (int r = 0; r < NUM_ROUNDS; r++) {
    generate_input(input, ARRAY_LEN, (unsigned int)(r * 17 + 7));
    score_array(input, output, ARRAY_LEN);
    total_hash ^= hash_array(output, ARRAY_LEN);
  }

#ifdef LOCAL_RUN
  printf("%u\n", total_hash);
  return 0;
#else
  indicate_end();
#endif
}
