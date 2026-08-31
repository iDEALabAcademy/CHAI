#ifdef LOCAL_RUN
#include <stdio.h>
#endif
#include <stdint.h>
#include <stdlib.h>
#include "image_data.h"

static uint8_t input_buf[MAX_IMAGESIZE * MAX_IMAGESIZE];
static uint8_t output_buf[MAX_IMAGESIZE * MAX_IMAGESIZE];

#ifdef LOCAL_RUN
unsigned char image2[MAX_IMAGESIZE][MAX_IMAGESIZE];
int x_size2, y_size2;
#endif

void sobel(const uint8_t *input, uint8_t *output, int width, int height)
{
  for (int y = 0; y < height; y++) {
    for (int x = 0; x < width; x++) {
      if (x == 0 || x == width - 1 || y == 0 || y == height - 1) {
        output[y * width + x] = 0;
        continue;
      }
      int p00 = input[(y-1)*width + (x-1)];
      int p01 = input[(y-1)*width +  x   ];
      int p02 = input[(y-1)*width + (x+1)];
      int p10 = input[ y   *width + (x-1)];
      int p12 = input[ y   *width + (x+1)];
      int p20 = input[(y+1)*width + (x-1)];
      int p21 = input[(y+1)*width +  x   ];
      int p22 = input[(y+1)*width + (x+1)];
      int gx = -p00 + p02 - 2*p10 + 2*p12 - p20 + p22;
      int gy =  p00 + 2*p01 + p02 - p20 - 2*p21 - p22;
      int mag = abs(gx) + abs(gy);
      if (mag > 255) mag = 255;
      output[y * width + x] = (uint8_t)mag;
    }
  }
}

#ifdef LOCAL_RUN
void save_image_data(void)
{
  char *file_name = "img.pgm";
  FILE *fp;
  int x, y;
  printf("-----------------------------------------------------\n");
  printf("Monochromatic image file output routine\n");
  printf("-----------------------------------------------------\n\n");
  fp = fopen(file_name, "wb");
  fputs("P5\n", fp);
  fputs("# Created by Image Processing\n", fp);
  fprintf(fp, "%d %d\n", x_size2, y_size2);
  fprintf(fp, "%d\n", 255);
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

void sobel_filtering(void)
{
  int x, y;
  for (y = 0; y < y_size1; y++) {
    for (x = 0; x < x_size1; x++) {
      input_buf[y * x_size1 + x] = image1[y][x];
    }
  }

  sobel(input_buf, output_buf, x_size1, y_size1);

#ifdef LOCAL_RUN
  x_size2 = x_size1;
  y_size2 = y_size1;
  for (y = 0; y < y_size2; y++) {
    for (x = 0; x < x_size2; x++) {
      image2[y][x] = output_buf[y * x_size2 + x];
    }
  }
#endif
}

int main(int argc, const char** argv)
{
  sobel_filtering();
#ifdef LOCAL_RUN
  save_image_data();
#endif
#ifndef LOCAL_RUN
  indicate_end();
#endif
  return 0;
}
