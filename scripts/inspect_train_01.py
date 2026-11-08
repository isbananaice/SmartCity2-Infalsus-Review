import cv2
import os
from pathlib import Path

video_path = "data/videos/train_01.mp4"
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print(f"Failed to open {video_path}")
    exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
duration = frames / fps if fps > 0 else 0

print(f"Video: {video_path}")
print(f"Resolution: {w}x{h}")
print(f"FPS: {fps}")
print(f"Total Frames: {frames}")
print(f"Duration: {duration:.2f}s ({int(duration//60)}m {int(duration%60)}s)")

# Sample some frames across the video and save them to inspect_frames/
out_dir = Path("data/inspect_frames")
out_dir.mkdir(parents=True, exist_ok=True)

# Sample 10 frames evenly spaced throughout the song
sample_times = [10, 30, 50, 70, 90, 110, 130, 150, 170, 190]
for t in sample_times:
    if t < duration:
        frame_idx = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            out_file = out_dir / f"frame_t{t:03d}s.jpg"
            cv2.imwrite(str(out_file), frame)
            # Also save ROI crop
            # Default ROI: y from 0.55 to 0.98, x from 0.05 to 0.95
            ymin, ymax = int(0.55 * h), int(0.98 * h)
            xmin, xmax = int(0.05 * w), int(0.95 * w)
            roi = frame[ymin:ymax, xmin:xmax]
            cv2.imwrite(str(out_dir / f"roi_t{t:03d}s.jpg"), roi)

cap.release()
print(f"Saved sample frames to {out_dir}")

