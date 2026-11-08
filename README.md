# SmartCity2 - In Falsus Review (智慧城市期中 - In Falsus 影像辨識復盤系統)

> **專案作者**：資訊三丙 吳昱霖  
> **技術核心**：YOLOv11 輕量目標偵測 + 時序消抖狀態機 + 倒數自動對齊 + 仿 *osu!* 時序誤差可視化

---

## 📌 專案簡介 (Overview)

本專案針對 lowiro 開發的 PC 音樂節奏冒險遊戲 **《In Falsus》**，設計了一套全自動影像辨識復盤系統。

### 解決痛點
* 音遊需要高強度的練習，但遊戲本身缺乏詳細的擊打誤差統計與段落弱點分析。
* 玩家在遊玩高難度譜面（如《魔王》）時，常因為變速、多押、密集長條而無法得知自己究竟是在哪個段落「心急搶拍（Early）」或「手速不足拖拍（Late）」。

### 解決方案
* 透過 **YOLOv11（遷移學習微調）** 逐影格分析玩家的錄影畫面。
* 以官方社群與 lowiro 判定標準之 **「大 P 判定區間（±25ms）」** 作為基準，將判定簡化為 **`early`、`perfect`、`late`** 三大分類。
* 自動產出音遊專用的 **「全曲打擊時機時序折線散點圖」** 與 **互動式網頁復盤儀表板**。

---

## ✨ 核心特色 (Key Features)

1. **零延遲離線分析架構（方法二）**：
   * 玩家遊玩時僅需顯卡硬體錄影，推論完全於後製離線進行，保證 100% 逐幀解析不漏幀，對遊戲幀率與手感零干擾。
2. **開場自動對齊（倒數與 CONNECT 動畫辨識）**：
   * 內建開場動畫偵測器，自動跳過開頭載入黑畫面與卡牌立繪演出，精確將時序圖的 `00:00` 錨定在歌曲正式開打的第一小節。
3. **6 軌下落 + 空中滑軌空間映射與時序消抖**：
   * 空間劃分 6 個按鍵槽位（`Shift`、`A`、`S`、`D`、`F`、`Space`）與中央空中滑軌。
   * 內建 80ms 消抖窗口狀態機，自動聚合多押（Chords）、跨軌音符（Wide Notes）與長按光效。
4. **全曲時序折線圖 (Timing Deviation Timeline)**：
   * **橫軸**：歌曲時間軸（mm:ss）。
   * **縱軸**：打擊時差偏移（ms），明確標記 $\pm 25\text{ ms}$ 大 P 安全綠色帶。
   * **趨勢折線**：以滑動平均線即時反映玩家在全曲各段落的節奏急躁或拖拍傾向。

---

## 📂 專案架構 (Project Structure)

```
smartcity2/
│
├── analyze_video.py                 # 【主入口】全自動分析單曲，生成時序折線圖與 HTML 報表
├── train.py                         # 【訓練】一鍵啟動 YOLOv11 三分類微調訓練 (GPU/CPU)
├── configs/
│   └── config.yaml                  # 系統設定檔 (大P ±25ms 參數、6 軌區間、ROI 設定)
│
├── src/
│   ├── video_manager.py             # OBS 預設檔名掃描與規格化重命名 (train/test)
│   ├── countdown_detector.py        # 畫面中央開場動畫與軌道啟動自動偵測
│   ├── detector.py                  # YOLOv11 推論封裝與類別解析
│   ├── tracker.py                   # 6 軌空間映射與 80ms 消抖狀態機
│   ├── visualizer.py                # 繪製「歌曲時間 vs. 打擊時機」專業時序折線散點圖
│   └── report_generator.py          # 生成視覺化 HTML 復盤報告與 JSON 統計
│
├── scripts/
│   ├── extract_training_frames.py   # 自動跳過前奏，抽取 60~80 張關鍵判定線 ROI 影格
│   └── inspect_train_01.py          # 影片元資料與影格抽檢工具
│
├── data/
│   ├── data.yaml                    # YOLOv11 資料集設定檔
│   └── dataset/images/train/        # 已抽取的 160 張高品質 ROI 訓練圖片
│
└── InFalsus_Replay_System_Plan.md   # 完整系統架構與期中規劃規格書
```

---

## 🚀 快速上手 (Quick Start)

### 1. 安裝環境依賴
```bash
pip install -r requirements.txt
pip install ultralytics
```

### 2. 準備影片與自動規格化
將 OBS 錄製的影片放進 `data/` 目錄，執行自動重命名整理：
```bash
python src/video_manager.py
```
*(系統會依序規格化為 `train_01.mp4`, `train_02.mp4`, `test_01.mp4`)*

### 3. 自動抽幀以供標註
```bash
python scripts/extract_training_frames.py
```
抽出的 ROI 圖片將自動存放於 `data/dataset/images/train/`。

### 4. 啟動 YOLOv11 模型訓練
使用標註工具（如 Roboflow）標註 `early`、`perfect`、`late` 三大類別後，執行：
```bash
python train.py
```

### 5. 執行全自動復盤分析
```bash
python analyze_video.py --video data/videos/test_01.mp4
```
輸出成果：
* **時序折線散點圖**：`reports/timing_timeline.png`
* **網頁互動儀表板**：`reports/replay_report.html`
* **JSON 數據匯出**：`reports/summary_stats.json`

---

## 📊 成果展示範例 (Preview)

時序折線圖範例：橫軸為歌曲時間，縱軸為打擊誤差（ms），標註 $\pm 25\text{ ms}$ 大 P 綠色安全帶：
```
                       In Falsus 全曲打擊時機時序折線圖
  +60 ms ------------------------------------------------------------- [Late 晚按區]
  +25 ms ============================================================= (大P上限 +25ms)
    0 ms - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - [標準拍點基準線]
  -25 ms ============================================================= (大P下限 -25ms)
  -60 ms ------------------------------------------------------------- [Early 早按區]
         00:00        00:30        01:00        01:30        02:00
                              歌曲時間 (分:秒)
```

---

## 📦 大型檔案備註
* 依據 GitHub 單檔 100MB 限制規範，原始遊玩影片 (`.mp4`, 800MB+) 不納入 Git 版控。
* 裁切後的有效 ROI 訓練資料集 (`data/dataset/`) 與完整分析原始碼均已完整包含於本倉庫中。

