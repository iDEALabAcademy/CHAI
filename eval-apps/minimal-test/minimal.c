#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Simple signal processing function for testing
void process_signal(int* signal, int length) {
    int sum = 0;
    for (int i = 0; i < length; i++) {
        sum += signal[i];
    }
    printf("Signal sum: %d\n", sum);
}

// Filter function
void apply_filter(int* data, int size) {
    for (int i = 1; i < size - 1; i++) {
        data[i] = (data[i-1] + data[i] + data[i+1]) / 3;
    }
}

int main() {
    int signal[100];
    for (int i = 0; i < 100; i++) {
        signal[i] = i;
    }
    
    process_signal(signal, 100);
    apply_filter(signal, 100);
    process_signal(signal, 100);
    
    return 0;
}
