#include "Sobel.h"
#include <stdint.h>
#include <stdlib.h>

/*
 * Approximated sobel() with tunable knobs.
 * 
 * Knob variables:
 *   downsample_factor  [1, 4]  — process every nth pixel (1=exact, 4=max approx)
 *   loop_perf_factor   [1, 4]  — skip rows (1=exact, 4=max approx)
 *   early_exit_enabled [0, 1]  — enable early exit
 *   max_iterations     [100, 10000] — max pixels before early exit
 *   quantize_shift     [0, 4]  — right-shift magnitude (0=exact, 4=max approx)
 *
 * Suggested starting point (balanced speed/accuracy):
 *   downsample_factor=2, loop_perf_factor=1,
 *   early_exit_enabled=1, max_iterations=2000, quantize_shift=1
 */
void sobel(const uint8_t *input, uint8_t *output, int width, int height)
{
    /* Knob Variables Declaration Start */
    int downsample_factor  = 2;
    int loop_perf_factor   = 2;
    int early_exit_enabled = 1;
    int max_iterations     = 10000;
    int quantize_shift     = 4;
    /* Knob Variables Declaration End */

    int iteration_count = 0;

    for (int y = 0; y < height; y += loop_perf_factor) {
        for (int x = 0; x < width; x += downsample_factor) {

            /* Border pixels — zero out */
            if (x == 0 || x >= width - 1 || y == 0 || y >= height - 1) {
                /* Fill block with zeros */
                for (int fy = 0; fy < loop_perf_factor && (y + fy) < height; fy++)
                    for (int fx = 0; fx < downsample_factor && (x + fx) < width; fx++)
                        output[(y + fy) * width + (x + fx)] = 0;
                continue;
            }

            /* Sobel convolution at anchor pixel */
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

            /* Quantization approximation */
            if (quantize_shift > 0) {
                mag = (mag >> quantize_shift) << quantize_shift;
                if (mag > 255) mag = 255;
            }

            uint8_t val = (uint8_t)mag;

            /* Fill skipped pixels with anchor value (nearest-neighbor) */
            for (int fy = 0; fy < loop_perf_factor && (y + fy) < height; fy++)
                for (int fx = 0; fx < downsample_factor && (x + fx) < width; fx++)
                    output[(y + fy) * width + (x + fx)] = val;

            /* Early exit */
            iteration_count++;
            if (early_exit_enabled && iteration_count >= max_iterations)
                return;
        }
    }
}