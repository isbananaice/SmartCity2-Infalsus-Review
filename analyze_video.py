import argparse
import sys
import os
from pathlib import Path
import yaml
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, total=None, desc=""):
        return iterable

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.video_utils import VideoProcessor
from src.countdown_detector import CountdownDetector
from src.detector import InFalsusDetector
from src.tracker import ReplayTracker
from src.report_generator import ReportGenerator

def main():
    parser = argparse.ArgumentParser(description="In Falsus 影片復盤分析系統 (自動倒數辨識 + YOLOv11 + 時序狀態機)")
    parser.add_argument("--video", type=str, help="In Falsus 遊玩錄影路徑 (.mp4 / .mkv)")
    parser.add_argument("--weights", type=str, default="models/yolov11_infalsus_best.pt", help="YOLO 權重檔案路徑")
    parser.add_argument("--config", type=str, default="configs/config.yaml", help="設定檔路徑")
    parser.add_argument("--step", type=int, default=1, help="影格步長 (預設逐幀分析=1)")
    parser.add_argument("--demo", action="store_true", help="執行示範流程 (自動模擬生成報表)")

    args = parser.parse_args()

    # 讀取設定檔
    config_path = ROOT_DIR / args.config
    if not config_path.exists():
        print(f"[錯誤] 找不到設定檔: {config_path}")
        return
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if args.demo or not args.video:
        print("=" * 60)
        print("  In Falsus 復盤系統 - 示範模式 (Demo Pipeline)")
        print("=" * 60)
        video_info = {
            "path": "demo_gameplay_preview.mp4",
            "duration_formatted": "02:15",
            "fps": 60.0,
            "total_frames": 8100,
            "width": 1920,
            "height": 1080
        }
        tracker = ReplayTracker(config)
        import numpy as np
        np.random.seed(101)
        t = 0.5
        while t < 135.0:
            if 35 <= t <= 55:
                cat = np.random.choice(["perfect", "late", "early"], p=[0.30, 0.60, 0.10])
            elif 85 <= t <= 105:
                cat = np.random.choice(["perfect", "early", "late"], p=[0.30, 0.60, 0.10])
            else:
                cat = np.random.choice(["perfect", "early", "late"], p=[0.82, 0.09, 0.09])
            
            lx = np.random.uniform(50, 590)
            tracker.process_frame_detections(
                timestamp=t,
                detections=[{"label": cat, "conf": 0.95, "bbox": [lx, 150, lx + 45, 200]}],
                roi_w=640,
                roi_h=250
            )
            t += np.random.uniform(0.12, 0.32)

        stats = tracker.get_summary_statistics()
        reporter = ReportGenerator(config)
        outs = reporter.generate(video_info, stats)
        print("\n[完成] 示範復盤報告已產出：")
        print(f"  - 時序折線圖: {outs['chart']}")
        print(f"  - 網頁儀表板: {outs['html']}")
        print(f"  - 數據統計:   {outs['json']}")
        return

    # 正式影片分析模式
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[錯誤] 找不到指定影片: {video_path}")
        return

    print("=" * 60)
    print(f"  開始分析 In Falsus 遊玩影片: {video_path.name}")
    print("=" * 60)

    # 1. 執行畫面中間倒數偵測 (自動校準歌曲真正開始的時間)
    print("[階段 1/4] 掃描開頭畫面，偵測畫面中間倒數 (3, 2, 1) 與軌道啟動...")
    cd_detector = CountdownDetector()
    song_start_sec, cd_meta = cd_detector.detect_song_start_time(str(video_path))
    print(f"  => 歌曲正式開始時間: {song_start_sec:.2f} 秒 (判定依據: {cd_meta['method']})")
    print(f"  => 自動略過前導 {song_start_sec:.2f} 秒的非遊玩畫面，將時序軸歸零對齊")

    # 2. 初始化影片處理與 ROI
    video_proc = VideoProcessor(str(video_path), roi_config=config.get("roi"))
    video_info = video_proc.get_info()
    video_info["song_start_sec"] = song_start_sec

    # 3. 初始化 YOLO 偵測器與時序狀態機
    print("\n[階段 2/4] 初始化 YOLOv11 偵測模型與時序狀態機...")
    detector = InFalsusDetector(
        weights_path=args.weights,
        conf_threshold=config.get("model", {}).get("conf_threshold", 0.4),
        device=config.get("model", {}).get("device", "auto")
    )
    tracker = ReplayTracker(config)

    # 4. 逐幀解碼與時序推論 (從歌曲開始時間開始)
    total_frames_to_process = int((video_proc.total_frames - int(song_start_sec * video_proc.fps)) // args.step)
    print(f"\n[階段 3/4] 逐幀解碼與即時推論 (共約 {total_frames_to_process} 幀)...")

    pbar = tqdm(
        video_proc.frame_generator(start_sec=song_start_sec, step=args.step),
        total=total_frames_to_process,
        desc="分析進度"
    )

    for f_idx, video_timestamp, frame, roi in pbar:
        roi_h, roi_w = roi.shape[:2]
        # 相對於歌曲開始的精確秒數 (使折線圖 00:00 精準對齊第一拍)
        song_time = video_timestamp - song_start_sec
        detections = detector.detect_roi(roi)
        if detections:
            tracker.process_frame_detections(song_time, detections, roi_w, roi_h)

    # 5. 匯總分析與產出視覺化報表
    print("\n[階段 4/4] 匯總統計並生成折線圖與復盤儀表板...")
    stats = tracker.get_summary_statistics()
    reporter = ReportGenerator(config)
    outs = reporter.generate(video_info, stats)

    print("\n" + "=" * 60)
    print("  In Falsus 復盤報告生成完成！")
    print(f"  - 歌曲開始校準點: {song_start_sec:.2f}s")
    print(f"  - 大P達成率 (Perfect Rate): {stats.get('perfect_rate', 0)}%")
    print(f"  - 總打擊音符數: {stats.get('total_notes', 0)}")
    print(f"  - 平均時序偏移: {stats.get('mean_offset_ms', 0)} ms")
    print(f"  - 時序折線圖:   {outs['chart']}")
    print(f"  - 網頁復盤報告: {outs['html']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
