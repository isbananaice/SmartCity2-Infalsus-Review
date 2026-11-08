import sys
import os
from pathlib import Path

# 加入根目錄至 sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import numpy as np
from src.tracker import ReplayTracker
from src.visualizer import ReplayVisualizer
import yaml

with open(ROOT_DIR / 'configs' / 'config.yaml', 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

tracker = ReplayTracker(cfg)

# 模擬 2 分鐘的一首歌 (120 秒，約 500 個 notes)
np.random.seed(42)
t = 1.0
while t < 120.0:
    # 30-50s 遭遇密集段落，玩家偏晚 (late)
    # 70-90s 玩家心急搶拍，偏快 (early)
    if 30 <= t <= 50:
        cat = np.random.choice(['perfect', 'late', 'early'], p=[0.25, 0.65, 0.10])
    elif 70 <= t <= 90:
        cat = np.random.choice(['perfect', 'early', 'late'], p=[0.25, 0.65, 0.10])
    else:
        cat = np.random.choice(['perfect', 'early', 'late'], p=[0.85, 0.08, 0.07])
    
    lane_x = np.random.uniform(50, 590)
    tracker.process_frame_detections(
        timestamp=t,
        detections=[{'label': cat, 'conf': 0.92, 'bbox': [lane_x, 150, lane_x+40, 200]}],
        roi_w=640,
        roi_h=250
    )
    t += np.random.uniform(0.15, 0.35)

stats = tracker.get_summary_statistics()
print(f"Total notes processed: {stats['total_notes']}")
print(f"Classification Counts: {stats['counts']}")
print(f"Perfect Rate (大P率): {stats['perfect_rate']}%")
print(f"Mean Timing Offset: {stats['mean_offset_ms']} ms")

viz = ReplayVisualizer(perfect_window_ms=25.0)
out_img = ROOT_DIR / 'reports' / 'timing_timeline_sample.png'
viz.plot_timing_timeline(stats['events'], output_path=str(out_img))
print(f"Successfully generated {out_img}")
