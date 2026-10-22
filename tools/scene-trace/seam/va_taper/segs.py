import sys, numpy as np; from PIL import Image
A=np.asarray(Image.open('../A.png').convert('RGB')).astype(float)@[0.299,0.587,0.114]
B=np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float)@[0.299,0.587,0.114]
segs=[(81,200),(200,262),(262,385),(385,664),(664,740),(740,770),(770,857)]
print('seam per segment:', ' '.join(f'{a}-{b}:{np.abs(A[-1,a:b]-B[0,a:b]).mean():.1f}' for a,b in segs))
