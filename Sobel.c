#include "Sobel.h"
#include <stdint.h>
#include <stdlib.h>


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
