import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.countdown_detector import CountdownDetector

cd = CountdownDetector()
videos_dir = Path("data/videos")

print("=" * 60)
print("  掃描所有影片開場開始時間 (Countdown / Connect Fadeout)")
print("=" * 60)

for v in sorted(videos_dir.glob("*.mp4")):
    t, m = cd.detect_song_start_time(str(v))
    print(f"{v.name:15s} -> 開始時間: {t:5.2f}s  (依據: {m.get('method', 'unknown')})")
