"""look.py x0 x1 ya yb scale out [img]: labeled crop of the A-over-B stack (y relative to the join; negative = A)."""
import sys, numpy as np
from PIL import Image, ImageDraw
H=1678
x0,x1,ya,yb=map(int,sys.argv[1:5]); s=float(sys.argv[5]); out=sys.argv[6]
bp=sys.argv[7] if len(sys.argv)>7 else 'base/B_warp.png'
A=np.asarray(Image.open('../A.png').convert('RGB')); B=np.asarray(Image.open(bp).convert('RGB'))
c=np.vstack([A,B])[H+ya:H+yb, x0:x1]
im=Image.fromarray(c).resize((int((x1-x0)*s),int((yb-ya)*s)),Image.LANCZOS); d=ImageDraw.Draw(im)
step=20 if s>=2 else 50
for y in range((ya//step)*step,yb,step):
    if y<ya: continue
    d.line([(0,(y-ya)*s),(10,(y-ya)*s)],fill=(255,0,0)); d.text((12,(y-ya)*s-5),str(y),fill=(255,0,0))
for x in range((x0//step+1)*step,x1,step):
    d.line([((x-x0)*s,0),((x-x0)*s,8)],fill=(0,0,255)); d.text(((x-x0)*s+2,8),str(x),fill=(0,0,255))
im.save(out)
