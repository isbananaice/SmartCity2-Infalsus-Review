import os
import re
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

class VideoManager:
    """
    OBS 錄影檔管理與自動規格化重命名工具
    功能：
    1. 掃描 data/ 目錄下的 OBS 預設檔名影片 (如: 2026-11-07 19-45-00.mp4)
    2. 自動將其歸類並重命名為標準格式 (train_01.mp4, train_02.mp4, test_01.mp4 等)
    3. 維護 data/manifest.json 紀錄對應表，確保可溯源原始錄影檔
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.videos_dir = self.data_dir / "videos"
        self.manifest_file = self.data_dir / "manifest.json"

        # 確保目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)

        self.video_extensions = {".mp4", ".mkv", ".mov", ".avi"}

    def scan_raw_videos(self) -> List[Path]:
        """掃描 data/ 及 data/raw/ 下所有尚未歸類的原始影片"""
        found = []
        # 同時搜尋 data 根目錄與 data/raw
        for search_path in [self.data_dir, self.raw_dir]:
            for p in search_path.glob("*"):
                if p.is_file() and p.suffix.lower() in self.video_extensions:
                    # 排除已是 train_xx 或 test_xx 的檔案
                    if not (p.stem.startswith("train_") or p.stem.startswith("test_")):
                        found.append(p)
        # 依檔案修改時間排序
        found.sort(key=lambda x: x.stat().st_mtime)
        return found

    def organize_videos(self, train_count: int = 4, test_count: int = 2) -> Dict[str, Any]:
        """
        將原始影片依序重命名為 train_01.mp4, test_01.mp4 等標準規格
        """
        raw_videos = self.scan_raw_videos()
        if not raw_videos:
            print("[VideoManager] data/ 目錄下目前沒有找到待處理的原始影片。")
            return {"status": "empty", "manifest": {}}

        print(f"[VideoManager] 偵測到 {len(raw_videos)} 個原始影片檔案。")

        manifest = {}
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = {}

        train_idx = 1
        test_idx = 1
        processed_files = []

        for idx, src_path in enumerate(raw_videos):
            ext = src_path.suffix.lower()
            
            # 分配角色 (先滿足 train_count，其餘或後續分給 test)
            if train_idx <= train_count:
                new_name = f"train_{train_idx:02d}{ext}"
                category = "train"
                train_idx += 1
            else:
                new_name = f"test_{test_idx:02d}{ext}"
                category = "test"
                test_idx += 1

            dst_path = self.videos_dir / new_name

            # 移動並更名
            shutil.move(str(src_path), str(dst_path))

            manifest[new_name] = {
                "original_filename": src_path.name,
                "current_path": str(dst_path.relative_to(self.data_dir.parent)),
                "category": category,
                "file_size_mb": round(dst_path.stat().st_size / (1024 * 1024), 2),
                "timestamp_modified": dst_path.stat().st_mtime
            }
            processed_files.append((src_path.name, new_name))
            print(f"  [重命名] {src_path.name}  ->  {new_name} ({category})")

        # 寫入清單檔案
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"[VideoManager 完成] 已規格化 {len(processed_files)} 部影片，對照表已儲存至: {self.manifest_file}")
        return {"status": "success", "processed_count": len(processed_files), "manifest": manifest}

if __name__ == "__main__":
    vm = VideoManager()
    vm.organize_videos()

