import cv2
import os
from pathlib import Path
from typing import Dict, Any, Generator, Tuple

class VideoProcessor:
    """處理 In Falsus 遊玩影片之影格讀取、資訊解析與 ROI 裁切"""

    def __init__(self, video_path: str, roi_config: Dict[str, Any] = None):
        self.video_path = video_path
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"找不到影片檔案: {video_path}")
        
        self.roi_config = roi_config or {
            "crop": {"ymin": 0.55, "ymax": 0.98, "xmin": 0.05, "xmax": 0.95}
        }
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"無法打開影片: {video_path}")

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 60.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_seconds = self.total_frames / self.fps if self.fps > 0 else 0

    def get_info(self) -> Dict[str, Any]:
        """取得影片基礎元資料"""
        return {
            "path": self.video_path,
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 2),
            "total_frames": self.total_frames,
            "duration_sec": round(self.duration_seconds, 2),
            "duration_formatted": f"{int(self.duration_seconds // 60):02d}:{int(self.duration_seconds % 60):02d}"
        }

    def crop_roi(self, frame):
        """依據設定裁切出判定線與按鍵區域 ROI"""
        crop = self.roi_config.get("crop", {})
        ymin = int(crop.get("ymin", 0.55) * self.height)
        ymax = int(crop.get("ymax", 0.98) * self.height)
        xmin = int(crop.get("xmin", 0.05) * self.width)
        xmax = int(crop.get("xmax", 0.95) * self.width)
        return frame[ymin:ymax, xmin:xmax]

    def frame_generator(self, start_sec: float = 0.0, end_sec: float = None, step: int = 1) -> Generator[Tuple[int, float, Any, Any], None, None]:
        """
        逐幀產生器
        回傳: (frame_idx, timestamp_sec, original_frame, roi_frame)
        """
        start_frame = int(start_sec * self.fps)
        end_frame = int(end_sec * self.fps) if end_sec else self.total_frames
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        current_frame = start_frame

        while current_frame < end_frame:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            if (current_frame - start_frame) % step == 0:
                timestamp = current_frame / self.fps
                roi = self.crop_roi(frame)
                yield current_frame, timestamp, frame, roi

            current_frame += 1

    def sample_frames_for_annotation(self, output_dir: str, sample_interval_frames: int = 30, max_frames: int = 500):
        """從影片抽幀以供 YOLO 標註訓練集使用"""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        for f_idx, timestamp, frame, roi in self.frame_generator(step=sample_interval_frames):
            if saved_count >= max_frames:
                break
            
            # 儲存 ROI 圖片
            file_name = f"frame_{f_idx:06d}_t{timestamp:.2f}.jpg"
            cv2.imwrite(str(out_path / file_name), roi)
            saved_count += 1
            
        print(f"[抽幀完成] 已儲存 {saved_count} 張圖片至 {output_dir}")

    def close(self):
        if self.cap.isOpened():
            self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

