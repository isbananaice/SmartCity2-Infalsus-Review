import cv2
import os
from pathlib import Path

cap = cv2.VideoCapture('data/videos/train_01.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)

out_dir = Path('data/inspect_frames/feedback_check')
out_dir.mkdir(parents=True, exist_ok=True)

# Let's save frames between 10s and 13s, every 5 frames
for f_i in range(int(10*fps), int(13*fps), 5):
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_i)
    ret, frame = cap.read()
    if ret:
        t = f_i / fps
        crop = frame[580:880, 350:1570]
        cv2.imwrite(str(out_dir / f'jline_t{t:.2f}s.jpg'), crop)

cap.release()
print('Done saving feedback check frames')

