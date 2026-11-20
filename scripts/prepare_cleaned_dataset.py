import json
import shutil
import random
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

def prepare_cleaned_dataset(coco_json_path: Path, dataset_root: Path, val_ratio: float = 0.20, seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    
    with open(coco_json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)
        
    cat_by_id = {cat['id']: cat['name'] for cat in coco['categories']}
    target_classes = {"exact": 0, "near": 1, "break": 2}
    
    # 1. Clean annotations
    anns_by_img = defaultdict(list)
    for ann in coco['annotations']:
        cname = cat_by_id.get(ann['category_id'])
        if cname in target_classes:
            anns_by_img[ann['image_id']].append(ann)
            
    cleaned_anns_by_img = {}
    stats_removed_dups = 0
    stats_resolved_conflicts = 0
    stats_class_counts = defaultdict(int)
    
    # Priority for NMS: break (3) > near (2) > exact (1)
    def priority(a):
        c = cat_by_id[a['category_id']]
        if c == 'break': return 3
        if c == 'near': return 2
        if c == 'exact': return 1
        return 0

    img_by_id = {img['id']: img for img in coco['images']}
    
    # Categorize images by their most critical label for stratified split
    # images with break -> group 1
    # images with near -> group 2
    # images with only exact -> group 3
    # images with 0 annotations -> group 4
    img_groups = defaultdict(list)
    
    for img_id, img_info in img_by_id.items():
        raw_anns = anns_by_img.get(img_id, [])
        sorted_anns = sorted(raw_anns, key=priority, reverse=True)
        
        kept = []
        for ann in sorted_anns:
            box = ann['bbox']
            cat = cat_by_id[ann['category_id']]
            
            overlap = False
            for k in kept:
                if calculate_iou(box, k['bbox']) > 0.4:
                    overlap = True
                    k_cat = cat_by_id[k['category_id']]
                    if k_cat == cat:
                        stats_removed_dups += 1
                    else:
                        stats_resolved_conflicts += 1
                    break
            if not overlap:
                kept.append(ann)
                stats_class_counts[cat] += 1
                
        cleaned_anns_by_img[img_id] = kept
        
        # Determine stratification group
        cats_in_img = {cat_by_id[a['category_id']] for a in kept}
        if "break" in cats_in_img:
            img_groups["has_break"].append(img_id)
        elif "near" in cats_in_img:
            img_groups["has_near"].append(img_id)
        elif "exact" in cats_in_img:
            img_groups["exact_only"].append(img_id)
        else:
            img_groups["empty"].append(img_id)
            
    # 2. Stratified split into train & val
    train_ids = set()
    val_ids = set()
    
    for gname, ids in img_groups.items():
        random.shuffle(ids)
        n_val = int(round(len(ids) * val_ratio))
        # Ensure at least 1 in val if group is not tiny
        if n_val == 0 and len(ids) >= 3:
            n_val = 1
        val_subset = ids[:n_val]
        train_subset = ids[n_val:]
        val_ids.update(val_subset)
        train_ids.update(train_subset)
        print(f"Stratified group '{gname}': total={len(ids)} -> train={len(train_subset)}, val={len(val_subset)}")
        
    print(f"\nTotal split: Train={len(train_ids)} images, Val={len(val_ids)} images")
    
    # 3. Prepare target folders (clean them up first)
    for split in ["train", "val"]:
        p_img = dataset_root / "images" / split
        p_lbl = dataset_root / "labels" / split
        if p_img.exists():
            shutil.rmtree(p_img)
        if p_lbl.exists():
            shutil.rmtree(p_lbl)
        p_img.mkdir(parents=True, exist_ok=True)
        p_lbl.mkdir(parents=True, exist_ok=True)
        
    source_img_dir = coco_json_path.parent
    
    split_stats = {"train": defaultdict(int), "val": defaultdict(int)}
    
    # 4. Copy images and write YOLO labels
    for split, id_set in [("train", train_ids), ("val", val_ids)]:
        dest_img_dir = dataset_root / "images" / split
        dest_lbl_dir = dataset_root / "labels" / split
        
        for img_id in id_set:
            img_info = img_by_id[img_id]
            fname = img_info['file_name']
            src_file = source_img_dir / fname
            dest_file = dest_img_dir / fname
            
            # Copy image
            shutil.copy2(src_file, dest_file)
            
            # YOLO label
            anns = cleaned_anns_by_img[img_id]
            lbl_file = dest_lbl_dir / (Path(fname).stem + ".txt")
            
            img_w = float(img_info['width'])
            img_h = float(img_info['height'])
            
            lines = []
            for a in anns:
                cat_name = cat_by_id[a['category_id']]
                cls_id = target_classes[cat_name]
                x, y, w, h = a['bbox']
                cx = (x + w / 2.0) / img_w
                cy = (y + h / 2.0) / img_h
                nw = w / img_w
                nh = h / img_h
                lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
                split_stats[split][cat_name] += 1
                
            with open(lbl_file, "w", encoding="utf-8") as lf:
                lf.write("\n".join(lines))
                
    # 5. Write data.yaml
    data_yaml_content = f"""# YOLOv11 In Falsus Hit Detection Dataset Config
path: {dataset_root.as_posix()}
train: images/train
val: images/val

names:
  0: exact
  1: near
  2: break

# Dataset statistics
# Train: {len(train_ids)} images, Val: {len(val_ids)} images
# Total Clean Instances: {dict(stats_class_counts)}
"""
    yaml_path = dataset_root.parent / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(data_yaml_content)
        
    print(f"\nWritten {yaml_path}")
    print(f"Train set labels: {dict(split_stats['train'])}")
    print(f"Val set labels:   {dict(split_stats['val'])}")
    print("\nDataset preparation completed successfully!")

if __name__ == "__main__":
    coco_json = Path(r"C:\Users\USER\Desktop\smartcity2\Infalsus Review-Uploaded.coco\train\_annotations.coco.json")
    dataset_root = Path(r"C:\Users\USER\Desktop\smartcity2\data\dataset")
    prepare_cleaned_dataset(coco_json, dataset_root, val_ratio=0.20)
