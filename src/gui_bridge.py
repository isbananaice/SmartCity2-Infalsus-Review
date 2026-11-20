"""
In Falsus AI 復盤診斷系統 - 本地桌面 API 橋接器 (GUI Bridge)
純本機運行，無需網路伺服器、無需開放 Port、完全離線工作。
直接透過 pywebview JS API 與前端互動。
"""

import os
import sys
import json
import shutil
import threading
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

VIDEOS_DIR = ROOT_DIR / "data" / "videos"
REPORTS_DIR = ROOT_DIR / "reports"
STATIC_DIR = Path(__file__).resolve().parent / "gui_static"

VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def get_config():
    config_path = ROOT_DIR / "configs" / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


class LocalReplayBridge:
    """
    本地復盤桌面應用核心橋接器
    提供前端 JavaScript 調用的所有原生功能
    """
    def __init__(self, window=None):
        self._window = window
        self.analysis_jobs: Dict[str, Dict[str, Any]] = {}
        self._cached_sys_info = None

    def set_window(self, window):
        self._window = window

    # ==========================================
    # 1. 影片列表與復盤數據獲取 (完全讀取本地檔案)
    # ==========================================
    def get_videos(self) -> Dict[str, Any]:
        """列出 data/videos 目錄下所有影片，並檢查是否已有分析結果"""
        videos = []
        for ext in ["*.mp4", "*.mkv", "*.avi", "*.mov"]:
            for vfile in sorted(VIDEOS_DIR.glob(ext)):
                vid = vfile.stem
                stats_path = REPORTS_DIR / f"{vid}_stats.json"
                analyzed = stats_path.exists()
                stats_summary = {}
                if analyzed:
                    try:
                        with open(stats_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            stats_summary = {
                                "perfect_rate": data.get("perfect_rate", 0),
                                "total_notes": data.get("total_notes", 0),
                                "mean_offset_ms": data.get("mean_offset_ms", 0),
                                "std_offset_ms": data.get("std_offset_ms", 0),
                                "counts": data.get("counts", {}),
                                "lane_stats": data.get("lane_stats", {})
                            }
                    except Exception:
                        pass

                videos.append({
                    "id": vid,
                    "filename": vfile.name,
                    "size_mb": round(vfile.stat().st_size / (1024 * 1024), 2),
                    "analyzed": analyzed,
                    "stats": stats_summary
                })
        return {"videos": videos}

    def get_replay_data(self, video_id: str) -> Dict[str, Any]:
        """
        獲取指定影片的完整復盤數據 (包含音符事件、滾動平均數據、歌曲對齊秒數等)
        若已有分析結果則直接套用！
        """
        stats_path = REPORTS_DIR / f"{video_id}_stats.json"
        events_path = REPORTS_DIR / f"{video_id}_events.json"

        if not stats_path.exists():
            return {
                "id": video_id,
                "analyzed": False,
                "message": "尚未進行 AI 復盤分析，請在左側功能表點擊 [開始分析]"
            }

        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)

        events = []
        if events_path.exists():
            try:
                with open(events_path, "r", encoding="utf-8") as f:
                    events = json.load(f)
            except Exception:
                events = []

        # 計算滾動平均走勢 (Rolling Mean Offset)
        events.sort(key=lambda x: x["timestamp"])
        t_max = max([e["timestamp"] for e in events]) if events else 120.0
        rolling_series = []

        sample_times = [round(t * 0.5, 2) for t in range(int(t_max * 2) + 1)]
        for st in sample_times:
            window_events = [e["offset_ms"] for e in events if abs(e["timestamp"] - st) <= 1.5]
            if window_events:
                mean_val = float(sum(window_events) / len(window_events))
            else:
                mean_val = 0.0
            rolling_series.append({
                "timestamp": st,
                "mean_offset_ms": round(mean_val, 2)
            })

        vinfo = stats.get("video_info", {})
        return {
            "id": video_id,
            "analyzed": True,
            "video_info": vinfo,
            "song_start_sec": vinfo.get("song_start_sec", 3.0),
            "stats": {
                "total_notes": stats.get("total_notes", len(events)),
                "perfect_rate": stats.get("perfect_rate", 0),
                "mean_offset_ms": stats.get("mean_offset_ms", 0),
                "std_offset_ms": stats.get("std_offset_ms", 0),
                "counts": stats.get("counts", {}),
                "lane_stats": stats.get("lane_stats", {})
            },
            "rolling_series": rolling_series,
            "events": events
        }

    # ==========================================
    # 2. 原生檔案選擇與匯入 (完全本地複製，不需 HTTP 傳輸)
    # ==========================================
    def select_and_import_video(self) -> Dict[str, Any]:
        """打開 Windows 原生檔案選擇對話框匯入影片"""
        if not self._window:
            return {"success": False, "message": "視窗尚未就緒"}

        import webview
        file_types = ("影片檔案 (*.mp4;*.mkv;*.avi;*.mov)", "所有檔案 (*.*)")
        result = self._window.create_file_dialog(
            dialog_type=webview.FileDialog.OPEN,
            file_types=file_types
        )
        if not result or len(result) == 0:
            return {"success": False, "cancelled": True}

        chosen_path = Path(result[0])
        return self.import_local_video_file(str(chosen_path))

    def import_local_video_file(self, file_path_str: str) -> Dict[str, Any]:
        """將指定路徑之影片複製到 data/videos 目錄"""
        src_path = Path(file_path_str)
        if not src_path.exists():
            return {"success": False, "message": "找不到指定的檔案"}

        filename = src_path.name
        dst_path = VIDEOS_DIR / filename
        vid = src_path.stem

        if src_path.resolve() != dst_path.resolve():
            shutil.copy2(src_path, dst_path)

        stats_path = REPORTS_DIR / f"{vid}_stats.json"
        already_analyzed = stats_path.exists()

        return {
            "success": True,
            "id": vid,
            "filename": filename,
            "already_analyzed": already_analyzed,
            "message": "影片匯入成功！已直接套用既有分析報告" if already_analyzed else "影片匯入成功！請點擊 [開始分析] 進行 AI 復盤。"
        }

    # ==========================================
    # 3. 本地 YOLOv11 AI 推論復盤
    # ==========================================
    def start_analysis(self, video_id: str, step: int = 1) -> Dict[str, Any]:
        """啟動本地 AI 復盤分析線程"""
        target = None
        for ext in [".mp4", ".mkv", ".avi", ".mov"]:
            cand = VIDEOS_DIR / f"{video_id}{ext}"
            if cand.exists():
                target = cand
                break
        if not target:
            return {"status": "error", "message": "找不到欲分析的影片檔案"}

        if video_id in self.analysis_jobs and self.analysis_jobs[video_id].get("status") == "processing":
            return {"status": "processing", "message": "該影片已在分析中"}

        self.analysis_jobs[video_id] = {
            "status": "queued",
            "progress": 0,
            "log": "正在排隊開始分析...",
            "total_frames": 0,
            "processed_frames": 0
        }

        t = threading.Thread(
            target=self._run_analysis_worker,
            args=(target, video_id, step),
            daemon=True
        )
        t.start()

        return {"status": "started", "video_id": video_id}

    def _run_analysis_worker(self, video_path: Path, video_id: str, step: int = 1):
        """後台分析工作線程 (採用優化後的空間類別生命週期追蹤器)"""
        from src.video_utils import VideoProcessor
        from src.countdown_detector import CountdownDetector
        from src.detector import InFalsusDetector
        from src.tracker import ReplayTracker
        from src.report_generator import ReportGenerator

        job = self.analysis_jobs[video_id]
        job["status"] = "processing"
        job["progress"] = 5
        job["log"] = "正在進行開頭倒數偵測與歌曲對齊..."

        try:
            config = get_config()
            model_cfg = config.get("model", {})
            weights_path = str(ROOT_DIR / model_cfg.get("weights_path", "models/yolov11s_infalsus_ultimate.pt"))
            if not Path(weights_path).exists():
                weights_path = str(ROOT_DIR / "models" / "yolov11_infalsus_best.pt")

            cd_detector = CountdownDetector()
            song_start_sec, cd_meta = cd_detector.detect_song_start_time(str(video_path))
            job["song_start_sec"] = song_start_sec
            job["log"] = f"倒數校準完成：歌曲自 {song_start_sec:.2f}s 開始，正在初始化推論模型..."
            job["progress"] = 15

            video_proc = VideoProcessor(str(video_path), roi_config=config.get("roi"))
            video_info = video_proc.get_info()
            video_info["song_start_sec"] = song_start_sec

            detector = InFalsusDetector(
                weights_path=weights_path,
                conf_threshold=model_cfg.get("conf_threshold", 0.55),
                iou_threshold=model_cfg.get("iou_threshold", 0.45),
                device=model_cfg.get("device", "auto"),
                imgsz=model_cfg.get("input_size", 960),
                augment=model_cfg.get("augment", False)
            )
            tracker = ReplayTracker(config)

            total_frames = int((video_proc.total_frames - int(song_start_sec * video_proc.fps)) // step)
            job["total_frames"] = total_frames
            job["processed_frames"] = 0
            job["log"] = f"開始逐幀分析 (共 {total_frames} 幀)..."

            f_count = 0
            for f_idx, t_sec, frame, roi in video_proc.frame_generator(start_sec=song_start_sec, step=step):
                rel_time = t_sec - song_start_sec
                detections = detector.detect_roi(roi)
                if detections:
                    tracker.process_frame_detections(
                        timestamp=rel_time,
                        detections=detections,
                        roi_w=roi.shape[1],
                        roi_h=roi.shape[0]
                    )
                f_count += 1
                if f_count % 300 == 0:
                    prog = 15 + int((f_count / max(1, total_frames)) * 75)
                    job["progress"] = min(90, prog)
                    job["processed_frames"] = f_count
                    job["log"] = f"分析中: {f_count}/{total_frames} 幀 ({job['progress']}%)"

            job["log"] = "正在匯出分析報告與時序數據..."
            job["progress"] = 92

            stats = tracker.get_summary_statistics()
            events = stats.get("events", [])

            # 儲存 events.json
            events_path = REPORTS_DIR / f"{video_id}_events.json"
            with open(events_path, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False)

            # 儲存 stats.json
            stats_path = REPORTS_DIR / f"{video_id}_stats.json"
            export_stats = {k: v for k, v in stats.items() if k != "events"}
            export_stats["video_info"] = video_info
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(export_stats, f, ensure_ascii=False, indent=2)

            # 產出視覺化與 HTML 報告
            report_gen = ReportGenerator(config)
            chart_path = REPORTS_DIR / f"{video_id}_timeline.png"
            html_path = REPORTS_DIR / f"{video_id}_report.html"
            report_gen.visualizer.plot_timing_timeline(events, str(chart_path), title=f"In Falsus 全曲時序分析 - {video_id}")
            report_gen._generate_html_report(video_info, stats, chart_filename=chart_path.name, output_file=html_path)

            job["progress"] = 100
            job["status"] = "completed"
            job["log"] = f"分析圓滿完成！大P達成率: {stats.get('perfect_rate', 0)}%"

        except Exception as e:
            job["status"] = "error"
            job["log"] = f"分析過程出錯: {str(e)}"

    def get_analysis_status(self, video_id: str) -> Dict[str, Any]:
        """查詢分析進度"""
        if video_id not in self.analysis_jobs:
            stats_path = REPORTS_DIR / f"{video_id}_stats.json"
            if stats_path.exists():
                return {"status": "completed", "progress": 100, "log": "已完成"}
            return {"status": "idle", "progress": 0, "log": "尚未分析"}
        return self.analysis_jobs[video_id]

    # ==========================================
    # 4. 檔案與報告管理
    # ==========================================
    def delete_analysis(self, video_id: str) -> Dict[str, Any]:
        """刪除指定影片的分析紀錄與快取"""
        for f in [
            REPORTS_DIR / f"{video_id}_stats.json",
            REPORTS_DIR / f"{video_id}_events.json",
            REPORTS_DIR / f"{video_id}_report.html",
            REPORTS_DIR / f"{video_id}_timeline.png"
        ]:
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass
        if video_id in self.analysis_jobs:
            del self.analysis_jobs[video_id]
        return {"success": True, "message": f"{video_id} 分析紀錄已刪除"}

    def delete_video(self, video_id: str) -> Dict[str, Any]:
        """刪除指定影片及其分析紀錄"""
        self.delete_analysis(video_id)
        for ext in [".mp4", ".mkv", ".avi", ".mov"]:
            vpath = VIDEOS_DIR / f"{video_id}{ext}"
            if vpath.exists():
                try:
                    vpath.unlink()
                except Exception:
                    pass
        return {"success": True, "message": f"{video_id} 影片檔案已刪除"}

    def open_html_report(self, video_id: str) -> Dict[str, Any]:
        """以系統預設瀏覽器打開本機 HTML 報告"""
        html_path = REPORTS_DIR / f"{video_id}_report.html"
        if html_path.exists():
            import webbrowser
            webbrowser.open(html_path.as_uri())
            return {"success": True}
        return {"success": False, "message": "尚未生成 HTML 報告"}

    def get_system_info(self) -> Dict[str, Any]:
        """獲取硬體加速與設定資訊 (具備快取以加速初始化)"""
        if self._cached_sys_info is not None:
            return self._cached_sys_info

        config = get_config()
        device_name = "CPU"
        cuda_avail = False
        try:
            import torch
            cuda_avail = torch.cuda.is_available()
            if cuda_avail:
                device_name = torch.cuda.get_device_name(0)
        except Exception:
            pass

        self._cached_sys_info = {
            "model": config.get("model", {}),
            "device": device_name,
            "cuda_available": cuda_avail,
            "perfect_window_ms": config.get("timing_metrics", {}).get("perfect_window_ms", 25.0)
        }
        return self._cached_sys_info
