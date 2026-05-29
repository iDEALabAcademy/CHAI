#include <stdio.h>
#include <string.h>

/* Boyer-Moore string search function for testing */

/* Simple bad-character table builder */
void build_bad_char_shift(
    const char *pattern,
    int *shift_table,
    int pattern_len
) {
    int i;
    
    /* Initialize all chars to pattern_len */
    for (i = 0; i < 256; i++) {
        shift_table[i] = pattern_len;
    }
    
    /* Set actual distances for pattern chars */
    for (i = 0; i < pattern_len; i++) {
        unsigned char ch = (unsigned char)pattern[i];
        shift_table[ch] = pattern_len - i - 1;
    }
}

/* Boyer-Moore search */
int bm_search(
    const char *text,
    const char *pattern,
    int *matches,
    int max_matches
) {
    int text_len = strlen(text);
    int pattern_len = strlen(pattern);
    int shift_table[256];
    int match_count = 0;
    int i, j, shift;
    
    if (pattern_len == 0 || pattern_len > text_len) {
        return 0;
    }
    
    /* Build preprocessing table */
    build_bad_char_shift(pattern, shift_table, pattern_len);
    
    /* Search */
    i = pattern_len - 1;
    while (i < text_len && match_count < max_matches) {
        j = pattern_len - 1;
        
        /* Match from right to left */
        while (j >= 0 && text[i] == pattern[j]) {
            i--;
            j--;
        }
        
        if (j < 0) {
            /* Match found */
            matches[match_count++] = i + 1;
            i += pattern_len + 1;
        } else {
            /* Mismatch: use bad-character shift */
            unsigned char ch = (unsigned char)text[i];
            shift = shift_table[ch];
            shift = (shift > j + 1) ? shift : (j + 1);
            i += shift;
        }
    }
    
    return match_count;
}

int main() {
    /* Test text: short but sufficient for compression testing */
    const char *test_text = "the quick brown fox jumps over the lazy dog. "
                           "the fox is quick and the dog is lazy. "
                           "quick brown foxes are known to jump. "
                           "the fox jumps and the dog runs.";
    
    /* Test patterns */
    const char *patterns[] = {"the", "fox", "quick", "dog", "xyz"};
    int num_patterns = 5;
    int i;
    int matches[100];
    int match_count;
    
    printf("Boyer-Moore String Search Test\n");
    printf("Text: %s\n", test_text);
    printf("\nSearching for patterns:\n");
    
    for (i = 0; i < num_patterns; i++) {
        match_count = bm_search(test_text, patterns[i], matches, 100);
        printf("  Pattern '%s': %d matches\n", patterns[i], match_count);
    }
    
    return 0;
}
