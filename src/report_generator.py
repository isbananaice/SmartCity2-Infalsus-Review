import os
import json
from pathlib import Path
from typing import Dict, Any
from src.visualizer import ReplayVisualizer

class ReportGenerator:
    """產生 In Falsus 復盤報表 (含折線圖、統計數據與 HTML 儀表板)"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = Path(config.get("output", {}).get("report_dir", "reports"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.perfect_window = config.get("timing_metrics", {}).get("perfect_window_ms", 25.0)
        self.visualizer = ReplayVisualizer(perfect_window_ms=self.perfect_window)

    def generate(self, video_info: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, str]:
        """
        執行完整報表生成
        回傳已產生的檔案路徑 dict
        """
        results = {}
        chart_path = self.output_dir / "timing_timeline.png"
        json_path = self.output_dir / "summary_stats.json"
        html_path = self.output_dir / "replay_report.html"

        # 1. 產生時序折線圖
        events = stats.get("events", [])
        self.visualizer.plot_timing_timeline(
            events=events,
            output_path=str(chart_path),
            title=f"In Falsus 全曲打擊時機時序折線圖 - {Path(video_info.get('path', '遊玩片段')).stem}"
        )
        results["chart"] = str(chart_path)

        # 2. 匯出 JSON 統計檔
        # 移除 events 避免 json 過大，保留核心指標
        export_stats = {k: v for k, v in stats.items() if k != "events"}
        export_stats["video_info"] = video_info
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_stats, f, ensure_ascii=False, indent=2)
        results["json"] = str(json_path)

        # 3. 匯出獨立 HTML 儀表板
        self._generate_html_report(video_info, stats, chart_filename=chart_path.name, output_file=html_path)
        results["html"] = str(html_path)

        print(f"[報表產生完成] 儀表板已輸出至: {html_path}")
        return results

    def _generate_html_report(self, video_info: Dict[str, Any], stats: Dict[str, Any], chart_filename: str, output_file: Path):
        counts = stats.get("counts", {"perfect": 0, "early": 0, "late": 0})
        total = stats.get("total_notes", 0)
        p_rate = stats.get("perfect_rate", 0.0)
        mean_offset = stats.get("mean_offset_ms", 0.0)
        std_offset = stats.get("std_offset_ms", 0.0)
        lane_stats = stats.get("lane_stats", {})

        # 生成 6 軌統計行
        lane_rows = ""
        lane_display_names = {
            "lane_1": "1 (Shift)",
            "lane_2": "2 (Key A)",
            "lane_3": "3 (Key S)",
            "lane_4": "4 (Key D)",
            "lane_5": "5 (Key F)",
            "lane_6": "6 (Space)",
            "slide": "空中滑軌 (Slide)"
        }
        for l_key, l_data in lane_stats.items():
            name = lane_display_names.get(l_key, l_key)
            l_tot = l_data.get("total", 0)
            l_perf = l_data.get("perfect", 0)
            l_early = l_data.get("early", 0)
            l_late = l_data.get("late", 0)
            l_rate = f"{(l_perf / l_tot * 100):.1f}%" if l_tot > 0 else "-"
            lane_rows += f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{l_tot}</td>
                <td style="color:#2ecc71;">{l_perf}</td>
                <td style="color:#3498db;">{l_early}</td>
                <td style="color:#e74c3c;">{l_late}</td>
                <td><strong>{l_rate}</strong></td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>In Falsus 復盤分析儀表板</title>
    <style>
        body {{
            background-color: #121318;
            color: #e0e6ed;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            border-bottom: 2px solid #2a2e39;
            padding-bottom: 16px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        h1 {{
            margin: 0;
            font-size: 26px;
            color: #00d2ff;
            letter-spacing: 0.5px;
        }}
        .meta {{
            color: #8b949e;
            font-size: 14px;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: #1a1d24;
            border-radius: 8px;
            padding: 18px;
            border: 1px solid #2a2e39;
        }}
        .card .title {{
            font-size: 13px;
            color: #8b949e;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}
        .card .value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .chart-box {{
            background: #1a1d24;
            border: 1px solid #2a2e39;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
            text-align: center;
        }}
        .chart-box img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1a1d24;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #2a2e39;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #242832;
        }}
        th {{
            background: #20242d;
            color: #9da7b3;
            font-size: 13px;
            text-transform: uppercase;
        }}
        tr:hover {{
            background: #232732;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>In Falsus 智慧復盤分析報告</h1>
                <div class="meta" style="margin-top:6px;">檔案：{video_info.get('path', 'video')} | 長度：{video_info.get('duration_formatted', '00:00')} | FPS: {video_info.get('fps', 60)}</div>
            </div>
            <div class="meta">大P基準指標：±{self.perfect_window} ms</div>
        </header>

        <div class="card-grid">
            <div class="card">
                <div class="title">大 P 率 (Critical Perfect)</div>
                <div class="value" style="color: #2ecc71;">{p_rate}%</div>
            </div>
            <div class="card">
                <div class="title">總打擊數 (Total Hits)</div>
                <div class="value">{total}</div>
            </div>
            <div class="card">
                <div class="title">分類計數 (Perfect / Early / Late)</div>
                <div class="value" style="font-size: 20px; line-height: 1.4;">
                    <span style="color:#2ecc71;">P: {counts.get('perfect', 0)}</span> | 
                    <span style="color:#3498db;">E: {counts.get('early', 0)}</span> | 
                    <span style="color:#e74c3c;">L: {counts.get('late', 0)}</span>
                </div>
            </div>
            <div class="card">
                <div class="title">平均時序偏移 (Timing Offset)</div>
                <div class="value" style="color: {'#e74c3c' if mean_offset > 5 else ('#3498db' if mean_offset < -5 else '#2ecc71')};">
                    {'+' if mean_offset > 0 else ''}{mean_offset} ms
                </div>
                <div class="meta" style="margin-top:4px;">偏差標準差 (UR): ±{std_offset} ms</div>
            </div>
        </div>

        <div class="chart-box">
            <h3 style="margin-top:0; text-align:left; color:#f1f5f9;">全曲時序折線散點圖 (Timing Deviation Timeline)</h3>
            <img src="{chart_filename}" alt="Timing Timeline Chart">
        </div>

        <h3 style="color:#f1f5f9; margin-bottom: 12px;">6 鍵軌道與空中滑軌表現詳細診斷</h3>
        <table>
            <thead>
                <tr>
                    <th>軌道 (Lane)</th>
                    <th>總音符數</th>
                    <th>Perfect (大P)</th>
                    <th>Early (早按)</th>
                    <th>Late (晚按)</th>
                    <th>大P達成率</th>
                </tr>
            </thead>
            <tbody>
                {lane_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

