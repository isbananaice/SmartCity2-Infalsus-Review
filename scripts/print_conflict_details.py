import json
import cv2
from pathlib import Path

train_dir = Path(r'Infalsus Review-Uploaded.coco\train')
with open(r'Infalsus Review-Uploaded.coco\train\_annotations.coco.json', 'r', encoding='utf-8') as f:
    coco = json.load(f)

img_by_id = {img['id']: img for img in coco['images']}
cat_by_id = {cat['id']: cat['name'] for cat in coco['categories']}
ann_by_id = {ann['id']: ann for ann in coco['annotations']}

conflict_pairs = [
    (694, 696, "train_04_f001794_t22-50s"),
    (848, 849, "train_04_f001629_t19-75s"),
    (851, 852, "train_05_f001161_t10-75s"),
    (287, 289, "train_04_f001404_t16-00s"),
    (734, 735, "train_05_f001356_t14-00s"),
    (965, 966, "train_05_f001626_t18-50s"),
    (993, 995, "train_05_f001386_t14-50s"),
]

for a1, a2, label in conflict_pairs:
    ann1 = ann_by_id[a1]
    ann2 = ann_by_id[a2]
    print(f"\n--- {label} ---")
    print(f"Ann 1: ID={a1}, Cat={cat_by_id[ann1['category_id']]}, Box={ann1['bbox']}")
    print(f"Ann 2: ID={a2}, Cat={cat_by_id[ann2['category_id']]}, Box={ann2['bbox']}")
