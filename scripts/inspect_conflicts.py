import json
import cv2
from pathlib import Path

with open(r'Infalsus Review-Uploaded.coco\train\_annotations.coco.json', 'r', encoding='utf-8') as f:
    coco = json.load(f)

img_by_id = {img['id']: img for img in coco['images']}
cat_by_id = {cat['id']: cat['name'] for cat in coco['categories']}

# Find all conflicts
conflicts = [
    ("train_04_f001794_t22-50s", 694, 696), # exact vs break
    ("train_04_f001629_t19-75s", 848, 849), # exact vs near
    ("train_05_f001161_t10-75s", 851, 852), # near vs exact
    ("train_04_f001404_t16-00s", 287, 289), # near vs exact
    ("train_05_f001356_t14-00s", 734, 735), # exact vs near
    ("train_05_f001626_t18-50s", 965, 966), # break vs exact
    ("train_05_f001386_t14-50s", 993, 995), # exact vs break
]

ann_by_id = {ann['id']: ann for ann in coco['annotations']}

train_dir = Path(r'Infalsus Review-Uploaded.coco\train')
debug_dir = Path("reports/debug_conflicts")
debug_dir.mkdir(parents=True, exist_ok=True)

print("Checking conflict details:")
for stem, id1, id2 in conflicts:
    ann1 = ann_by_id.get(id1)
    ann2 = ann_by_id.get(id2)
    img_info = img_by_id[ann1['image_id']]
    file_path = train_dir / img_info['file_name']
    
    img = cv2.imread(str(file_path))
    if img is not None:
        # Draw box 1 (green for exact, blue for near, red for break)
        def get_color(cat):
            if cat == 'exact': return (0, 255, 0)
            if cat == 'near': return (255, 165, 0)
            if cat == 'break': return (0, 0, 255)
            return (255, 255, 255)
            
        c1 = get_color(cat_by_id[ann1['category_id']])
        c2 = get_color(cat_by_id[ann2['category_id']])
        
        b1 = [int(v) for v in ann1['bbox']]
        b2 = [int(v) for v in ann2['bbox']]
        
        # Save a crop around this area
        xmin = max(0, min(b1[0], b2[0]) - 50)
        xmax = min(img.shape[1], max(b1[0]+b1[2], b2[0]+b2[2]) + 50)
        ymin = max(0, min(b1[1], b2[1]) - 20)
        ymax = min(img.shape[0], max(b1[1]+b1[3], b2[1]+b2[3]) + 40)
        
        crop = img.copy()
        cv2.rectangle(crop, (b1[0], b1[1]), (b1[0]+b1[2], b1[1]+b1[3]), c1, 2)
        cv2.putText(crop, f"{cat_by_id[ann1['category_id']]} ({id1})", (b1[0], max(15, b1[1]-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c1, 1)
        
        cv2.rectangle(crop, (b2[0], b2[1]), (b2[0]+b2[2], b2[1]+b2[3]), c2, 2)
        cv2.putText(crop, f"{cat_by_id[ann2['category_id']]} ({id2})", (b2[0], b2[1]+b2[3]+15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c2, 1)
        
        out_crop = crop[ymin:ymax, xmin:xmax]
        cv2.imwrite(str(debug_dir / f"conflict_{stem}_{id1}_{id2}.jpg"), out_crop)
        print(f"Saved conflict crop: {stem} -> {cat_by_id[ann1['category_id']]} vs {cat_by_id[ann2['category_id']]}")
