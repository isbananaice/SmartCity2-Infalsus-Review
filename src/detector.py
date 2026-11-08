from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

class InFalsusDetector:
    """
    YOLOv11 推論封裝器
    支援:
    1. 載入 Ultralytics YOLO 模型 (.pt 權重)
    2. 自動判斷 GPU (CUDA) / CPU 模式
    3. ROI 影像批次/單張推論
    4. 當尚未訓練好權重時，提供 Mock/模擬模式以利端到端流程驗證
    """

    def __init__(self, weights_path: Optional[str] = None, conf_threshold: float = 0.4, device: str = "auto"):
        self.weights_path = weights_path
        self.conf_threshold = conf_threshold
        self.device = device
        self.model = None
        self.is_mock = False

        if weights_path and Path(weights_path).exists():
            try:
                from ultralytics import YOLO
                import torch
                
                if device == "auto":
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                
                print(f"[Detector] 正在載入模型: {weights_path} (裝置: {self.device})")
                self.model = YOLO(weights_path)
            except Exception as e:
                print(f"[Detector 警告] 載入模型失敗 ({e})，切換至模擬推論模式")
                self.is_mock = True
        else:
            if weights_path:
                print(f"[Detector 提示] 權重檔案尚未存在 ({weights_path})，將以展示模擬模式運行")
            self.is_mock = True

    def detect_roi(self, roi_image: np.ndarray) -> List[Dict[str, Any]]:
        """
        對 ROI 影像進行目標偵測
        回傳清單: [{"label": "perfect"|"early"|"late", "conf": float, "bbox": [x1, y1, x2, y2]}, ...]
        """
        if self.is_mock or self.model is None:
            # 模擬模式：回傳隨機或空偵測 (測試用)
            return self._mock_detect(roi_image)

        # 呼叫 YOLOv11 推論
        results = self.model.predict(
            source=roi_image,
            conf=self.conf_threshold,
            device=self.device,
            verbose=False
        )

        detections = []
        if len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                label = self.model.names.get(cls_id, str(cls_id)).lower()
                conf = float(box.conf[0].item())
                xyxy = [float(x) for x in box.xyxy[0].tolist()]

                # 過濾並正規化至三分類
                if label in ["0", "early"]:
                    norm_label = "early"
                elif label in ["1", "perfect"]:
                    norm_label = "perfect"
                elif label in ["2", "late"]:
                    norm_label = "late"
                else:
                    norm_label = label

                detections.append({
                    "label": norm_label,
                    "conf": conf,
                    "bbox": xyxy
                })

        return detections

    def _mock_detect(self, roi_image: np.ndarray) -> List[Dict[str, Any]]:
        """無模型權重時的輕量測試回傳"""
        h, w = roi_image.shape[:2]
        # 15% 機率產生一個判定框以利流程測試
        if np.random.rand() < 0.15:
            cat = np.random.choice(["perfect", "early", "late"], p=[0.7, 0.15, 0.15])
            x1 = np.random.uniform(20, w - 80)
            y1 = np.random.uniform(50, h - 50)
            return [{
                "label": cat,
                "conf": round(np.random.uniform(0.75, 0.98), 2),
                "bbox": [x1, y1, x1 + 60, y1 + 40]
            }]
        return []

