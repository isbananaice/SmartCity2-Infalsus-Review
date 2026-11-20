from ultralytics import YOLO

def main():
    model = YOLO("models/yolov11_infalsus_best.pt")
    metrics = model.val(data="data/data.yaml", device="cuda:0", split="val", workers=1, plots=False)

    print("\n" + "=" * 60)
    print("  YOLOv11 模型在獨立驗證集 (75 張未見過影格) 上的精確度驗證")
    print("=" * 60)
    print(f"整體 mAP50:       {metrics.box.map50 * 100:.2f}%")
    print(f"整體 mAP50-95:    {metrics.box.map * 100:.2f}%")
    print(f"整體 Precision:   {metrics.box.mp * 100:.2f}%")
    print(f"整體 Recall:      {metrics.box.mr * 100:.2f}%")

    print("\n--- 各類別細部指標 ---")
    class_names = ["exact", "near", "break"]
    for i, name in enumerate(class_names):
        p = metrics.box.p[i] * 100
        r = metrics.box.r[i] * 100
        ap50 = metrics.box.ap50[i] * 100
        ap = metrics.box.ap[i] * 100
        f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
        print(f"[{name.upper()}]")
        print(f"  - Precision (查準率): {p:.2f}%")
        print(f"  - Recall    (召回率): {r:.2f}%")
        print(f"  - F1-Score  (平衡分): {f1:.2f}%")
        print(f"  - mAP@0.5  (準確率): {ap50:.2f}%")
        print(f"  - mAP@0.5:0.95:      {ap:.2f}%")

if __name__ == "__main__":
    main()
