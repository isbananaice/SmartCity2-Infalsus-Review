/**
 * In Falsus AI 復盤診斷系統 GUI 前端核心邏輯
 * 具備 60 FPS 雙圖表同步定位線、精準影片控制、檔案管理與無縫快取套用
 */

(function () {
  'use strict';

  // 全域狀態
  const state = {
    videos: [],
    currentVideoId: null,
    replayData: null,
    songStartSec: 0,
    songDuration: 0,
    videoDuration: 0,
    isPlaying: false,
    animFrameId: null,
    playbackSpeed: 1.0,
    hoveredNote: null
  };

  // DOM 元素快取
  const dom = {
    // 導覽
    navTabs: document.querySelectorAll('.nav-tab'),
    pages: document.querySelectorAll('.page-view'),
    topGpuBadge: document.getElementById('topGpuBadge'),
    topModelBadge: document.getElementById('topModelBadge'),

    // 側邊欄
    videoSelect: document.getElementById('videoSelect'),
    videoAnalyzedBadge: document.getElementById('videoAnalyzedBadge'),
    videoFileInput: document.getElementById('videoFileInput'),
    btnStartAnalyze: document.getElementById('btnStartAnalyze'),
    btnReanalyze: document.getElementById('btnReanalyze'),
    btnOpenHtmlReport: document.getElementById('btnOpenHtmlReport'),
    analyzeProgressContainer: document.getElementById('analyzeProgressContainer'),
    analyzeProgressBar: document.getElementById('analyzeProgressBar'),
    analyzeProgressText: document.getElementById('analyzeProgressText'),

    // KPI
    kpiPerfectRate: document.getElementById('kpiPerfectRate'),
    kpiTotalNotes: document.getElementById('kpiTotalNotes'),
    kpiMeanOffset: document.getElementById('kpiMeanOffset'),
    kpiStdOffset: document.getElementById('kpiStdOffset'),
    songTimeInfo: document.getElementById('songTimeInfo'),
    barExact: document.getElementById('barExact'),
    barNear: document.getElementById('barNear'),
    barBreak: document.getElementById('barBreak'),
    countExact: document.getElementById('countExact'),
    countNear: document.getElementById('countNear'),
    countBreak: document.getElementById('countBreak'),
    lane1: document.getElementById('lane1'),
    lane2: document.getElementById('lane2'),
    lane3: document.getElementById('lane3'),
    lane4: document.getElementById('lane4'),
    lane5: document.getElementById('lane5'),
    lane6: document.getElementById('lane6'),

    // 播放器
    video: document.getElementById('mainVideo'),
    btnPlayPause: document.getElementById('btnPlayPause'),
    btnPrevFrame: document.getElementById('btnPrevFrame'),
    btnNextFrame: document.getElementById('btnNextFrame'),
    videoSeeker: document.getElementById('videoSeeker'),
    timeCurrent: document.getElementById('timeCurrent'),
    timeDuration: document.getElementById('timeDuration'),
    timeSong: document.getElementById('timeSong'),
    currentJudgeBadge: document.getElementById('currentJudgeBadge'),
    speedBtns: document.querySelectorAll('.btn-speed'),
    stepBtns: document.querySelectorAll('.btn-step'),

    // 圖表
    meanCanvas: document.getElementById('meanChartCanvas'),
    scatterCanvas: document.getElementById('scatterChartCanvas'),
    meanCursorValue: document.getElementById('meanCursorValue'),
    scatterCursorValue: document.getElementById('scatterCursorValue'),
    noteHoverTooltip: document.getElementById('noteHoverTooltip'),

    // 檔案頁面
    filesTableBody: document.getElementById('filesTableBody'),
    fileDropZone: document.getElementById('fileDropZone')
  };

  // ==========================================
  // 1. 初始化與事件綁定
  // ==========================================
  async function init() {
    setupTabNavigation();
    setupVideoControls();
    setupCanvasEvents();
    setupFileImport();
    await loadSystemInfo();
    await loadVideoList();
  }

  // 頂部分頁切換
  function setupTabNavigation() {
    dom.navTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetPage = tab.getAttribute('data-page');
        dom.navTabs.forEach(t => t.classList.remove('active'));
        dom.pages.forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(targetPage).classList.add('active');
        if (targetPage === 'page-analyzer') {
          resizeCanvases();
          drawCharts();
        } else if (targetPage === 'page-files') {
          renderFilesTable();
        }
      });
    });
  }

  // 格式化時間 (秒 -> mm:ss.ms)
  function formatTime(seconds, includeMs = true) {
    if (isNaN(seconds) || seconds < 0) seconds = 0;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    const mm = String(m).padStart(2, '0');
    const ss = String(s).padStart(2, '0');
    if (includeMs) {
      return `${mm}:${ss}.${String(ms).padStart(2, '0')}`;
    }
    return `${mm}:${ss}`;
  }

  // ==========================================
  // 2. 影片播放器與精準同步控制
  // ==========================================
  function setupVideoControls() {
    // 播放 / 暫停按鈕
    dom.btnPlayPause.addEventListener('click', togglePlayPause);
    
    // 空白鍵快捷鍵播放/暫停
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT') {
        e.preventDefault();
        togglePlayPause();
      }
    });

    // 影片時間更新事件
    dom.video.addEventListener('timeupdate', onVideoTimeUpdate);
    dom.video.addEventListener('seeking', onVideoTimeUpdate);
    dom.video.addEventListener('seeked', onVideoTimeUpdate);
    dom.video.addEventListener('loadedmetadata', () => {
      state.videoDuration = dom.video.duration || 120;
      dom.timeDuration.textContent = formatTime(state.videoDuration);
      dom.videoSeeker.max = state.videoDuration;
      onVideoTimeUpdate();
    });

    dom.video.addEventListener('play', () => {
      state.isPlaying = true;
      dom.btnPlayPause.textContent = '⏸ 暫停';
      startSmoothRenderLoop();
    });

    dom.video.addEventListener('pause', () => {
      state.isPlaying = false;
      dom.btnPlayPause.textContent = '▶ 播放';
      cancelAnimationFrame(state.animFrameId);
      drawCharts();
    });

    // 進度條拖動
    dom.videoSeeker.addEventListener('input', () => {
      const targetTime = parseFloat(dom.videoSeeker.value);
      dom.video.currentTime = targetTime;
      onVideoTimeUpdate();
    });

    // 快進 / 快退步進
    dom.stepBtns.forEach(btn => {
      const stepVal = btn.getAttribute('data-step');
      if (stepVal) {
        btn.addEventListener('click', () => {
          const delta = parseFloat(stepVal);
          dom.video.currentTime = Math.max(0, Math.min(state.videoDuration, dom.video.currentTime + delta));
        });
      }
    });

    // 單幀步進 (1/60s)
    const frameDuration = 1.0 / 60.0;
    dom.btnPrevFrame.addEventListener('click', () => {
      dom.video.pause();
      dom.video.currentTime = Math.max(0, dom.video.currentTime - frameDuration);
    });
    dom.btnNextFrame.addEventListener('click', () => {
      dom.video.pause();
      dom.video.currentTime = Math.min(state.videoDuration, dom.video.currentTime + frameDuration);
    });

    // 播放速度切換
    dom.speedBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        dom.speedBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.playbackSpeed = parseFloat(btn.getAttribute('data-speed'));
        dom.video.playbackRate = state.playbackSpeed;
      });
    });
  }

  function togglePlayPause() {
    if (dom.video.paused) {
      dom.video.play();
    } else {
      dom.video.pause();
    }
  }

  // 影片時間更新處理
  function onVideoTimeUpdate() {
    const curTime = dom.video.currentTime;
    dom.timeCurrent.textContent = formatTime(curTime);
    dom.videoSeeker.value = curTime;

    // 計算曲內時間
    const songTime = Math.max(0, curTime - state.songStartSec);
    dom.timeSong.textContent = `曲中: ${formatTime(songTime)}`;
    dom.songTimeInfo.textContent = formatTime(songTime, false);

    // 判斷當前音符反饋
    updateCurrentJudgeCallout(songTime);

    // 重繪定位線
    drawCharts();
  }

  // 60 FPS 平滑跟隨繪製循環
  function startSmoothRenderLoop() {
    function loop() {
      if (state.isPlaying) {
        onVideoTimeUpdate();
        state.animFrameId = requestAnimationFrame(loop);
      }
    }
    state.animFrameId = requestAnimationFrame(loop);
  }

  // 顯示即時判定浮水文字
  function updateCurrentJudgeCallout(songTime) {
    if (!state.replayData || !state.replayData.events) return;
    // 尋找當前時間 ±0.08 秒內的打擊事件
    const events = state.replayData.events;
    const hit = events.find(e => Math.abs(e.timestamp - songTime) <= 0.08);
    if (hit) {
      const cat = hit.category.toUpperCase();
      dom.currentJudgeBadge.textContent = `${hit.lane || 'Key'} | ${cat} (${hit.offset_ms > 0 ? '+' : ''}${hit.offset_ms}ms)`;
      dom.currentJudgeBadge.className = `overlay-badge ${hit.category.toLowerCase()}`;
    }
  }

  // ==========================================
  // 3. 雙圖表 Canvas 高效能繪圖與定位線同步
  // ==========================================
  function setupCanvasEvents() {
    window.addEventListener('resize', () => {
      resizeCanvases();
      drawCharts();
    });

    // 點擊圖表任意位置跳轉影片時間 (Seek)
    [dom.meanCanvas, dom.scatterCanvas].forEach(canvas => {
      canvas.addEventListener('click', (e) => {
        if (!state.replayData) return;
        const rect = canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const padLeft = 55;
        const padRight = 20;
        const chartW = rect.width - padLeft - padRight;
        if (clickX >= padLeft && clickX <= rect.width - padRight) {
          const ratio = (clickX - padLeft) / chartW;
          const targetSongTime = ratio * state.songDuration;
          const targetVideoTime = targetSongTime + state.songStartSec;
          dom.video.currentTime = Math.max(0, Math.min(state.videoDuration, targetVideoTime));
        }
      });
    });

    // 散點圖 Hover 提示
    dom.scatterCanvas.addEventListener('mousemove', (e) => {
      if (!state.replayData || !state.replayData.events) return;
      const rect = dom.scatterCanvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const padLeft = 55;
      const padRight = 20;
      const padTop = 15;
      const padBottom = 25;
      const chartW = rect.width - padLeft - padRight;
      const chartH = rect.height - padTop - padBottom;

      const timeRatio = (mouseX - padLeft) / chartW;
      const targetTime = timeRatio * state.songDuration;

      // 尋找距離最近的點
      const events = state.replayData.events;
      let closest = null;
      let minDis = 15; // 15px 半徑

      for (let i = 0; i < events.length; i++) {
        const ev = events[i];
        if (Math.abs(ev.timestamp - targetTime) > 3.0) continue;
        const px = padLeft + (ev.timestamp / state.songDuration) * chartW;
        // Y: -75 ~ +75 ms
        const yNorm = (ev.offset_ms - (-75)) / 150.0;
        const py = padTop + chartH - yNorm * chartH;

        const dist = Math.hypot(px - mouseX, py - mouseY);
        if (dist < minDis) {
          minDis = dist;
          closest = { ev, px, py };
        }
      }

      if (closest) {
        state.hoveredNote = closest;
        dom.noteHoverTooltip.classList.remove('hidden');
        dom.noteHoverTooltip.style.left = `${closest.px + 12}px`;
        dom.noteHoverTooltip.style.top = `${closest.py - 20}px`;
        const sign = closest.ev.offset_ms > 0 ? '+' : '';
        dom.noteHoverTooltip.innerHTML = `
          <strong>[${closest.ev.category.toUpperCase()}]</strong> ${closest.ev.lane || 'Track'}<br>
          時間: ${formatTime(closest.ev.timestamp)}<br>
          偏差: <span style="color: ${getCategoryColor(closest.ev.category)}">${sign}${closest.ev.offset_ms} ms</span>
        `;
      } else {
        state.hoveredNote = null;
        dom.noteHoverTooltip.classList.add('hidden');
      }
    });

    dom.scatterCanvas.addEventListener('mouseleave', () => {
      state.hoveredNote = null;
      dom.noteHoverTooltip.classList.add('hidden');
    });
  }

  function getCategoryColor(cat) {
    if (cat === 'exact' || cat === 'perfect') return '#2ecc71';
    if (cat === 'near') return '#f39c12';
    if (cat === 'break') return '#ff4757';
    if (cat === 'early') return '#3498db';
    if (cat === 'late') return '#f39c12';
    return '#00f0ff';
  }

  function resizeCanvases() {
    [dom.meanCanvas, dom.scatterCanvas].forEach(canvas => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.parentElement.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
    });
  }

  // 主要繪圖核心 (重繪兩個表格 + 影片定位線)
  function drawCharts() {
    if (!state.replayData) return;
    const currentSongTime = Math.max(0, dom.video.currentTime - state.songStartSec);

    drawMeanChart(currentSongTime);
    drawScatterChart(currentSongTime);
  }

  // 繪製中間表格: 滾動平均偏差趨勢 (Rolling Mean Offset)
  function drawMeanChart(currentSongTime) {
    const canvas = dom.meanCanvas;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;

    ctx.clearRect(0, 0, w, h);

    const padLeft = 55;
    const padRight = 20;
    const padTop = 15;
    const padBottom = 25;
    const chartW = w - padLeft - padRight;
    const chartH = h - padTop - padBottom;

    const yMin = -35;
    const yMax = 35;
    const maxT = state.songDuration || 120;

    const getX = (t) => padLeft + (t / maxT) * chartW;
    const getY = (val) => padTop + chartH - ((val - yMin) / (yMax - yMin)) * chartH;

    // 1. ±25ms 大P 判定帶
    const yP25 = getY(25);
    const yM25 = getY(-25);
    ctx.fillStyle = 'rgba(46, 204, 113, 0.12)';
    ctx.fillRect(padLeft, yP25, chartW, yM25 - yP25);

    // 2. 網格線與 Y 軸刻度
    ctx.strokeStyle = '#1a2438';
    ctx.lineWidth = 1;
    ctx.font = '10px "JetBrains Mono"';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    [-25, -15, 0, 15, 25].forEach(val => {
      const y = getY(val);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(w - padRight, y);
      ctx.stroke();
      ctx.fillText(`${val > 0 ? '+' : ''}${val}ms`, padLeft - 8, y);
    });

    // 0ms 中心基準線
    const yZero = getY(0);
    ctx.strokeStyle = '#27ae60';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padLeft, yZero);
    ctx.lineTo(w - padRight, yZero);
    ctx.stroke();
    ctx.setLineDash([]);

    // X 軸時間刻度
    drawTimeAxis(ctx, maxT, padLeft, chartW, h - padBottom);

    // 3. 滾動平均折線
    const series = state.replayData.rolling_series || [];
    if (series.length > 1) {
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      series.forEach((pt, idx) => {
        const px = getX(pt.timestamp);
        const py = getY(pt.mean_offset_ms);
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
    }

    // 4. 垂直時間定位線 (跟隨影片播放時間移動！)
    if (currentSongTime >= 0 && currentSongTime <= maxT) {
      const cursorX = getX(currentSongTime);
      ctx.strokeStyle = '#ff4757';
      ctx.lineWidth = 2.0;
      ctx.shadowColor = '#ff4757';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.moveTo(cursorX, padTop);
      ctx.lineTo(cursorX, h - padBottom);
      ctx.stroke();
      ctx.shadowBlur = 0; // 重設光暈

      // 取得當前滾動平均值
      let curVal = 0;
      const pt = series.find(p => Math.abs(p.timestamp - currentSongTime) <= 0.6);
      if (pt) curVal = pt.mean_offset_ms;
      dom.meanCursorValue.classList.remove('hidden');
      dom.meanCursorValue.style.left = `${cursorX}px`;
      dom.meanCursorValue.textContent = `${curVal > 0 ? '+' : ''}${curVal.toFixed(1)} ms`;
    } else {
      dom.meanCursorValue.classList.add('hidden');
    }
  }

  // 繪製最下面表格: 各音符偏差散點圖 (Individual Note Timing Scatter)
  function drawScatterChart(currentSongTime) {
    const canvas = dom.scatterCanvas;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;

    ctx.clearRect(0, 0, w, h);

    const padLeft = 55;
    const padRight = 20;
    const padTop = 15;
    const padBottom = 25;
    const chartW = w - padLeft - padRight;
    const chartH = h - padTop - padBottom;

    const yMin = -75;
    const yMax = 75;
    const maxT = state.songDuration || 120;

    const getX = (t) => padLeft + (t / maxT) * chartW;
    const getY = (val) => padTop + chartH - ((val - yMin) / (yMax - yMin)) * chartH;

    // 1. ±25ms 大P 判定帶
    const yP25 = getY(25);
    const yM25 = getY(-25);
    ctx.fillStyle = 'rgba(46, 204, 113, 0.12)';
    ctx.fillRect(padLeft, yP25, chartW, yM25 - yP25);

    // 2. 網格線與 Y 軸刻度
    ctx.strokeStyle = '#1a2438';
    ctx.lineWidth = 1;
    ctx.font = '10px "JetBrains Mono"';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    [-50, -25, 0, 25, 50].forEach(val => {
      const y = getY(val);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(w - padRight, y);
      ctx.stroke();
      ctx.fillText(`${val > 0 ? '+' : ''}${val}ms`, padLeft - 8, y);
    });

    // 0ms 中心基準線
    const yZero = getY(0);
    ctx.strokeStyle = '#27ae60';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padLeft, yZero);
    ctx.lineTo(w - padRight, yZero);
    ctx.stroke();
    ctx.setLineDash([]);

    // X 軸時間刻度
    drawTimeAxis(ctx, maxT, padLeft, chartW, h - padBottom);

    // 3. 音符散點繪製
    const events = state.replayData.events || [];
    for (let i = 0; i < events.length; i++) {
      const ev = events[i];
      const px = getX(ev.timestamp);
      const py = getY(ev.offset_ms);

      ctx.fillStyle = getCategoryColor(ev.category);
      if (ev.category === 'break') {
        // Break 畫菱形
        ctx.beginPath();
        ctx.moveTo(px, py - 4);
        ctx.lineTo(px + 4, py);
        ctx.lineTo(px, py + 4);
        ctx.lineTo(px - 4, py);
        ctx.closePath();
        ctx.fill();
      } else {
        // 一般圓點
        ctx.beginPath();
        ctx.arc(px, py, 2.8, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // 4. 垂直時間定位線 (跟隨影片播放時間移動！)
    if (currentSongTime >= 0 && currentSongTime <= maxT) {
      const cursorX = getX(currentSongTime);
      ctx.strokeStyle = '#ff4757';
      ctx.lineWidth = 2.0;
      ctx.shadowColor = '#ff4757';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.moveTo(cursorX, padTop);
      ctx.lineTo(cursorX, h - padBottom);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // 尋找當前最接近的音符
      const nearEv = events.find(e => Math.abs(e.timestamp - currentSongTime) <= 0.2);
      if (nearEv) {
        dom.scatterCursorValue.classList.remove('hidden');
        dom.scatterCursorValue.style.left = `${cursorX}px`;
        const sign = nearEv.offset_ms > 0 ? '+' : '';
        dom.scatterCursorValue.textContent = `${nearEv.lane || 'Key'}: ${sign}${nearEv.offset_ms}ms`;
      } else {
        dom.scatterCursorValue.classList.add('hidden');
      }
    } else {
      dom.scatterCursorValue.classList.add('hidden');
    }
  }

  // 繪製 X 軸時間刻度
  function drawTimeAxis(ctx, maxT, padLeft, chartW, axisY) {
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = '#64748b';
    ctx.font = '10px "JetBrains Mono"';

    const stepSec = maxT > 100 ? 15 : 10;
    for (let t = 0; t <= maxT; t += stepSec) {
      const x = padLeft + (t / maxT) * chartW;
      ctx.beginPath();
      ctx.moveTo(x, axisY);
      ctx.lineTo(x, axisY + 4);
      ctx.stroke();
      ctx.fillText(formatTime(t, false), x, axisY + 6);
    }
  }

  // ==========================================
  // 4. 資料載入與切換 (直接套用既有分析)
  // ==========================================
  async function loadVideoList() {
    try {
      const res = await fetch('/api/videos');
      const data = await res.json();
      state.videos = data.videos || [];

      dom.videoSelect.innerHTML = '';
      if (state.videos.length === 0) {
        dom.videoSelect.innerHTML = '<option value="">無可用影片，請匯入</option>';
        return;
      }

      state.videos.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = `${v.filename} (${v.analyzed ? '🟢 已分析' : '🟡 未分析'})`;
        dom.videoSelect.appendChild(opt);
      });

      // 預設選擇第一個
      selectVideo(state.videos[0].id);

      dom.videoSelect.addEventListener('change', () => {
        selectVideo(dom.videoSelect.value);
      });
    } catch (e) {
      console.error('載入影片列表失敗:', e);
    }
  }

  async function selectVideo(videoId) {
    if (!videoId) return;
    state.currentVideoId = videoId;
    const vMeta = state.videos.find(v => v.id === videoId);

    // 更新 Badge
    if (vMeta && vMeta.analyzed) {
      dom.videoAnalyzedBadge.textContent = '🟢 已載入歷史分析';
      dom.videoAnalyzedBadge.className = 'badge';
      dom.btnStartAnalyze.textContent = '⚡ 重新分析';
    } else {
      dom.videoAnalyzedBadge.textContent = '🟡 尚未分析';
      dom.videoAnalyzedBadge.className = 'badge pending';
      dom.btnStartAnalyze.textContent = '⚡ 開始分析';
    }

    // 載入影片串流
    dom.video.src = `/api/video_stream/${videoId}`;
    dom.video.load();

    // 載入復盤數據 (若已有分析則直接套用)
    await loadReplayData(videoId);
  }

  async function loadReplayData(videoId) {
    try {
      const res = await fetch(`/api/replay/${videoId}`);
      const data = await res.json();

      if (!data.analyzed) {
        state.replayData = null;
        clearKpiDisplay();
        return;
      }

      state.replayData = data;
      state.songStartSec = data.song_start_sec || 0;
      
      const events = data.events || [];
      state.songDuration = events.length > 0 ? Math.max(...events.map(e => e.timestamp)) : 120;

      // 更新側邊欄 KPI
      updateKpiDisplay(data.stats);

      // 重繪圖表
      resizeCanvases();
      drawCharts();

    } catch (e) {
      console.error('載入復盤數據失敗:', e);
    }
  }

  function updateKpiDisplay(stats) {
    if (!stats) return;
    dom.kpiPerfectRate.textContent = `${stats.perfect_rate || 0}%`;
    dom.kpiTotalNotes.textContent = stats.total_notes || 0;
    const mean = stats.mean_offset_ms || 0;
    dom.kpiMeanOffset.textContent = `${mean > 0 ? '+' : ''}${mean} ms`;
    dom.kpiStdOffset.textContent = `±${stats.std_offset_ms || 0} ms`;

    const counts = stats.counts || {};
    const exact = counts.exact || 0;
    const near = counts.near || 0;
    const brk = counts.break || 0;
    const tot = Math.max(1, exact + near + brk);

    dom.countExact.textContent = exact;
    dom.countNear.textContent = near;
    dom.countBreak.textContent = brk;

    dom.barExact.style.width = `${(exact / tot) * 100}%`;
    dom.barNear.style.width = `${(near / tot) * 100}%`;
    dom.barBreak.style.width = `${(brk / tot) * 100}%`;

    const lanes = stats.lane_stats || {};
    dom.lane1.textContent = lanes.lane_1 ? lanes.lane_1.total : 0;
    dom.lane2.textContent = lanes.lane_2 ? lanes.lane_2.total : 0;
    dom.lane3.textContent = lanes.lane_3 ? lanes.lane_3.total : 0;
    dom.lane4.textContent = lanes.lane_4 ? lanes.lane_4.total : 0;
    dom.lane5.textContent = lanes.lane_5 ? lanes.lane_5.total : 0;
    dom.lane6.textContent = lanes.lane_6 ? lanes.lane_6.total : 0;
  }

  function clearKpiDisplay() {
    dom.kpiPerfectRate.textContent = '--%';
    dom.kpiTotalNotes.textContent = '--';
    dom.kpiMeanOffset.textContent = '-- ms';
    dom.kpiStdOffset.textContent = '±-- ms';
    dom.countExact.textContent = '0';
    dom.countNear.textContent = '0';
    dom.countBreak.textContent = '0';
    dom.barExact.style.width = '0%';
    dom.barNear.style.width = '0%';
    dom.barBreak.style.width = '0%';
  }

  // ==========================================
  // 5. 檔案管理與匯入 (支援已分析直接套用)
  // ==========================================
  function setupFileImport() {
    // 匯入檔案按鈕觸發
    dom.videoFileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (file) await uploadVideoFile(file);
    });

    // 拖曳上傳
    if (dom.fileDropZone) {
      dom.fileDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dom.fileDropZone.style.borderColor = 'var(--primary)';
      });
      dom.fileDropZone.addEventListener('dragleave', () => {
        dom.fileDropZone.style.borderColor = 'var(--border-light)';
      });
      dom.fileDropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dom.fileDropZone.style.borderColor = 'var(--border-light)';
        if (e.dataTransfer.files.length > 0) {
          await uploadVideoFile(e.dataTransfer.files[0]);
        }
      });
    }

    // 開始分析按鈕
    dom.btnStartAnalyze.addEventListener('click', () => triggerAnalysis(state.currentVideoId));
    dom.btnReanalyze.addEventListener('click', () => triggerAnalysis(state.currentVideoId));

    // 開啟獨立 HTML 報告
    dom.btnOpenHtmlReport.addEventListener('click', () => {
      if (state.currentVideoId) {
        window.open(`/reports/${state.currentVideoId}_report.html`, '_blank');
      }
    });
  }

  async function uploadVideoFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    dom.analyzeProgressContainer.classList.remove('hidden');
    dom.analyzeProgressBar.style.width = '30%';
    dom.analyzeProgressText.textContent = '正在上傳影片至系統...';

    try {
      const res = await fetch('/api/import_video', { method: 'POST', body: formData });
      const ret = await res.json();
      
      dom.analyzeProgressBar.style.width = '100%';
      dom.analyzeProgressText.textContent = ret.message;
      alert(ret.message);

      await loadVideoList();
      selectVideo(ret.id);
    } catch (e) {
      alert('上傳失敗: ' + e);
    } finally {
      setTimeout(() => dom.analyzeProgressContainer.classList.add('hidden'), 3000);
    }
  }

  async function triggerAnalysis(videoId) {
    if (!videoId) return;
    dom.analyzeProgressContainer.classList.remove('hidden');
    dom.analyzeProgressBar.style.width = '5%';
    dom.analyzeProgressText.textContent = '正在排入分析任務...';

    try {
      const res = await fetch(`/api/analyze/${videoId}?step=1`, { method: 'POST' });
      const ret = await res.json();

      // 輪詢進度
      const pollTimer = setInterval(async () => {
        const sRes = await fetch(`/api/analyze_status/${videoId}`);
        const status = await sRes.json();
        dom.analyzeProgressBar.style.width = `${status.progress || 0}%`;
        dom.analyzeProgressText.textContent = status.log || '處理中...';

        if (status.status === 'completed') {
          clearInterval(pollTimer);
          alert('AI 復盤分析圓滿完成！');
          setTimeout(() => dom.analyzeProgressContainer.classList.add('hidden'), 2000);
          await loadVideoList();
          selectVideo(videoId);
        } else if (status.status === 'error') {
          clearInterval(pollTimer);
          alert('分析出錯: ' + status.log);
        }
      }, 1000);
    } catch (e) {
      alert('觸發分析失敗: ' + e);
    }
  }

  // 渲染檔案管理頁面表格
  function renderFilesTable() {
    dom.filesTableBody.innerHTML = '';
    if (state.videos.length === 0) {
      dom.filesTableBody.innerHTML = '<tr><td colspan="7" style="text-align: center;">尚無影片</td></tr>';
      return;
    }

    state.videos.forEach(v => {
      const tr = document.createElement('tr');
      const stats = v.stats || {};
      const rateStr = stats.perfect_rate ? `${stats.perfect_rate}%` : '--';
      const notesStr = stats.total_notes || '--';
      const offsetStr = stats.mean_offset_ms ? `${stats.mean_offset_ms}ms` : '--';
      const statusBadge = v.analyzed ? '<span class="badge">已分析</span>' : '<span class="badge pending">未分析</span>';

      tr.innerHTML = `
        <td><strong>${v.filename}</strong></td>
        <td>${v.size_mb} MB</td>
        <td>${statusBadge}</td>
        <td style="color: var(--success); font-weight: 700;">${rateStr}</td>
        <td>${notesStr}</td>
        <td>${offsetStr}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="window.guiSelectVideo('${v.id}')">檢視</button>
          <button class="btn btn-outline btn-sm danger" onclick="window.guiDeleteVideo('${v.id}')">刪除</button>
        </td>
      `;
      dom.filesTableBody.appendChild(tr);
    });
  }

  // 全域外顯函數供 HTML 點擊
  window.guiSelectVideo = (id) => {
    dom.navTabs[0].click();
    dom.videoSelect.value = id;
    selectVideo(id);
  };

  window.guiDeleteVideo = async (id) => {
    if (confirm(`確定要刪除 ${id} 影片與分析紀錄嗎？`)) {
      await fetch(`/api/delete_video/${id}`, { method: 'DELETE' });
      await loadVideoList();
      renderFilesTable();
    }
  };

  async function loadSystemInfo() {
    try {
      const res = await fetch('/api/system_info');
      const info = await res.json();
      if (info.device) {
        dom.topGpuBadge.textContent = `GPU: ${info.device}`;
      }
    } catch (e) {}
  }

  // 啟動
  window.addEventListener('DOMContentLoaded', init);

})();
