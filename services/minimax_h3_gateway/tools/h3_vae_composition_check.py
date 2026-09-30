#!/usr/bin/env python3
"""CPU-only seam mechanism check against the installed H3 tiled decoder.

Run inside each ComfyUI image without GPU access. A synthetic tile decoder
isolates composition from the VAE weights and diffusion sampling; independent
two-way overlap-add supplies the expected pixels, not another runtime's image.
"""
from __future__ import annotations

import argparse
import json
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expect', choices=['affected', 'fixed'], required=True)
option = parser.parse_args()
sys.argv = ['main.py', '--cpu']

import comfy.options

comfy.options.enable_args_parsing()

import torch
from comfy.cli_args import args

args.cpu = True

from comfy.ldm.minimax.vae import MiniMaxH3VideoVAE


def synthetic_decode(latent):
    pixels = latent.repeat_interleave(16, -2).repeat_interleave(16, -1)
    # Different local edge gradients make raw/composited-tail confusion visible.
    y = torch.linspace(0, 1, pixels.shape[-2]).view(1, 1, 1, -1, 1)
    x = torch.linspace(0, 1, pixels.shape[-1]).view(1, 1, 1, 1, -1)
    return pixels + y.square() + 2 * x.square()


def axis_weights(index, length, overlaps, count):
    result = torch.ones(length)
    if index:
        extent = overlaps[index - 1]
        result[:extent] *= torch.arange(extent) / extent
    if index < count - 1:
        extent = overlaps[index]
        result[-extent:] *= 1 - torch.arange(extent) / extent
    return result


vae = MiniMaxH3VideoVAE.__new__(MiniMaxH3VideoVAE)
torch.nn.Module.__init__(vae)
vae.vae_ratio = 16
vae.tile_size = 256
vae.tile_overlap_min = 64
vae._decode_pixels = synthetic_decode
latent = torch.arange(32 * 32, dtype=torch.float32).view(1, 1, 1, 32, 32) / 1024
ys, heights, yo = vae.split_tiles(512)
xs, widths, xo = vae.split_tiles(512)
expected = torch.zeros(1, 1, 1, 512, 512)
weight_sum = torch.zeros_like(expected)
for i, (y, height) in enumerate(zip(ys, heights)):
    for j, (x, width) in enumerate(zip(xs, widths)):
        tile = synthetic_decode(latent[..., y // 16:(y + height) // 16, x // 16:(x + width) // 16])
        wy = axis_weights(i, height, yo, len(ys)).view(-1, 1)
        wx = axis_weights(j, width, xo, len(xs)).view(1, -1)
        weights = wy * wx
        expected[..., y:y + height, x:x + width] += tile * weights
        weight_sum[..., y:y + height, x:x + width] += weights
expected /= weight_sum
actual = vae.tiled_decode(latent)
error = (actual - expected).abs()
result = {'kind': 'synthetic_two_way_h3_vae_composition', 'expected': option.expect,
          'grid': [len(ys), len(xs)], 'maxAbsError': error.max().item(),
          'meanAbsError': error.mean().item(), 'gpuUsed': False}
assert torch.all(weight_sum > 0)
fixed = result['maxAbsError'] < 1e-5
result['passed'] = fixed if option.expect == 'fixed' else not fixed
print(json.dumps(result))
raise SystemExit(0 if result['passed'] else 1)
