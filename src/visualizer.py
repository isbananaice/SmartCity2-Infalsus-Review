import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import List, Dict, Any
import os

# 設定支援中文的字型相容
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ReplayVisualizer:
    """繪製 In Falsus 復盤專業分析圖表"""

    def __init__(self, perfect_window_ms: float = 25.0):
        self.perfect_window = perfect_window_ms

    def plot_timing_timeline(self, events: List[Dict[str, Any]], output_path: str = "reports/timing_timeline.png", title: str = "In Falsus 全曲打擊時機時序折線圖"):
        """
        繪製核心折線圖:
        - 橫軸: 歌曲時間 (秒或分:秒)
        - 縱軸: 玩家打擊時機偏差 (ms)
        - 標出 ±25ms 大P判定區間帶
        - 畫出打擊散點與平滑趨勢折線 (Rolling Mean)
        """
        if not events:
            print("[警告] 無事件資料可供繪圖")
            return

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df = pd.DataFrame(events)
        
        # 建立畫布
        fig, ax = plt.subplots(figsize=(14, 6), dpi=300)

        # 1. 繪製背景判定區間帶 (大P, Early, Late)
        time_min = df["timestamp"].min()
        time_max = df["timestamp"].max()
        time_pad = max(2.0, (time_max - time_min) * 0.02)
        x_range = [time_min - time_pad, time_max + time_pad]

        # 大P區間 (-25ms ~ +25ms)
        ax.axhspan(-self.perfect_window, self.perfect_window, color="#2ecc71", alpha=0.15, label=f"Perfect (大P區間 ±{int(self.perfect_window)}ms)")
        # 晚按區間 (> +25ms)
        ax.axhspan(self.perfect_window, 70, color="#e74c3c", alpha=0.08, label=f"Late (晚按 >+{int(self.perfect_window)}ms)")
        # 早按區間 (< -25ms)
        ax.axhspan(-70, -self.perfect_window, color="#3498db", alpha=0.08, label=f"Early (早按 <-{int(self.perfect_window)}ms)")
        # 零基準線 (Perfect Center)
        ax.axhline(0, color="#27ae60", linestyle="--", linewidth=1.2, alpha=0.7)

        # 2. 分類繪製散點
        early_df = df[df["category"] == "early"]
        perfect_df = df[df["category"] == "perfect"]
        late_df = df[df["category"] == "late"]

        ax.scatter(perfect_df["timestamp"], perfect_df["offset_ms"], c="#27ae60", s=28, alpha=0.65, edgecolors="none", label="Perfect 打擊點")
        ax.scatter(early_df["timestamp"], early_df["offset_ms"], c="#2980b9", marker="v", s=38, alpha=0.85, edgecolors="black", linewidth=0.5, label="Early 早按點")
        ax.scatter(late_df["timestamp"], late_df["offset_ms"], c="#c0392b", marker="^", s=38, alpha=0.85, edgecolors="black", linewidth=0.5, label="Late 晚按點")

        # 3. 繪製趨勢平滑折線 (5-Note 滾動平均)
        if len(df) >= 5:
            df_sorted = df.sort_values("timestamp").copy()
            df_sorted["rolling_mean"] = df_sorted["offset_ms"].rolling(window=7, min_periods=3, center=True).mean()
            ax.plot(df_sorted["timestamp"], df_sorted["rolling_mean"], color="#8e44ad", linewidth=2.5, alpha=0.9, label="節奏趨勢折線 (7-Hit 滑動平均)")

        # 4. 座標軸與標題美化
        ax.set_title(title, fontsize=16, fontweight="bold", pad=15)
        ax.set_xlabel("歌曲時間 (秒, Song Time)", fontsize=12, labelpad=10)
        ax.set_ylabel("玩家打擊時機 (毫秒 ms, Hit Offset)", fontsize=12, labelpad=10)
        ax.set_xlim(x_range)
        ax.set_ylim(-65, 65)

        # 格式化 X 軸時間標籤為 mm:ss
        def time_formatter(x, pos):
            mins = int(x // 60)
            secs = int(x % 60)
            return f"{mins:02d}:{secs:02d}"
        
        from matplotlib.ticker import FuncFormatter
        ax.xaxis.set_major_formatter(FuncFormatter(time_formatter))

        # 輔助格線與圖例
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="upper right", framealpha=0.9, fontsize=10)

        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        print(f"[成功匯出] 時序折線圖已儲存至: {output_path}")

