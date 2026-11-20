"""
In Falsus AI 復盤診斷系統 - 歌曲結尾與結算畫面偵測器 (Ending Detector)
偵測全曲結束時刻：
1. 結尾全螢幕出現 CLEARED / FAILED 大字閃爍動畫
2. 結算畫面 (DIVE RESULT / DIVE CLEARED / DIVE FAILED) 出現
3. 底部 6 軌打擊線徹底熄滅退場 (淡出黑屏過場)

在偵測到結尾時立即終止打擊判定與時序統計，徹底杜絕結算畫面動畫造成的誤判。
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any


class EndingDetector:
    def __init__(self, fps: float = 60.0):
        self.fps = fps

    def detect_song_end_time(self, video_path: str, song_start_sec: float = 0.0) -> Tuple[float, Dict[str, Any]]:
        """
        偵測歌曲結尾時刻 (秒數)
        返回: (video_end_sec, metadata)
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 9999.0, {"detected": False, "reason": "video_open_failed"}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
        duration = total_frames / self.fps

        # 歌曲至少持續 40 秒，自 min(duration-35s, song_start_sec + 40s) 開始向後掃描
        start_sec = max(song_start_sec + 40.0, duration - 35.0)
        cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)

        curr_frame = int(start_sec * self.fps)
        end_time_sec = None
        detect_reason = None
        dark_track_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            curr_frame += 1
            # 每 6 幀 (約 0.1 秒) 檢測一次
            if curr_frame % 6 != 0:
                continue

            t_sec = curr_frame / self.fps
            h, w = frame.shape[:2]

            # 1. 底部軌道判定線活躍度 (y: 83% ~ 87%, x: 30% ~ 70%)
            track_roi = frame[int(h * 0.83):int(h * 0.87), int(w * 0.30):int(w * 0.70)]
            track_mean = float(cv2.mean(track_roi)[0])

            # 2. 左上角 DIVE RESULT 結算文字標題 (y: 2% ~ 8%, x: 10% ~ 25%)
            tl_roi = frame[int(h * 0.02):int(h * 0.08), int(w * 0.10):int(w * 0.25)]
            tl_mean = float(cv2.mean(tl_roi)[0])

            # 3. 中央區域 CLEARED / FAILED 大字閃爍 (y: 35% ~ 65%, x: 20% ~ 80%)
            center_roi = frame[int(h * 0.35):int(h * 0.65), int(w * 0.20):int(w * 0.80)]
            gray_center = cv2.cvtColor(center_roi, cv2.COLOR_BGR2GRAY)
            bright_pixels = int(np.count_nonzero(gray_center > 220))

            # 判定準則：
            # A: 軌道已熄滅 (track_mean < 45) 且 (中央出現大量白光 CLEARED 閃爍 或 左上角出現 DIVE RESULT)
            if track_mean < 45.0 and (bright_pixels > 15000 or tl_mean > 70.0):
                end_time_sec = t_sec
                detect_reason = f"Ending screen detected (track={track_mean:.1f}, bright={bright_pixels}, tl={tl_mean:.1f})"
                break

            # B: 軌道持續熄滅超過 0.5 秒 (歌曲結束淡出黑屏過場)
            if track_mean < 25.0:
                dark_track_count += 1
                if dark_track_count >= 5: # 0.5s
                    end_time_sec = t_sec - 0.4
                    detect_reason = "Track faded out to black at song end"
                    break
            else:
                dark_track_count = 0

        cap.release()

        if end_time_sec is not None:
            song_duration = max(10.0, end_time_sec - song_start_sec)
            return round(end_time_sec, 2), {
                "detected": True,
                "video_end_sec": round(end_time_sec, 2),
                "song_duration_sec": round(song_duration, 2),
                "reason": detect_reason
            }

        return round(duration, 2), {
            "detected": False,
            "video_end_sec": round(duration, 2),
            "song_duration_sec": round(duration - song_start_sec, 2)
        }
