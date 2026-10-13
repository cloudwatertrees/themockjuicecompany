import numpy as np
import cv2


def to_lab(rgb):
    u8 = np.clip(rgb, 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(u8, cv2.COLOR_RGB2LAB).astype(float)
    lab[..., 0] *= 100 / 255
    lab[..., 1:] -= 128
    return lab


def to_hsv(rgb):
    u8 = np.clip(rgb, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV_FULL).astype(float)
    return hsv[..., 0] * 360 / 256, hsv[..., 1] / 255, hsv[..., 2] / 255
