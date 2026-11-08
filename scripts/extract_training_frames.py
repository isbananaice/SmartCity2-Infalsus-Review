import sys
import os
from pathlib import Path
import argparse
import cv2
import yaml
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, total=None, desc=""):
        return iterable

# 將專案根目錄加入路徑
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.video_utils import VideoProcessor
from src.countdown_detector import CountdownDetector

def extract_frames_for_training(video_path: Path, output_dir: Path, roi_config: dict, sample_interval: int = 12, max_frames: int = 80):
    """從單一訓練影片抽取出適合標註的 ROI 圖片 (每首約 60~80 張，過濾重複影格)"""
    print(f"\n[處理影片] {video_path.name}")
    
    # 1. 偵測歌曲倒數與開始時間
    cd_detector = CountdownDetector()
    start_sec, info = cd_detector.detect_song_start_time(str(video_path))
    print(f"  - 偵測到歌曲正式開始時間: {start_sec:.2f} 秒 (依據: {info['method']})")

    # 2. 開啟影片處理器並從開始時間抽幀
    vproc = VideoProcessor(str(video_path), roi_config=roi_config)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    prev_saved_gray = None
    end_sec = max(start_sec + 10, vproc.duration_seconds - 5)
    
    for f_idx, t_sec, frame, roi in vproc.frame_generator(start_sec=start_sec, end_sec=end_sec, step=sample_interval):
        if saved >= max_frames:
            break

        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # 1. 亮度門檻：過濾全黑或幾乎無音符的影格
        if cv2.mean(gray_roi)[0] < 20:
            continue

        # 2. 去重檢查：過濾與前一張過於相似的重複影格 (確保每張都具有獨特擊打或譜面狀態)
        if prev_saved_gray is not None:
            diff = cv2.absdiff(prev_saved_gray, gray_roi)
            if cv2.mean(diff)[0] < 8.0:
                continue

        song_time = t_sec - start_sec
        fname = f"{video_path.stem}_f{f_idx:06d}_t{song_time:.2f}s.jpg"
        cv2.imwrite(str(output_dir / fname), roi)
        prev_saved_gray = gray_roi.copy()
        saved += 1

    print(f"  - 成功抽取出 {saved} 張高品質 ROI 影格至: {output_dir}")
    return saved

def main():
    parser = argparse.ArgumentParser(description="In Falsus 訓練資料集抽幀工具 (自動跳過前導選曲與倒數)")
    parser.add_argument("--input_dir", type=str, default="data/videos", help="存放已更名訓練影片的資料夾")
    parser.add_argument("--output_dir", type=str, default="data/dataset/images/train", help="抽取圖片儲存目錄")
    parser.add_argument("--interval", type=int, default=15, help="抽幀間隔 (預設每 15 幀抽 1 張)")
    parser.add_argument("--max_per_video", type=int, default=80, help="每部影片最多抽取張數 (建議 60~80 張)")
    parser.add_argument("--config", type=str, default="configs/config.yaml", help="設定檔")

    args = parser.parse_args()

    cfg_path = ROOT_DIR / args.config
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    input_path = ROOT_DIR / args.input_dir
    train_videos = list(input_path.glob("train_*.mp4")) + list(input_path.glob("train_*.mkv"))

    if not train_videos:
        print(f"[提示] 在 {input_path} 下找不到 train_*.mp4 影片。")
        print("請先將 OBS 錄影檔放入 data/ 資料夾，並執行 `python src/video_manager.py` 進行重命名規格化。")
        return

    out_path = ROOT_DIR / args.output_dir
    total_saved = 0
    for v_path in train_videos:
        total_saved += extract_frames_for_training(
            video_path=v_path,
            output_dir=out_path,
            roi_config=cfg.get("roi"),
            sample_interval=args.interval,
            max_frames=args.max_per_video
        )

    print("\n" + "=" * 60)
    print(f"  抽幀作業完成！共累積 {total_saved} 張高品質訓練候選圖片。")
    print(f"  圖片儲存位置: {out_path}")
    print("  下一步：可以使用 Labelme 或 Roboflow 將標籤標為 early, perfect, late！")
    print("=" * 60)

if __name__ == "__main__":
    main()
