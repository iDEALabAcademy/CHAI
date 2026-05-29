#ifndef PEAK_DETECT_H
#define PEAK_DETECT_H

#define ARRAY_SIZE 1024
#define MAX_PEAKS 100

extern int input_signal[ARRAY_SIZE];
extern int peak_count;
extern int peak_indices[MAX_PEAKS];
extern int peak_values[MAX_PEAKS];

void find_peaks(void);
void init_signal(void);
int validate_peaks(void);
void print_results(void);

#endif
