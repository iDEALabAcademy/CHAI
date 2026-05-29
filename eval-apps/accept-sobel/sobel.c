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
  int downsample_factor = 2;
  int interpolation_mode = 0;
  double perforation_ratio = 0.3731854636087587;
  /* Knob Variables Declaration End */

  /* Definition of Sobel filter in horizontal direction */
  int weight[3][3] = {{ -1,  0,  1 },
                      { -2,  0,  2 },
                      { -1,  0,  1 }};

  double pixel_value;
  double min, max;
  int x, y, i, j;
  int effective_y_end, effective_x_end;

  /* Calculate truncated loop bounds based on perforation ratio */
  effective_y_end = 1 + (int)((y_size1 - 2) * perforation_ratio);
  effective_x_end = 1 + (int)((x_size1 - 2) * perforation_ratio);

  /* PASS 1: Filtering and finding min/max values with spatial downsampling */
  min = DBL_MAX;
  max = -DBL_MAX;

  for (y = 1; y < effective_y_end; y += downsample_factor) {
    for (x = 1; x < effective_x_end; x += downsample_factor) {
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

  if ((int)(max - min) == 0) {
    return;
  }

  /* PASS 2: Normalization and output with spatial downsampling and interpolation */
  x_size2 = x_size1;
  y_size2 = y_size1;

  for (y = 1; y < y_size1 - 1; y++) {
    for (x = 1; x < x_size1 - 1; x++) {
      
      /* Check if this is an anchor point (compute) or fill point (interpolate) */
      if (((y - 1) % downsample_factor == 0) && ((x - 1) % downsample_factor == 0) && 
          (y < effective_y_end) && (x < effective_x_end)) {
        
        /* ANCHOR POINT: Compute full Sobel convolution */
        pixel_value = 0.0;
        for (j = -1; j <= 1; j++) {
          for (i = -1; i <= 1; i++) {
            pixel_value += weight[j + 1][i + 1] * image1[y + j][x + i];
          }
        }
        pixel_value = MAX_BRIGHTNESS * (pixel_value - min) / (max - min);
        image2[y][x] = (unsigned char)pixel_value;
        
      } else {
        /* FILL POINT: Use interpolation based on interpolation_mode */
        if (interpolation_mode == 0) {
          /* Nearest neighbor interpolation */
          int anchor_y = ((y - 1) / downsample_factor) * downsample_factor + 1;
          int anchor_x = ((x - 1) / downsample_factor) * downsample_factor + 1;
          
          /* Ensure anchor point is within computed bounds */
          if (anchor_y >= effective_y_end) anchor_y = effective_y_end - downsample_factor;
          if (anchor_x >= effective_x_end) anchor_x = effective_x_end - downsample_factor;
          if (anchor_y < 1) anchor_y = 1;
          if (anchor_x < 1) anchor_x = 1;
          
          image2[y][x] = image2[anchor_y][anchor_x];
          
        } else {
          /* Linear interpolation */
          int y1 = ((y - 1) / downsample_factor) * downsample_factor + 1;
          int x1 = ((x - 1) / downsample_factor) * downsample_factor + 1;
          int y2 = y1 + downsample_factor;
          int x2 = x1 + downsample_factor;
          
          /* Boundary checks */
          if (y2 >= effective_y_end) y2 = y1;
          if (x2 >= effective_x_end) x2 = x1;
          
          /* Simple bilinear interpolation */
          if (y1 == y2 && x1 == x2) {
            image2[y][x] = image2[y1][x1];
          } else if (y1 == y2) {
            /* Linear interpolation in x direction */
            double weight_x = (double)(x - x1) / (x2 - x1);
            image2[y][x] = (unsigned char)(image2[y1][x1] * (1.0 - weight_x) + 
                                         image2[y1][x2] * weight_x);
          } else if (x1 == x2) {
            /* Linear interpolation in y direction */
            double weight_y = (double)(y - y1) / (y2 - y1);
            image2[y][x] = (unsigned char)(image2[y1][x1] * (1.0 - weight_y) + 
                                         image2[y2][x1] * weight_y);
          } else {
            /* Bilinear interpolation */
            double weight_x = (double)(x - x1) / (x2 - x1);
            double weight_y = (double)(y - y1) / (y2 - y1);
            
            double val = image2[y1][x1] * (1.0 - weight_x) * (1.0 - weight_y) +
                        image2[y1][x2] * weight_x * (1.0 - weight_y) +
                        image2[y2][x1] * (1.0 - weight_x) * weight_y +
                        image2[y2][x2] * weight_x * weight_y;
            
            image2[y][x] = (unsigned char)val;
          }
        }
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
