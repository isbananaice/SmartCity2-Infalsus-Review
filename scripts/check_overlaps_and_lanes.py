import json
from pathlib import Path
from collections import defaultdict

with open(r'Infalsus Review-Uploaded.coco\train\_annotations.coco.json', 'r', encoding='utf-8') as f:
    coco = json.load(f)

img_by_id = {img['id']: img for img in coco['images']}
cat_by_id = {cat['id']: cat['name'] for cat in coco['categories']}

# Let's inspect all high overlap pairs
anns_by_img = defaultdict(list)
for ann in coco['annotations']:
    anns_by_img[ann['image_id']].append(ann)

def calculate_iou(box1, box2):
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    xa = max(x1, x2)
    ya = max(y1, y2)
    xb = min(x1 + w1, x2 + w2)
    yb = min(y1 + h1, y2 + h2)
    inter_area = max(0, xb - xa) * max(0, yb - ya)
    area1 = w1 * h1
    area2 = w2 * h2
    union_area = area1 + area2 - inter_area
    return inter_area / union_area if union_area > 0 else 0.0

duplicates = []
for img_id, anns in anns_by_img.items():
    for i in range(len(anns)):
        for j in range(i + 1, len(anns)):
            iou = calculate_iou(anns[i]['bbox'], anns[j]['bbox'])
            if iou > 0.4:
                duplicates.append({
                    "img_id": img_id,
                    "file_name": img_by_id[img_id]['file_name'],
                    "ann1": anns[i],
                    "ann2": anns[j],
                    "cat1": cat_by_id.get(anns[i]['category_id']),
                    "cat2": cat_by_id.get(anns[j]['category_id']),
                    "iou": iou
                })

print(f"Total overlapping pairs (IoU > 0.4): {len(duplicates)}")
print("\n--- Overlapping pairs breakdown ---")
for d in duplicates:
    print(f"File: {d['file_name']}")
    print(f"  IoU: {d['iou']:.3f} | {d['cat1']} (id={d['ann1']['id']}) vs {d['cat2']} (id={d['ann2']['id']})")
    print(f"  Box1: {d['ann1']['bbox']}")
    print(f"  Box2: {d['ann2']['bbox']}")

# Check lane distribution of annotations
# lanes config: 0.00-0.16, 0.16-0.32, 0.32-0.48, 0.48-0.64, 0.64-0.80, 0.80-1.00
lanes_dist = defaultdict(lambda: defaultdict(int))
for ann in coco['annotations']:
    x, y, w, h = ann['bbox']
    cx = (x + w / 2.0) / 1728.0
    cat = cat_by_id[ann['category_id']]
    if cx < 0.16:
        lane = "Lane 1 (Shift)"
    elif cx < 0.32:
        lane = "Lane 2 (A)"
    elif cx < 0.48:
        lane = "Lane 3 (S)"
    elif cx < 0.64:
        lane = "Lane 4 (D)"
    elif cx < 0.80:
        lane = "Lane 5 (F)"
    else:
        lane = "Lane 6 (Space)"
    lanes_dist[lane][cat] += 1

print("\n--- Lane Distribution ---")
for lane in sorted(lanes_dist.keys()):
    print(f"{lane}: {dict(lanes_dist[lane])}")

# Check video source distribution
video_source_dist = defaultdict(int)
for img in coco['images']:
    orig_name = img.get('extra', {}).get('name', img['file_name'])
    vname = orig_name.split('_f')[0]
    video_source_dist[vname] += 1

print("\n--- Video Source Frame Counts ---")
for vname, cnt in sorted(video_source_dist.items()):
    print(f"{vname}: {cnt} frames")
