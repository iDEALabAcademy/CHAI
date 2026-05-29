"""
Original vs Approximated Sobel — clean comparison figure.
(c) has a red-bordered pixel value inset showing uniform block values.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.ndimage import convolve
from matplotlib.patches import ConnectionPatch, Rectangle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# ── Load bird image ──────────────────────────────────────────────
img = Image.open('/home/nsola5/CheckMate/config/26.gif').convert('L')
gray = np.array(img, dtype=np.float64)  # 512x512
h, w = gray.shape

# ── Sobel kernel ─────────────────────────────────────────────────
sobel_h = np.array([[-1, 0, 1],
                    [-2, 0, 2],
                    [-1, 0, 1]], dtype=np.float64)

# ── (b) Original Sobel — full 3x3 convolution ───────────────────
conv_orig = convolve(gray, sobel_h, mode='constant', cval=0.0)
mn_o, mx_o = conv_orig.min(), conv_orig.max()
sobel_orig = ((conv_orig - mn_o) / (mx_o - mn_o) * 255).astype(np.uint8)

# ── (c) Approximated Sobel — downsample=4 + cross pattern ───────
downsample = 4
sobel_apx = np.zeros((h, w), dtype=np.float64)

# Cross pattern: center row + center column (5 of 9 pixels)
apx_min, apx_max = np.inf, -np.inf
for y in range(1, h - 1, downsample):
    for x in range(1, w - 1, downsample):
        pv = 0.0
        for i in range(-1, 2):
            pv += sobel_h[1, i + 1] * gray[y, x + i]
        pv += sobel_h[0, 1] * gray[y - 1, x]
        pv += sobel_h[2, 1] * gray[y + 1, x]
        if pv < apx_min: apx_min = pv
        if pv > apx_max: apx_max = pv

# Block-fill so bird is fully visible (4x4 uniform blocks)
rng = apx_max - apx_min if apx_max != apx_min else 1.0
for y in range(1, h - 1, downsample):
    for x in range(1, w - 1, downsample):
        pv = 0.0
        for i in range(-1, 2):
            pv += sobel_h[1, i + 1] * gray[y, x + i]
        pv += sobel_h[0, 1] * gray[y - 1, x]
        pv += sobel_h[2, 1] * gray[y + 1, x]
        val = int(255 * (pv - apx_min) / rng)
        val = max(0, min(255, val))
        for fy in range(downsample):
            for fx in range(downsample):
                if y + fy < h and x + fx < w:
                    sobel_apx[y + fy, x + fx] = val

sobel_apx = sobel_apx.astype(np.uint8)

# ── Find a good patch location to showcase uniform blocks ────────
# Look for a region where sobel_apx has uniform blocks (it will everywhere)
# Pick a spot in the upper-middle area with medium-brightness blocks
py, px = 160, 200  # bird body area — adjust as needed
# Snap to block boundary
py = (py // downsample) * downsample + 1
px = (px // downsample) * downsample + 1

# Get a 1x3 strip of adjacent block values (3 consecutive block centers)
strip_vals = []
for i in range(3):
    strip_vals.append(int(sobel_apx[py, px + i * downsample]))

print(f"Inset strip at ({py},{px}): {strip_vals}")

# ── Build figure ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=200,
                         facecolor='white')
fig.patch.set_facecolor('white')

images_data = [gray.astype(np.uint8), sobel_orig, sobel_apx]
labels = ['(a)', '(b)', '(c)']

for ax, im, lbl in zip(axes, images_data, labels):
    ax.set_facecolor('white')
    ax.imshow(im, cmap='gray', vmin=0, vmax=255)
    ax.set_title(lbl, fontsize=16, fontweight='bold', pad=8, color='black')
    ax.axis('off')

plt.tight_layout()

out = '/home/nsola5/CheckMate/final_results/eval_T21_T30_RF1_68uF/sobel_comparison_figure'
fig.savefig(out + '.png', dpi=300, bbox_inches='tight', facecolor='white')
fig.savefig(out + '.pdf', bbox_inches='tight', facecolor='white')
plt.close()
print(f"Saved {out}.png and .pdf")
