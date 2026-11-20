import sys
import os
from pathlib import Path
import json
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.video_utils import VideoProcessor
from src.countdown_detector import CountdownDetector
from src.detector import InFalsusDetector
from src.tracker import ReplayTracker
from src.report_generator import ReportGenerator

def analyze_single_video(video_path: Path, output_prefix: str, config: dict, detector: InFalsusDetector):
    print("\n" + "=" * 60)
    print(f"  [批次分析] 開始處理: {video_path.name}")
    print("=" * 60)

    # 1. 偵測歌曲倒數與正式開始時間
    cd_detector = CountdownDetector()
    song_start_sec, cd_meta = cd_detector.detect_song_start_time(str(video_path))
    print(f"  - 歌曲正式開始時間: {song_start_sec:.2f} 秒 (依據: {cd_meta['method']})")

    # 2. 初始化影片處理器
    video_proc = VideoProcessor(str(video_path), roi_config=config.get("roi"))
    video_info = video_proc.get_info()
    video_info["song_start_sec"] = song_start_sec

    # 3. 初始化時序狀態機
    tracker = ReplayTracker(config)

    # 4. 逐幀推論
    total_frames = int((video_proc.total_frames - int(song_start_sec * video_proc.fps)))
    print(f"  - 逐幀推論中 (共 {total_frames} 幀)...")

    frame_count = 0
    for f_idx, t_sec, frame, roi in video_proc.frame_generator(start_sec=song_start_sec, step=1):
        rel_time = t_sec - song_start_sec
        detections = detector.detect_roi(roi)
        if detections:
            tracker.process_frame_detections(
                timestamp=rel_time,
                detections=detections,
                roi_w=roi.shape[1],
                roi_h=roi.shape[0]
            )
        frame_count += 1
        if frame_count % 1500 == 0:
            print(f"    進度: {frame_count}/{total_frames} 幀 ({(frame_count/total_frames*100):.1f}%)")

    # 5. 匯出成果
    stats = tracker.get_summary_statistics()
    report_gen = ReportGenerator(config)

    # 自訂產出路徑
    chart_path = ROOT_DIR / "reports" / f"{output_prefix}_timeline.png"
    json_path = ROOT_DIR / "reports" / f"{output_prefix}_stats.json"
    html_path = ROOT_DIR / "reports" / f"{output_prefix}_report.html"

    report_gen.visualizer.plot_timing_timeline(
        events=stats.get("events", []),
        output_path=str(chart_path),
        title=f"In Falsus 全曲時序折線散點圖 - {video_path.stem}"
    )

    export_stats = {k: v for k, v in stats.items() if k != "events"}
    export_stats["video_info"] = video_info
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export_stats, f, ensure_ascii=False, indent=2)

    report_gen._generate_html_report(video_info, stats, chart_filename=chart_path.name, output_file=html_path)

    print(f"\n[成功] {video_path.name} 分析完成！")
    print(f"  - 大P達成率: {stats.get('perfect_rate', 0)}%")
    print(f"  - 總打擊數:   {stats.get('total_notes', 0)}")
    print(f"  - 平均偏差:   {stats.get('mean_offset_ms', 0)} ms")
    print(f"  - 報表路徑:   {html_path}")
    return stats

def main():
    config_path = ROOT_DIR / "configs" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    model_cfg = config.get("model", {})
    weights_path = str(ROOT_DIR / model_cfg.get("weights_path", "models/yolov11s_infalsus_ultimate.pt"))
    if not Path(weights_path).exists():
        weights_path = str(ROOT_DIR / "models" / "yolov11_infalsus_best.pt")

    detector = InFalsusDetector(
        weights_path=weights_path,
        conf_threshold=model_cfg.get("conf_threshold", 0.55),
        iou_threshold=model_cfg.get("iou_threshold", 0.45),
        device=model_cfg.get("device", "cuda"),
        imgsz=model_cfg.get("input_size", 960),
        augment=model_cfg.get("augment", False)
    )

    videos = [
        (ROOT_DIR / "data" / "videos" / "test_01.mp4", "test_01"),
        (ROOT_DIR / "data" / "videos" / "test_02.mp4", "test_02")
    ]

    summary = {}
    for vpath, prefix in videos:
        if vpath.exists():
            summary[prefix] = analyze_single_video(vpath, prefix, config, detector)

    print("\n" + "=" * 60)
    print("  全部測試影片分析完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
