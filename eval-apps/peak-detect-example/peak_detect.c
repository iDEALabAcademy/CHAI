#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define ARRAY_SIZE 1024
#define THRESHOLD_BASE 100

/* Global data */
int input_signal[ARRAY_SIZE];
int peak_count = 0;
int peak_indices[100];
int peak_values[100];

/**
 * Find peaks in a signal
 * A peak is defined as a value significantly higher than its neighbors
 * Approximations: Can skip some comparisons or reduce precision
 */
void find_peaks()
{
    int i;
    int threshold;
    int neighborhood_size = 3;
    int skip_factor = 1;
    int sum = 0;
    
    peak_count = 0;
    
    /* Calculate average value as baseline */
    for (i = 0; i < ARRAY_SIZE; i++) {
        sum += input_signal[i];
    }
    int average = sum / ARRAY_SIZE;
    threshold = average + THRESHOLD_BASE;
    
    /* Search for peaks */
    for (i = neighborhood_size; i < ARRAY_SIZE - neighborhood_size; i += skip_factor) {
        int current = input_signal[i];
        
        /* Check if current value is above threshold */
        if (current > threshold) {
            /* Verify it's a local maximum */
            int is_peak = 1;
            int j;
            
            for (j = i - neighborhood_size; j <= i + neighborhood_size; j++) {
                if (j != i && input_signal[j] > current) {
                    is_peak = 0;
                    break;
                }
            }
            
            if (is_peak && peak_count < 100) {
                peak_indices[peak_count] = i;
                peak_values[peak_count] = current;
                peak_count++;
            }
        }
    }
}

/* Initialize test signal with synthetic data */
void init_signal()
{
    int i;
    for (i = 0; i < ARRAY_SIZE; i++) {
        /* Create a signal with some peaks */
        input_signal[i] = 50 + (i % 100) * 2;
        
        /* Add peaks at specific locations */
        if (i == 200 || i == 400 || i == 600 || i == 800) {
            input_signal[i] = 350;  /* Strong peak */
        }
        if (i == 250 || i == 450 || i == 650 || i == 850) {
            input_signal[i] = 280;  /* Medium peak */
        }
    }
}

/* Validate results against baseline */
int validate_peaks()
{
    /* Expected: should find ~8 peaks in the synthetic signal */
    return peak_count >= 6 && peak_count <= 10;
}

/* Print results */
void print_results()
{
    int i;
    printf("Peak Detection Results:\n");
    printf("Found %d peaks\n", peak_count);
    for (i = 0; i < peak_count && i < 10; i++) {
        printf("  Peak %d: index=%d, value=%d\n", i+1, peak_indices[i], peak_values[i]);
    }
}

int main(int argc, char *argv[])
{
    init_signal();
    find_peaks();
    print_results();
    
    if (validate_peaks()) {
        printf("Validation: PASS\n");
        return 0;
    } else {
        printf("Validation: FAIL\n");
        return 1;
    }
}
