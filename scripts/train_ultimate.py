import sys
import os
from pathlib import Path
import shutil
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent

def main():
    print("=" * 70)
    print("  In Falsus YOLOv11s 終極全方位強化訓練 (Ultimate High-Precision Pipeline)")
    print("  組合所有最佳化策略:")
    print("  1. 骨幹升級: YOLOv11s (9.4M 參數量，高達 3.6x 深度特徵金字塔)")
    print("  2. 超高解析度: imgsz=960 (文字筆畫像素放大 2.25x，專克微小判定文字)")
    print("  3. 專業音遊增強: 禁止翻轉 (fliplr=0, flipud=0)、mosaic=0.5、mixup=0.1、close_mosaic=10")
    print("  4. 學習率優化: 余弦退火 (cos_lr=True)")
    print("  5. GPU 硬體加速: RTX 3070 8GB FP16 加速")
    print("=" * 70)

    import torch
    from ultralytics import YOLO

    device = "0" if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"\n[硬體檢測] 運算裝置: {device_name} (Device: {device})")

    data_yaml = ROOT_DIR / "data" / "data.yaml"
    if not data_yaml.exists():
        print(f"[錯誤] 找不到資料集設定檔: {data_yaml}")
        return

    # 載入 YOLOv11s 模型
    print("\n[模型載入] 載入官方 YOLOv11s 權重 (yolo11s.pt)...")
    model = YOLO("yolo11s.pt")

    # 開始訓練
    save_project = ROOT_DIR / "runs" / "detect"
    run_name = "infalsus_yolo11s_ultimate"

    print("\n[開始終極訓練] 進行 50 Epochs 遷移學習...")
    results = model.train(
        data=str(data_yaml),
        epochs=50,
        imgsz=960,
        batch=8,
        device=device,
        workers=2,
        patience=15,
        cos_lr=True,       # 餘弦退火學習率
        fliplr=0.0,        # 關鍵：禁止水平鏡像翻轉文字
        flipud=0.0,        # 禁止垂直翻轉
        mosaic=0.5,        # 輕度拼貼
        mixup=0.1,         # 特效疊加增強
        close_mosaic=10,   # 最後 10 輪關閉拼貼以在原圖精確收斂
        project=str(save_project),
        name=run_name,
        exist_ok=True,
        verbose=True
    )

    # 複製最佳權重至 models/
    best_pt = save_project / run_name / "weights" / "best.pt"
    models_dir = ROOT_DIR / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    target_pt = models_dir / "yolov11s_infalsus_ultimate.pt"

    if best_pt.exists():
        shutil.copy(str(best_pt), str(target_pt))
        print("\n" + "=" * 70)
        print("  終極模型訓練成功！")
        print(f"  最佳權重已儲存至: {target_pt}")
        print("=" * 70)
    else:
        print("[警告] 未找到 best.pt，請檢查 runs/detect 目錄。")

if __name__ == "__main__":
    main()
