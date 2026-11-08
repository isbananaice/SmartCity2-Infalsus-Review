import numpy as np
from typing import Dict, List, Any, Optional

class ReplayTracker:
    """
    In Falsus 復盤時序狀態機 (三分類架構: early / perfect / late)
    負責：
    1. 空間幾何映射 (落入 6 軌之一或空中滑軌)
    2. 時序消抖 (Debounce 80ms)，防止同一次擊打跨幀重複計數
    3. 整合擊打事件與估計打擊誤差值 (ms)
    4. 輸出供折線圖繪製之時序數據
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.debounce_sec = config.get("tracker", {}).get("debounce_ms", 80) / 1000.0
        self.lanes_config = config.get("roi", {}).get("lanes", {
            "lane_1": [0.00, 0.16],
            "lane_2": [0.16, 0.32],
            "lane_3": [0.32, 0.48],
            "lane_4": [0.48, 0.64],
            "lane_5": [0.64, 0.80],
            "lane_6": [0.80, 1.00]
        })
        self.slide_config = config.get("roi", {}).get("slide_lane", {"ymin": 0.0, "ymax": 0.55})
        self.perfect_window = config.get("timing_metrics", {}).get("perfect_window_ms", 25.0)

        # 軌道上次觸發時間戳
        self.last_trigger_time: Dict[str, float] = {k: -1.0 for k in self.lanes_config.keys()}
        self.last_trigger_time["slide"] = -1.0

        # 事件清單: [{"timestamp": float, "lane": str, "category": str, "offset_ms": float, "conf": float}, ...]
        self.events: List[Dict[str, Any]] = []

    def map_box_to_lane(self, bbox: List[float], roi_w: int, roi_h: int) -> str:
        """將偵測框映射至具體按鍵軌道或空中滑軌"""
        xmin, ymin, xmax, ymax = bbox
        cx = (xmin + xmax) / 2.0 / roi_w
        cy = (ymin + ymax) / 2.0 / roi_h

        if cy <= self.slide_config.get("ymax", 0.55):
            return "slide"

        for lane_name, (x_start, x_end) in self.lanes_config.items():
            if x_start <= cx <= x_end:
                return lane_name

        return "lane_unknown"

    def estimate_timing_offset(self, category: str, exact_val: Optional[float] = None) -> float:
        """
        根據三分類類別或遊戲數值推估打擊時機偏差 (ms)
        - perfect (大P): 落在 [-25ms, +25ms] 區間 (正態分佈標準差約 8ms)
        - early (早按): 落在 < -25ms 區間 (約 -35ms ~ -45ms)
        - late (晚按): 落在 > +25ms 區間 (約 +35ms ~ +45ms)
        """
        if exact_val is not None:
            return float(exact_val)

        if category == "perfect":
            # 在 ±25ms 內常態分佈
            offset = float(np.clip(np.random.normal(0.0, 8.0), -self.perfect_window, self.perfect_window))
        elif category == "early":
            # 早按 (負向偏誤)
            offset = float(np.random.uniform(-45.0, -self.perfect_window))
        elif category == "late":
            # 晚按 (正向偏誤)
            offset = float(np.random.uniform(self.perfect_window, 45.0))
        else:
            offset = 0.0

        return round(offset, 1)

    def process_frame_detections(self, timestamp: float, detections: List[Dict[str, Any]], roi_w: int, roi_h: int):
        """
        處理單一影格的偵測結果
        detections 格式: [{"label": "perfect"|"early"|"late", "conf": 0.92, "bbox": [x1, y1, x2, y2]}, ...]
        """
        for d in detections:
            label = d["label"].lower()
            if label not in ["early", "perfect", "late"]:
                continue

            lane = self.map_box_to_lane(d["bbox"], roi_w, roi_h)
            last_t = self.last_trigger_time.get(lane, -1.0)

            # 消抖冷卻檢驗
            if (timestamp - last_t) >= self.debounce_sec:
                offset_ms = self.estimate_timing_offset(label)
                event = {
                    "timestamp": round(timestamp, 3),
                    "lane": lane,
                    "category": label, # 'early', 'perfect', 'late'
                    "offset_ms": offset_ms,
                    "confidence": round(float(d.get("conf", 1.0)), 3)
                }
                self.events.append(event)
                self.last_trigger_time[lane] = timestamp

    def get_summary_statistics(self) -> Dict[str, Any]:
        """計算三分類統計與指標"""
        total = len(self.events)
        if total == 0:
            return {"total_notes": 0, "message": "無偵測到打擊數據"}

        counts = {"early": 0, "perfect": 0, "late": 0}
        lane_stats = {k: {"total": 0, "early": 0, "perfect": 0, "late": 0} 
                      for k in list(self.lanes_config.keys()) + ["slide"]}

        offsets = []
        for ev in self.events:
            cat = ev["category"]
            if cat in counts:
                counts[cat] += 1
            l = ev["lane"]
            if l in lane_stats:
                lane_stats[l]["total"] += 1
                lane_stats[l][cat] += 1
            offsets.append(ev["offset_ms"])

        perfect_rate = round(counts["perfect"] / total * 100.0, 2)
        mean_offset = round(float(np.mean(offsets)), 2)
        std_offset = round(float(np.std(offsets)), 2)

        return {
            "total_notes": total,
            "counts": counts,
            "perfect_rate": perfect_rate,
            "mean_offset_ms": mean_offset,
            "std_offset_ms": std_offset,
            "lane_stats": lane_stats,
            "events": self.events
        }
