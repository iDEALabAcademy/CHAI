#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#include "struct.h"
#include "communication_trace_A.h"
#include "communication_trace_B.h"
#ifndef LOCAL_RUN
#include "support/msp430-support.h"
#endif


// extern PacketLog communication_trace_A[];
// extern PacketLog communication_trace_B[];
// extern PacketLog communication_trace_C[];

#define VECTOR_SIZE 100 // assuming a maximum size of the vector

double calculateDeliveryRatio(PacketLog logs[], int size)
{
    /* Knob Variables Declaration Start */
    int perforation_factor = 6;
    int precision_mode = 1;
    double truncation_ratio = 0.7748258590669662;
    /* Knob Variables Declaration End */
    
    // Calculate truncated loop size based on truncation_ratio
    int effective_size = (int)(size * truncation_ratio);
    if (effective_size < 1) effective_size = 1; // Minimum 1 iteration
    
    #if defined(PRECISION_MODE) && PRECISION_MODE == 1
        float total_packets = 0;
        float delivered_weight = 0;
    #else
        double total_packets = 0;
        double delivered_weight = 0;
    #endif
    
    // Apply loop perforation with truncation strategy
    int step = (perforation_factor > 1) ? perforation_factor : 1;
    
    for (int i = 0; i < effective_size; i += step)
    {
        total_packets += 1.0;
        if (logs[i].status == 1)
        {
            delivered_weight += logs[i].weight;
        }
    }
    
    // Scale results to account for skipped packets due to perforation
    if (perforation_factor > 1) {
        total_packets *= perforation_factor;
        delivered_weight *= perforation_factor;
    }
    
    // Scale results to account for truncated portion of array
    if (truncation_ratio < 1.0) {
        double scale_factor = 1.0 / truncation_ratio;
        total_packets *= scale_factor;
        delivered_weight *= scale_factor;
    }
    
    return (delivered_weight / total_packets);
}

void reverseArray(int arr[], int size) {
    int start = 0;
    int end = size - 1;
    while (start < end) {
        // Swap the elements at start and end
        int temp = arr[start];
        arr[start] = arr[end];
        arr[end] = temp;

        // Move the pointers towards the middle
        start++;
        end--;
    }
}

int main()
{
    double sum = 0;

    double delivery_ratio_A = calculateDeliveryRatio(communication_trace_A, VECTOR_SIZE);
   double delivery_ratio_B = calculateDeliveryRatio(communication_trace_B, VECTOR_SIZE);
   double delivery_ratio_C = calculateDeliveryRatio(communication_trace_A, VECTOR_SIZE);
   delivery_ratio_C = calculateDeliveryRatio(communication_trace_A, VECTOR_SIZE);
   delivery_ratio_C = calculateDeliveryRatio(communication_trace_A, VECTOR_SIZE);
   delivery_ratio_C = calculateDeliveryRatio(communication_trace_B, VECTOR_SIZE);
   delivery_ratio_C = calculateDeliveryRatio(communication_trace_A, VECTOR_SIZE);
   delivery_ratio_C = calculateDeliveryRatio(communication_trace_A, VECTOR_SIZE);
   delivery_ratio_C = calculateDeliveryRatio(communication_trace_A, VECTOR_SIZE);

    sum += (delivery_ratio_A * delivery_ratio_A);
   sum += (delivery_ratio_B * delivery_ratio_B);
   sum += (delivery_ratio_C * delivery_ratio_C);

   sum = sum / 3;

    double rmse = sqrt(sum);

#ifdef LOCAL_RUN
    printf("%.4f\n", rmse);
#else
    indicate_end();
#endif

    return 0;
}
