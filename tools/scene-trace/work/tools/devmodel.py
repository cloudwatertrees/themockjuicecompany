"""devmodel.py DATADIR OUT.png : Python model render in device framing (393x852 @3x)."""
import sys, numpy as np
from PIL import Image
from pbrender import render
from pbart import load
from score import DS, DOX, DEV
img = render(load(sys.argv[1]), DS, DOX, 0, DEV[0], DEV[1])
Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8)).save(sys.argv[2])
