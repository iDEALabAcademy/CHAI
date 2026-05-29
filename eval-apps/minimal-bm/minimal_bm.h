#ifndef MINIMAL_BM_H
#define MINIMAL_BM_H

void build_bad_char_shift(
    const char *pattern,
    int *shift_table,
    int pattern_len
);

int bm_search(
    const char *text,
    const char *pattern,
    int *matches,
    int max_matches
);

#endif
