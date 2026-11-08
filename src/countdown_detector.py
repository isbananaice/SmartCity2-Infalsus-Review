import cv2
import numpy as np
from typing import Tuple, Dict, Any

class CountdownDetector:
    """
    In Falsus 歌曲開始與前導畫面偵測器
    純粹依賴畫面核心特徵：
    1. 開場 CONNECT / 卡牌動畫淡出時刻 (中央區域亮度回落)
    2. 底部 6 軌判定線展開亮起時刻
    (已徹底移除左上角計分板 ROI 依賴，避免座標偏移或卡片技能加分干擾)
    """

    def __init__(self, fps: float = 60.0):
        self.fps = fps
        # 畫面中心區域 (偵測 CONNECT 動畫與卡牌退場)
        self.center_roi_norm = {"ymin": 0.30, "ymax": 0.65, "xmin": 0.35, "xmax": 0.65}
        # 底部 6 軌展開檢測區域
        self.track_roi_norm = {"ymin": 0.65, "ymax": 0.85, "xmin": 0.20, "xmax": 0.80}

    def detect_song_start_time(self, video_path: str, max_search_sec: float = 20.0) -> Tuple[float, Dict[str, Any]]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[警告] 無法讀取影片: {video_path}")
            return 0.0, {"method": "fallback", "detected": False}

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
        max_search_frames = int(min(max_search_sec * self.fps, cap.get(cv2.CAP_PROP_FRAME_COUNT)))

        cy_min, cy_max = int(self.center_roi_norm["ymin"] * height), int(self.center_roi_norm["ymax"] * height)
        cx_min, cx_max = int(self.center_roi_norm["xmin"] * width), int(self.center_roi_norm["xmax"] * width)

        ty_min, ty_max = int(self.track_roi_norm["ymin"] * height), int(self.track_roi_norm["ymax"] * height)
        tx_min, tx_max = int(self.track_roi_norm["xmin"] * width), int(self.track_roi_norm["xmax"] * width)

        step = max(1, int(self.fps // 10)) # 每 0.1 秒取樣一幀
        timeline = []

        frame_idx = 0
        while frame_idx < max_search_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            current_time = frame_idx / self.fps
            center_crop = frame[cy_min:cy_max, cx_min:cx_max]
            track_crop = frame[ty_min:ty_max, tx_min:tx_max]

            c_mean = float(cv2.mean(cv2.cvtColor(center_crop, cv2.COLOR_BGR2GRAY))[0])
            t_mean = float(cv2.mean(cv2.cvtColor(track_crop, cv2.COLOR_BGR2GRAY))[0])

            timeline.append({
                "time": current_time,
                "center_mean": c_mean,
                "track_mean": t_mean
            })

            frame_idx += step

        cap.release()

        # 1. 偵測開場 CONNECT / 角色卡牌淡出瞬間 (中央亮度由 >75 顯著回落至 <65)
        connect_end_time = None
        for i in range(len(timeline) - 1):
            curr_c = timeline[i]["center_mean"]
            next_c = timeline[i+1]["center_mean"]
            if timeline[i]["time"] >= 2.5: # 略過開頭讀取過場
                if curr_c > 75.0 and next_c <= 65.0:
                    connect_end_time = timeline[i+1]["time"]
                    break

        if connect_end_time is not None:
            return round(connect_end_time, 2), {
                "method": "connect_screen_fadeout",
                "detected": True,
                "start_time_sec": round(connect_end_time, 2)
            }

        # 2. 備案：若無 CONNECT 動畫，偵測底部 6 軌亮起展開時刻
        for item in timeline:
            if item["time"] >= 1.5 and item["track_mean"] > 40.0:
                return round(item["time"], 2), {
                    "method": "track_activation",
                    "detected": True,
                    "start_time_sec": round(item["time"], 2)
                }

        return 0.0, {"method": "default_zero", "detected": False, "start_time_sec": 0.0}
