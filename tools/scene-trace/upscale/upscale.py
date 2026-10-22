"""2x upscale of the two home-screen sources with Real-ESRGAN (RealESRGAN_x4plus_anime_6B), run locally on the CPU.

usage: upscale.py A.png B.png OUTDIR
A is stacked over B and upscaled as one image (so the join is treated like any other row), 4x by the network, then
resampled to 2x (Lanczos, antialiased), and split back into OUTDIR/A2x.png and OUTDIR/B2x.png (1874x3356 each).
The network is RRDBNet (6 RRDB blocks, 64 features, growth 32), written out here so no basicsr install is needed.
Weights: weights/RealESRGAN_x4plus_anime_6B.pth from github.com/xinntao/Real-ESRGAN release v0.2.2.4, loaded with
weights_only=True."""
import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image


class RDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.rdb1, self.rdb2, self.rdb3 = RDB(nf, gc), RDB(nf, gc), RDB(nf, gc)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, nb=6, nf=64, gc=32):
        super().__init__()
        self.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode='nearest')))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode='nearest')))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


def upscale4(net, img, tile=192, pad=16):
    """img: H x W x 3 float in 0..1 -> 4H x 4W x 3, tiled with `pad` px of context per side."""
    H, W = img.shape[:2]
    out = np.zeros((H * 4, W * 4, 3), np.float32)
    t = torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).float()
    tp = F.pad(t, (pad, pad, pad, pad), mode='reflect')
    n = ((H + tile - 1) // tile) * ((W + tile - 1) // tile); k = 0
    for y in range(0, H, tile):
        for x in range(0, W, tile):
            h, w = min(tile, H - y), min(tile, W - x)
            with torch.inference_mode():
                o = net(tp[:, :, y:y + h + 2 * pad, x:x + w + 2 * pad])[0]
            o = o[:, pad * 4:(pad + h) * 4, pad * 4:(pad + w) * 4]
            out[y * 4:(y + h) * 4, x * 4:(x + w) * 4] = o.clamp(0, 1).numpy().transpose(1, 2, 0)
            k += 1
            print(f'\rtile {k}/{n}', end='', flush=True)
    print()
    return out


def main():
    a_png, b_png, outdir = sys.argv[1:4]
    os.makedirs(outdir, exist_ok=True)
    A = np.asarray(Image.open(a_png).convert('RGB')).astype(np.float32) / 255
    B = np.asarray(Image.open(b_png).convert('RGB')).astype(np.float32) / 255
    torch.set_num_threads(os.cpu_count() or 8)
    net = RRDBNet()
    sd = torch.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights', 'RealESRGAN_x4plus_anime_6B.pth'),
                    map_location='cpu', weights_only=True)
    net.load_state_dict(sd.get('params_ema', sd.get('params', sd)), strict=True)
    net.eval()
    x4 = upscale4(net, np.vstack([A, B]))
    im4 = Image.fromarray((x4 * 255 + 0.5).astype(np.uint8))
    W2, H2 = A.shape[1] * 2, (A.shape[0] + B.shape[0]) * 2
    im2 = im4.resize((W2, H2), Image.LANCZOS)
    h = A.shape[0] * 2
    im2.crop((0, 0, W2, h)).save(os.path.join(outdir, 'A2x.png'))
    im2.crop((0, h, W2, H2)).save(os.path.join(outdir, 'B2x.png'))
    print('wrote', outdir, im2.size)


if __name__ == '__main__':
    main()
