from pathlib import Path
import yaml

dataset_root = Path("data/dataset")
train_imgs = list((dataset_root / "images" / "train").glob("*.jpg"))
train_lbls = list((dataset_root / "labels" / "train").glob("*.txt"))
val_imgs = list((dataset_root / "images" / "val").glob("*.jpg"))
val_lbls = list((dataset_root / "labels" / "val").glob("*.txt"))

print(f"Train images: {len(train_imgs)}, Train labels: {len(train_lbls)}")
print(f"Val images:   {len(val_imgs)}, Val labels:   {len(val_lbls)}")

# Check 1-to-1 matching
train_unmatched_imgs = [img for img in train_imgs if not (dataset_root / "labels" / "train" / (img.stem + ".txt")).exists()]
val_unmatched_imgs = [img for img in val_imgs if not (dataset_root / "labels" / "val" / (img.stem + ".txt")).exists()]
print(f"Unmatched in Train: {len(train_unmatched_imgs)}")
print(f"Unmatched in Val:   {len(val_unmatched_imgs)}")

with open("data/data.yaml", "r", encoding="utf-8") as f:
    dy = yaml.safe_load(f)
print(f"data.yaml contents: {dy}")
