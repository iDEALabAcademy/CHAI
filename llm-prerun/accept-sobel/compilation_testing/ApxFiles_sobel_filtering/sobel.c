/*
 * Sobel edge detection filter
 * Original source: https://github.com/uwsampa/accept-apps/blob/master/sobel/sobel.c
 * Adapted for CheckMate: ACCEPT annotations (APPROX, ENDORSE, enerc.h) removed
 */

#ifdef LOCAL_RUN
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#endif

#include <float.h>

#include "image_data.h"

/* Constant declaration */
#define MAX_BRIGHTNESS  255 /* Maximum gray level */
#define GRAYLEVEL       256 /* No. of gray levels */
#define MAX_FILENAME    256 /* Filename length limit */
#define MAX_BUFFERSIZE  256

/* Output image data */
unsigned char image2[MAX_IMAGESIZE][MAX_IMAGESIZE];
int x_size2, y_size2;

#ifdef LOCAL_RUN
void save_image_data(void)
/* Output of image2[][] in pgm format */
{
  char *file_name = "img.pgm";
  FILE *fp;
  int x, y;

  fp = fopen(file_name, "wb");
  fputs("P5\n", fp);
  fputs("# Created by Image Processing\n", fp);
  fprintf(fp, "%d %d\n", x_size2, y_size2);
  fprintf(fp, "%d\n", MAX_BRIGHTNESS);
  for (y = 0; y < y_size2; y++) {
    for (x = 0; x < x_size2; x++) {
      fputc((image2[y][x]), fp);
    }
  }
  fclose(fp);
}
#endif

void sobel_filtering(void)
/* Sobel filter (horizontal differentiation)
 * Input: image1[y][x] -> Output: image2[y][x]
 * ACCEPT algorithm: two-pass approach with min/max normalization
 */
{
  /* Knob Variables Declaration Start */
  int perforation_factor = 100;  // Percentage of iterations to keep (100 = baseline)
  int use_integer_math = 0;      // 0 = double precision (baseline), 1 = integer math
  int scale_factor = 256;        // Fixed-point scaling for integer math
  /* Knob Variables Declaration End */

  /* Definition of Sobel filter in horizontal direction */
  int weight[3][3] = {{ -1,  0,  1 },
                      { -2,  0,  2 },
                      { -1,  0,  1 }};

  double pixel_value;
  double min, max;
  int x, y, i, j;
  
  // Integer math variables (used when use_integer_math = 1)
  int int_pixel_value;
  int int_min, int_max;
  
  // Calculate iteration limits based on perforation
  int y_limit = 1 + ((y_size1 - 2) * perforation_factor) / 100;
  int x_limit = 1 + ((x_size1 - 2) * perforation_factor) / 100;

  /* PASS 1: Filtering and finding min/max values */
  if (use_integer_math == 0) {
    // Original double precision path
    min = DBL_MAX;
    max = -DBL_MAX;

    for (y = 1; y < y_limit; y++) {  // Loop perforation applied
      for (x = 1; x < x_limit; x++) {  // Loop perforation applied
        pixel_value = 0.0;
        for (j = -1; j <= 1; j++) {
          for (i = -1; i <= 1; i++) {
            pixel_value += weight[j + 1][i + 1] * image1[y + j][x + i];
          }
        }
        if (pixel_value < min) min = pixel_value;
        if (pixel_value > max) max = pixel_value;
      }
    }
  } else {
    // Integer precision path (precision scaling)
    int_min = INT_MAX;
    int_max = INT_MIN;

    for (y = 1; y < y_limit; y++) {  // Loop perforation applied
      for (x = 1; x < x_limit; x++) {  // Loop perforation applied
        int_pixel_value = 0;
        for (j = -1; j <= 1; j++) {
          for (i = -1; i <= 1; i++) {
            int_pixel_value += weight[j + 1][i + 1] * (int)image1[y + j][x + i];
          }
        }
        if (int_pixel_value < int_min) int_min = int_pixel_value;
        if (int_pixel_value > int_max) int_max = int_pixel_value;
      }
    }
    
    // Convert back to double for compatibility with pass 2
    min = (double)int_min;
    max = (double)int_max;
  }

  if ((int)(max - min) == 0) {
    return;
  }

  /* PASS 2: Normalization and output */
  x_size2 = x_size1;
  y_size2 = y_size1;

  if (use_integer_math == 0) {
    // Original double precision path
    for (y = 1; y < y_limit; y++) {  // Loop perforation applied
      for (x = 1; x < x_limit; x++) {  // Loop perforation applied
        pixel_value = 0.0;
        for (j = -1; j <= 1; j++) {
          for (i = -1; i <= 1; i++) {
            pixel_value += weight[j + 1][i + 1] * image1[y + j][x + i];
          }
        }
        pixel_value = MAX_BRIGHTNESS * (pixel_value - min) / (max - min);
        image2[y][x] = (unsigned char)pixel_value;
      }
    }
  } else {
    // Integer precision path (precision scaling)
    int range = (int)(max - min);
    for (y = 1; y < y_limit; y++) {  // Loop perforation applied
      for (x = 1; x < x_limit; x++) {  // Loop perforation applied
        int_pixel_value = 0;
        for (j = -1; j <= 1; j++) {
          for (i = -1; i <= 1; i++) {
            int_pixel_value += weight[j + 1][i + 1] * (int)image1[y + j][x + i];
          }
        }
        // Integer-based normalization
        int normalized = (MAX_BRIGHTNESS * (int_pixel_value - (int)min)) / range;
        image2[y][x] = (unsigned char)normalized;
      }
    }
  }
  
  // Fill remaining pixels with boundary values for perforated regions
  if (perforation_factor < 100) {
    for (y = y_limit; y < y_size1 - 1; y++) {
      for (x = 1; x < x_size1 - 1; x++) {
        image2[y][x] = (y_limit > 1) ? image2[y_limit - 1][x] : 0;
      }
    }
    for (y = 1; y < y_limit; y++) {
      for (x = x_limit; x < x_size1 - 1; x++) {
        image2[y][x] = (x_limit > 1) ? image2[y][x_limit - 1] : 0;
      }
    }
  }
}

int main(void)
{
  /* Image dimensions are set by image_data.h */
  sobel_filtering();

#ifdef LOCAL_RUN
  save_image_data();
#endif

#ifndef LOCAL_RUN
  indicate_end();
#endif
  return 0;
}
