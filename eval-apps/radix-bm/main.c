/*
 * radix-bm: Minimal benchmark for Radix Variation (Technique #29)
 *
 * Converts integers to decimal strings using repeated % 10 / / 10 digit
 * extraction, then computes a simple hash of the string representation.
 * This is a proxy for debug-signature formatting, histogram bucket labeling,
 * or log output on batteryless devices.
 *
 * Output: one line per iteration with the hash value (integer).
 *         Ground truth is generated with baseline (radix_mode=10).
 *
 * Target function for approximation: int_to_str()
 *   - Contains expensive / 10 and % 10 operations (~150 cycles each on MSP430)
 *   - Radix variation replaces these with bit shifts when radix_mode != 10
 */

#ifdef LOCAL_RUN
#include <stdio.h>
#else
#include "support/msp430-support.h"
#endif

#include <stdint.h>

/* ------ Parameters ------ */
#define SEED  7L
#define ITER  100
#define NUM_FUNCS 100

/* ------ Functions ------ */

/*
 * int_to_str: Convert unsigned integer to string representation.
 *
 * Uses repeated division by 10 to extract digits (LSB first),
 * then reverses into output buffer.
 *
 * This function is the TARGET for Radix Variation approximation.
 * The / 10 and % 10 operations are expensive on MSP430 (no HW divider).
 */
void int_to_str(unsigned int value, char *buf, int buf_size) {
  /* Knob Variables Declaration Start */
  int radix_mode = 5;
  int max_digits = 5;
  int skip_leading_zeros = 0;
  /* Knob Variables Declaration End */

  char tmp[12];
  int pos = 0;
  int digits_extracted = 0;

  if (value == 0) {
    buf[0] = '0';
    buf[1] = '\0';
    return;
  }

  /* Radix-dependent digit extraction */
  while (value > 0 && pos < 11 && digits_extracted < max_digits) {
    unsigned int digit;
    if (radix_mode == 16) {
      digit = value & 0xF;    /* mask: 1 cycle on MSP430 */
      value = value >> 4;     /* shift: 1 cycle */
    } else if (radix_mode == 8) {
      digit = value & 0x7;
      value = value >> 3;
    } else if (radix_mode == 2) {
      digit = value & 0x1;
      value = value >> 1;
    } else {
      /* radix_mode == 10: baseline exact */
      digit = value % 10;    /* SW division: ~150 cycles on MSP430 */
      value = value / 10;
    }

    if (digit < 10)
      tmp[pos] = '0' + digit;
    else
      tmp[pos] = 'a' + (digit - 10);  /* hex digits a-f */

    pos++;
    digits_extracted++;
  }

  /* Reverse into output buffer */
  int start = 0;
  if (skip_leading_zeros) {
    while (start < pos - 1 && tmp[pos - 1 - start] == '0')
      start++;
  }

  int out_pos = 0;
  for (int i = pos - 1 - start; i >= 0 && out_pos < buf_size - 1; i--) {
    buf[out_pos++] = tmp[i];
  }
  buf[out_pos] = '\0';
}

/*
 * simple_hash: Compute a simple hash of a null-terminated string.
 *
 * Uses djb2-variant: hash = hash * 33 + c
 * This is NOT a target for approximation — it just consumes the
 * string output to produce a measurable result.
 */
unsigned int simple_hash(const char *str) {
    unsigned int hash = 5381;
    int c;
    while ((c = *str++)) {
        hash = ((hash << 5) + hash) + c;  /* hash * 33 + c */
    }
    return hash & 0xFFFF;  /* 16-bit hash for small output */
}

void main() {
    unsigned int total_hash = 0;
    uint32_t seed;
    char buf[16];

#ifndef LOCAL_RUN
    indicate_begin();
#endif

    seed = (uint32_t)SEED;

    for (unsigned int func = 0; func < NUM_FUNCS; func++) {
        for (unsigned int iter = 0; iter < ITER; iter++, seed += 13) {
            int_to_str((unsigned int)(seed & 0xFFFF), buf, 16);
            total_hash += simple_hash(buf);
        }
    }

#ifdef LOCAL_RUN
    printf("%u\n", total_hash);
#else
    indicate_end();
#endif
}
