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
    val_img_dir = ROOT_DIR / "data" / "dataset" / "images" / "val"
    if not train_img_dir.exists() or not list(train_img_dir.glob("*.jpg")):
        print(f"[錯誤] 訓練集圖片目錄為空 ({train_img_dir})。")
        return
        
    n_train = len(list(train_img_dir.glob("*.jpg")))
    n_val = len(list(val_img_dir.glob("*.jpg")))
    print(f"[資料集狀態] 訓練集: {n_train} 張, 驗證集: {n_val} 張")

    # 載入 YOLOv11 官方輕量預訓練模型
    print("\n[模型載入] 載入官方 YOLOv11n 基礎預訓練權重 (yolo11n.pt)...")
    model = YOLO("yolo11n.pt")

    # 開始訓練
    # 注意事項：
    # 1. fliplr=0.0: 文字辨識禁止水平翻轉 (避免鏡像字)
    # 2. mosaic=0.5: 輕度拼貼增強，防止過擬合且保持判定線物理空間特徵
    # 3. imgsz=640: 最適合小目標判定文字尺寸
    print("\n[開始微調訓練] 進行 50 Epochs 遷移學習 (含早停機制)...")
    results = model.train(
        data=str(data_yaml),
        epochs=50,
        imgsz=640,
        batch=16,
        device=device,
        workers=4,
        patience=15,
        fliplr=0.0,       # 關鍵：禁止水平鏡像翻轉文字
        flipud=0.0,       # 禁止垂直翻轉
        mosaic=0.5,       # 適度拼貼增強多目標檢測
        mixup=0.1,        # 輕微疊加提高光效泛化
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
