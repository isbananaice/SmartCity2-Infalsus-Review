import json
import shutil
from pathlib import Path
from collections import defaultdict
import numpy as np

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

def clean_and_convert(coco_dir: str, output_dataset_dir: str):
    coco_path = Path(coco_dir)
    json_path = coco_path / "train" / "_annotations.coco.json"
    with open(json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)
        
    out_dir = Path(output_dataset_dir)
    out_img_dir = out_dir / "images" / "train"
    out_lbl_dir = out_dir / "labels" / "train"
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)
    
    cat_by_id = {cat['id']: cat['name'] for cat in coco['categories']}
    
    # Target classes: 0: exact, 1: near, 2: break
    target_classes = {"exact": 0, "near": 1, "break": 2}
    
    anns_by_img = defaultdict(list)
    for ann in coco['annotations']:
        cat_name = cat_by_id.get(ann['category_id'])
        if cat_name in target_classes:
            anns_by_img[ann['image_id']].append(ann)
            
    img_by_id = {img['id']: img for img in coco['images']}
    
    total_raw_anns = len(coco['annotations'])
    cleaned_anns_count = 0
    removed_review_class = 0
    removed_duplicates = 0
    resolved_conflicts = 0
    
    train_source_dir = json_path.parent
    
    final_class_counts = defaultdict(int)
    
    for img_id, img_info in img_by_id.items():
        fname = img_info['file_name']
        src_img_path = train_source_dir / fname
        dest_img_path = out_img_dir / fname
        
        # Copy image if not exists
        if not dest_img_path.exists() and src_img_path.exists():
            shutil.copy2(src_img_path, dest_img_path)
            
        raw_anns = anns_by_img.get(img_id, [])
        
        # Sort annotations so that near and break come before exact
        # Priority: break (2), near (1), exact (0)
        # So if conflict exists, the rarer and hand-labeled near/break is preserved!
        def priority(a):
            c = cat_by_id[a['category_id']]
            if c == 'break': return 3
            if c == 'near': return 2
            if c == 'exact': return 1
            return 0
            
        sorted_anns = sorted(raw_anns, key=priority, reverse=True)
        
        kept_anns = []
        for ann in sorted_anns:
            box = ann['bbox']
            cat = cat_by_id[ann['category_id']]
            
            # Check overlap with already kept annotations
            overlap = False
            for kept in kept_anns:
                iou = calculate_iou(box, kept['bbox'])
                if iou > 0.4:
                    overlap = True
                    kept_cat = cat_by_id[kept['category_id']]
                    if kept_cat == cat:
                        removed_duplicates += 1
                    else:
                        resolved_conflicts += 1
                    break
                    
            if not overlap:
                kept_anns.append(ann)
                
        # Write YOLO label file (.txt)
        img_w = float(img_info['width'])
        img_h = float(img_info['height'])
        
        lbl_file = out_lbl_dir / (Path(fname).stem + ".txt")
        lines = []
        for ann in kept_anns:
            cat_name = cat_by_id[ann['category_id']]
            cls_id = target_classes[cat_name]
            x, y, w, h = ann['bbox']
            
            cx = (x + w / 2.0) / img_w
            cy = (y + h / 2.0) / img_h
            nw = w / img_w
            nh = h / img_h
            
            lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            final_class_counts[cat_name] += 1
            cleaned_anns_count += 1
            
        with open(lbl_file, "w", encoding="utf-8") as lf:
            lf.write("\n".join(lines))
            
    print(f"Dataset Cleaning and YOLO Conversion Summary:")
    print(f"  - Total Raw Annotations: {total_raw_anns}")
    print(f"  - Removed Project-Name / Invalid Class: 1")
    print(f"  - Removed Same-Class Duplicates (IoU > 0.4): {removed_duplicates}")
    print(f"  - Resolved Cross-Class Conflicts (Prioritized near/break): {resolved_conflicts}")
    print(f"  - Final Cleaned Annotations: {cleaned_anns_count}")
    print(f"  - Final Cleaned Class Distribution: {dict(final_class_counts)}")
    print(f"  - Images Output: {len(list(out_img_dir.glob('*.jpg')))}")
    print(f"  - Labels Output: {len(list(out_lbl_dir.glob('*.txt')))}")

if __name__ == "__main__":
    clean_and_convert(
        r"C:\Users\USER\Desktop\smartcity2\Infalsus Review-Uploaded.coco",
        r"C:\Users\USER\Desktop\smartcity2\data\dataset"
    )
