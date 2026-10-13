"""Quick CPU preview of traced shapes (Skia), for scoring before the Swift build."""
import numpy as np
import skia


def render(shapes, W, H):
    surface = skia.Surface(W, H)
    cv = surface.getCanvas()
    cv.clear(skia.ColorWHITE)
    for sh in shapes:
        path = skia.Path()
        path.setFillType(skia.PathFillType.kEvenOdd)
        for segs in sh['subpaths']:
            path.moveTo(*segs[0][0])
            for b in segs:
                path.cubicTo(*b[1], *b[2], *b[3])
            path.close()
        f = sh['fill']
        paint = skia.Paint(AntiAlias=True)
        if f['type'] == 'flat':
            r, g, b = (int(round(v)) for v in f['color'])
            paint.setColor(skia.Color(r, g, b))
        else:
            cols = [skia.Color(*(int(round(v)) for v in c)) for c in f['colors']]
            paint.setShader(skia.GradientShader.MakeLinear([skia.Point(*f['p0']), skia.Point(*f['p1'])], cols))
        cv.drawPath(path, paint)
    a = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    return a[..., :3].astype(np.float64)
