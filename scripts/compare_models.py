import sys
from pathlib import Path
from ultralytics import YOLO

ROOT_DIR = Path(__file__).resolve().parent.parent

def eval_model(name: str, weights_path: str, imgsz: int = 960, conf: float = 0.55):
    print(f"\n>>> 評估模型: {name} (imgsz={imgsz}, conf={conf})")
    model = YOLO(weights_path)
    metrics = model.val(
        data=str(ROOT_DIR / "data" / "data.yaml"),
        imgsz=imgsz,
        conf=conf,
        device="cuda:0",
        split="val",
        workers=1,
        plots=False,
        verbose=False
    )
    res = {
        "name": name,
        "mAP50": metrics.box.map50 * 100,
        "mAP50_95": metrics.box.map * 100,
        "precision": metrics.box.mp * 100,
        "recall": metrics.box.mr * 100,
        "classes": {}
    }
    class_names = ["exact", "near", "break"]
    for i, cname in enumerate(class_names):
        p = metrics.box.p[i] * 100
        r = metrics.box.r[i] * 100
        ap50 = metrics.box.ap50[i] * 100
        f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
        res["classes"][cname] = {
            "p": p, "r": r, "f1": f1, "ap50": ap50
        }
    return res

def main():
    print("=" * 75)
    print("  In Falsus 模型極致強化對比分析 (Baseline YOLOv11n vs Ultimate YOLOv11s)")
    print("=" * 75)

    base_pt = str(ROOT_DIR / "models" / "yolov11_infalsus_best.pt")
    ult_pt = str(ROOT_DIR / "models" / "yolov11s_infalsus_ultimate.pt")

    if not Path(ult_pt).exists():
        print(f"[提示] 尚未找到 {ult_pt}，請等待訓練完成。")
        return

    m_base = eval_model("YOLOv11n (Baseline 640px, conf=0.40)", base_pt, imgsz=640, conf=0.40)
    m_base_opt = eval_model("YOLOv11n (Optimized 640px, conf=0.55)", base_pt, imgsz=640, conf=0.55)
    m_ult = eval_model("YOLOv11s (Ultimate 960px, conf=0.55)", ult_pt, imgsz=960, conf=0.55)

    print("\n" + "=" * 75)
    print(f"{'模型版本':<35} | {'mAP@0.5':<10} | {'mAP50-95':<10} | {'Precision':<10} | {'Recall':<10}")
    print("-" * 75)
    for m in [m_base, m_base_opt, m_ult]:
        print(f"{m['name']:<35} | {m['mAP50']:>8.2f}% | {m['mAP50_95']:>8.2f}% | {m['precision']:>8.2f}% | {m['recall']:>8.2f}%")
    print("=" * 75)

    print("\n--- 各類別細部指標 (Ultimate YOLOv11s) ---")
    for cname, stats in m_ult["classes"].items():
        print(f"[{cname.upper()}]  Precision: {stats['p']:.2f}% | Recall: {stats['r']:.2f}% | F1: {stats['f1']:.2f}% | mAP50: {stats['ap50']:.2f}%")

if __name__ == "__main__":
    main()
