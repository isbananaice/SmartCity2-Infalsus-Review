import shutil
import random
from pathlib import Path
import cv2
import numpy as np

def augment_image_minority(src_img_path: Path, dest_img_path: Path, mode: int):
    img = cv2.imread(str(src_img_path))
    if img is None:
        return
        
    if mode == 1:
        # Slight brightness increase (+15)
        augmented = cv2.convertScaleAbs(img, alpha=1.05, beta=12)
    elif mode == 2:
        # Slight contrast and saturation boost
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.15, 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 0.95, 0, 255)
        augmented = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    elif mode == 3:
        # Subtle Gaussian blur (mimicking fast note motion)
        augmented = cv2.GaussianBlur(img, (3, 3), 0.5)
    else:
        augmented = img
        
    cv2.imwrite(str(dest_img_path), augmented)

def oversample_minority_classes(dataset_root: Path, multiplier: int = 3):
    train_lbl_dir = dataset_root / "labels" / "train"
    train_img_dir = dataset_root / "images" / "train"
    
    lbl_files = list(train_lbl_dir.glob("*.txt"))
    print(f"Scanning {len(lbl_files)} training label files...")
    
    minority_files = []
    for lf in lbl_files:
        with open(lf, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        classes = {int(l.split()[0]) for l in lines}
        # Class 1 is near, Class 2 is break
        if 1 in classes or 2 in classes:
            minority_files.append((lf, lines))
            
    print(f"Found {len(minority_files)} training files containing 'near' or 'break'.")
    
    added_count = 0
    for lf, lines in minority_files:
        stem = lf.stem
        src_img = train_img_dir / f"{stem}.jpg"
        if not src_img.exists():
            continue
            
        for m in range(1, multiplier + 1):
            aug_stem = f"{stem}_aug{m}"
            dest_img = train_img_dir / f"{aug_stem}.jpg"
            dest_lbl = train_lbl_dir / f"{aug_stem}.txt"
            
            # Create augmented image
            augment_image_minority(src_img, dest_img, mode=m)
            
            # Write identical bounding boxes
            with open(dest_lbl, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
                
            added_count += 1
            
    print(f"Successfully generated {added_count} augmented minority samples!")
    print(f"Total training images now: {len(list(train_img_dir.glob('*.jpg')))}")
    print(f"Total training labels now: {len(list(train_lbl_dir.glob('*.txt')))}")

if __name__ == "__main__":
    dataset_path = Path(r"C:\Users\USER\Desktop\smartcity2\data\dataset")
    oversample_minority_classes(dataset_path, multiplier=3)
