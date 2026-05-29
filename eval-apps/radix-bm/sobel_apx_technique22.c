/* sobel.c - APPROXIMATION TECHNIQUE #22: SPATIAL DOWNSAMPLING */
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

// output image data
unsigned char image2[MAX_IMAGESIZE][MAX_IMAGESIZE];
int x_size2, y_size2;

#ifdef LOCAL_RUN
void save_image_data( )
/* Output of image2[ ][ ], x_size2, y_size2 in pgm format*/     
{
  char *file_name = "img.pgm";
  FILE *fp; /* File pointer */
  int x, y; /* Loop variable */
  
  /* Output file open */
  printf("-----------------------------------------------------\n");
  printf("Monochromatic image file output routine\n");
  printf("-----------------------------------------------------\n\n");
  fp = fopen(file_name, "wb");
  /* output of pgm file header information */
  fputs("P5\n", fp);
  fputs("# Created by Image Processing\n", fp);
  fprintf(fp, "%d %d\n", x_size2, y_size2);
  fprintf(fp, "%d\n", MAX_BRIGHTNESS);
  /* Output of image data */
  for (y = 0; y < y_size2; y++) {
    for (x = 0; x < x_size2; x++) {
      fputc((image2[y][x]), fp);
    }
  }
  printf("\n-----Image data output OK-----\n\n");
  printf("-----------------------------------------------------\n\n");
  fclose(fp);
}
#endif

void sobel_filtering( )
     /* Spatial filtering of image data */
     /* APPROXIMATION TECHNIQUE #22: SPATIAL DOWNSAMPLING */
     /* Sobel filter (horizontal differentiation) */
     /* Input: image1[y][x] ---- Output: image2[y][x] */
{
  /* ================================================================= */
  /* KNOB VARIABLES DECLARATION START - APPROXIMATION TECHNIQUE #22    */
  /* ================================================================= */
  int downsample_factor = 1;  /* 
    KNOB: Spatial downsampling factor.
    Controls how many pixels are skipped in x and y directions.
    Allowed values: {1, 2, 4}
    Default: 1 (no downsampling, baseline behavior)
    
    Approximation Strategy (Input Fidelity Reduction):
    - downsample_factor = 1: Process ALL pixels (baseline, exact)
    - downsample_factor = 2: Process every 2nd pixel (4x fewer operations)
    - downsample_factor = 4: Process every 4th pixel (16x fewer operations)
    
    Fill Strategy for skipped pixels:
    Uses NEAREST-NEIGHBOR copy from last computed pixel.
    Rationale: 
      - Simple, O(1) per fill, no extra computation
      - Preserves edge connectivity in local neighborhoods
      - Acceptable for image processing (human visual tolerance)
      - Alternative (not used): linear interpolation (more costly)
  */
  /* ================================================================= */
  /* KNOB VARIABLES DECLARATION END                                   */
  /* ================================================================= */

  /* Definition of Sobel filter in horizontal direction */
  int weight[3][3] = {{ -1,  0,  1 },
		      { -2,  0,  2 },
		      { -1,  0,  1 }};
  double pixel_value;
  double min, max;
  int x, y, i, j;  /* Loop variable */
  
  /* Storage for last computed value (for nearest-neighbor fill) */
  unsigned char last_value = 0;

  min = DBL_MAX;
  max = -DBL_MAX;
  
  /* ================================================================= */
  /* PASS 1: DOWNSAMPLED COMPUTATION OF MIN/MAX GRADIENT              */
  /* ================================================================= */
  /* Process only every downsample_factor-th pixel                    */
  for (y = 1; y < y_size1 - 1; y += downsample_factor) {
    for (x = 1; x < x_size1 - 1; x += downsample_factor) {
      pixel_value = 0.0;
      for (j = -1; j <= 1; j++) {
	    for (i = -1; i <= 1; i++) {
	      pixel_value += weight[j + 1][i + 1] * (image1[y + j][x + i]);
	    }
      }
      if (pixel_value < min) min = pixel_value;
      if (pixel_value > max) max = pixel_value;
    }
  }
  
  if ((int)(max - min) == 0) {
    return;
  }

  /* New loop variables */
  int xa;
  int ya;
  /* New pixel_value */
  double pixel_value_app;
  
  /* Initialization of image2[y][x] */
  x_size2 = x_size1;
  y_size2 = y_size1;
  for (ya = 0; (ya < y_size2); ya++) {
    for (xa = 0; (xa < x_size2); xa++) {
      image2[ya][xa] = 0;
    }
  }
  
  /* ================================================================= */
  /* PASS 2: GENERATE OUTPUT WITH FILL STRATEGY                       */
  /* ================================================================= */
  /* Process downsampled pixels, fill others with nearest-neighbor    */
  for (ya = 1; (ya < y_size1 - 1); ya++) {
    for (xa = 1; (xa < x_size1 - 1); xa++) {
      
      /* Check if this pixel is computed or filled */
      if ((ya - 1) % downsample_factor == 0 && (xa - 1) % downsample_factor == 0) {
        /* COMPUTED PIXEL: Full Sobel convolution */
        pixel_value_app = 0.0;
        for (j = -1; j <= 1; j++) {
	      for (i = -1; i <= 1; i++) {
	        pixel_value_app += weight[j + 1][i + 1] * image1[ya + j][xa + i];
	      }
        }
        pixel_value_app = MAX_BRIGHTNESS * (pixel_value_app - min) / (max - min);
        last_value = (unsigned char)pixel_value_app;
        image2[ya][xa] = last_value;
      } else {
        /* SKIPPED PIXEL: Nearest-neighbor fill */
        /* Use last computed value (preserves local coherence) */
        image2[ya][xa] = last_value;
      }
    }
  }
  
  /* ================================================================= */
  /* LOGGING (for debug and validation)                               */
  /* ================================================================= */
  #ifdef LOCAL_RUN
  if (downsample_factor > 1) {
    printf("Applying Approximation #22: Spatial Downsampling\n");
    printf("  downsample_factor = %d\n", downsample_factor);
    printf("  Processed pixels: ~%d (vs %d baseline)\n",
           ((y_size1-2) / downsample_factor) * ((x_size1-2) / downsample_factor),
           (y_size1-2) * (x_size1-2));
  }
  #endif
}

int main(int argc, const char** argv)
{
  sobel_filtering( );

#ifdef LOCAL_RUN
  save_image_data( );
#endif

#ifndef LOCAL_RUN
  indicate_end();
#endif
  return 0;
}
