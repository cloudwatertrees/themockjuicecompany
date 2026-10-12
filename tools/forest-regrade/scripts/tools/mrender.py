import sys, numpy as np
from PIL import Image
import model
from art import load
d, out = sys.argv[1], sys.argv[2]
P = model.render(load(d), d)
Image.fromarray((np.clip(P, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out)
