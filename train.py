import sys
import os
from pathlib import Path
import shutil
import yaml

ROOT_DIR = Path(__file__).resolve().parent

def run_training():
    print("=" * 60)
    print("  In Falsus YOLOv11 模型微調訓練程序 (Transfer Learning)")
    print("=" * 60)

    try:
        import torch
        from ultralytics import YOLO
    except ImportError:
        print("[錯誤] 尚未安裝 ultralytics 或 torch，請先執行：pip install ultralytics")
        return

    # 檢查硬體運算環境
    device = "0" if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"[硬體檢測] 運算裝置: {device_name} (Device: {device})")

    # 檢查資料集設定檔
    data_yaml = ROOT_DIR / "data" / "data.yaml"
    if not data_yaml.exists():
        print(f"[錯誤] 找不到資料集設定檔: {data_yaml}")
        return

    # 檢查訓練集目錄是否已有資料
    train_img_dir = ROOT_DIR / "data" / "dataset" / "images" / "train"
    if not train_img_dir.exists() or not list(train_img_dir.glob("*.jpg")):
        print(f"[警告] 訓練集圖片目錄為空 ({train_img_dir})。")
        print("請先執行抽幀腳本並標註圖片後再啟動訓練：")
        print("  1. python scripts/extract_training_frames.py")
        print("  2. 完成標註生成 labels/train/*.txt")
        return

    # 載入 YOLOv11 官方輕量預訓練模型
    print("\n[模型載入] 載入官方 YOLOv11n 基礎預訓練權重...")
    model = YOLO("yolo11n.pt")

    # 開始訓練
    print("\n[開始微調訓練] 進行 50 Epochs 遷移學習...")
    results = model.train(
        data=str(data_yaml),
        epochs=50,
        imgsz=640,
        batch=16,
        device=device,
        workers=4,
        patience=15,
        project=str(ROOT_DIR / "runs" / "detect"),
        name="infalsus_yolo11",
        exist_ok=True,
        verbose=True
    )

    # 將最佳權重儲存至 models/
    best_pt = ROOT_DIR / "runs" / "detect" / "infalsus_yolo11" / "weights" / "best.pt"
    models_dir = ROOT_DIR / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    target_pt = models_dir / "yolov11_infalsus_best.pt"

    if best_pt.exists():
        shutil.copy(str(best_pt), str(target_pt))
        print("\n" + "=" * 60)
        print("  訓練成功完成！")
        print(f"  最佳權重已儲存至: {target_pt}")
        print("  現在您可以直接執行 analyze_video.py 分析遊玩影片！")
        print("=" * 60)
    else:
        print("[提示] 訓練完成，但未定位到 best.pt，請檢查 runs/detect 目錄。")

if __name__ == "__main__":
    run_training()

