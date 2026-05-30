

/* CHAI Sobel Function */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Sobel Function */
void sobel(uint8_t *input, uint8_t *output, int width, int height) {
   /* Knob Variables Declaration Start */
   int quantize_enabled; // Enable or disable quantization (0 or 1)= 0;
   int shift_bits;       // Number of bits to shift for quantization= 0;
   float truncation_factor; // Factor to truncate the loop iterations (0.0 to 1.0)= 0.9994025759272094;
   /* Knob Variables Declaration End */
      memset(output, 0, width * height);
   /* Initialize Knob Variables */
   quantize_enabled = 1; // Enable quantization by default
   shift_bits = 2;       // Default shift for 4-bit quantization
   truncation_factor = 0.8; // Default truncation factor (80% of iterations)


   int truncated_height = (int)(height * truncation_factor);
   int truncated_width = (int)(width * truncation_factor);


   for (int y = 1; y < truncated_height - 1; y++) {
       for (int x = 1; x < truncated_width - 1; x++) {
           int gx = 0, gy = 0;


           // Sobel Gx kernel
           gx += input[(y - 1) * width + (x - 1)] * -1;
           gx += input[(y - 1) * width + (x + 1)] * 1;
           gx += input[y * width + (x - 1)] * -2;
           gx += input[y * width + (x + 1)] * 2;
           gx += input[(y + 1) * width + (x - 1)] * -1;
           gx += input[(y + 1) * width + (x + 1)] * 1;


           // Sobel Gy kernel
           gy += input[(y - 1) * width + (x - 1)] * -1;
           gy += input[(y - 1) * width + x] * -2;
           gy += input[(y - 1) * width + (x + 1)] * -1;
           gy += input[(y + 1) * width + (x - 1)] * 1;
           gy += input[(y + 1) * width + x] * 2;
           gy += input[(y + 1) * width + (x + 1)] * 1;


           // Compute gradient magnitude
           int magnitude = abs(gx) + abs(gy);


           // Apply quantization if enabled
           if (quantize_enabled) {
               magnitude = magnitude >> shift_bits; // Right-shift for quantization
           }


           // Clamp the result to 8-bit range
           if (magnitude > 255) magnitude = 255;
           if (magnitude < 0) magnitude = 0;


           // Write the result to the output image
           output[y * width + x] = (uint8_t)magnitude;
       }
   }
}

