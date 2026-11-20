from pathlib import Path
import cv2
import numpy as np

debug_dir = Path("reports/debug_conflicts")
for p in debug_dir.glob("*.jpg"):
    img = cv2.imread(str(p))
    if img is not None:
        h, w = img.shape[:2]
        print(f"Conflict file: {p.name}, size: {w}x{h}")
