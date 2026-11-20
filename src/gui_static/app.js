/**
 * In Falsus AI 復盤診斷系統 GUI 前端核心邏輯
 * 支援:
 * 1. 上下滑動拖曳自由調整影片與雙圖表高度 (含雙擊重設與持久化記憶)
 * 2. 影片隨容器高度等比例動態縮放
 * 3. 60 FPS 平滑時間定位線同步與雙向跳轉
 * 4. 檔案管理與直接套用快取
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
  window.appState = state;

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
    videoCard: document.getElementById('videoCard'),
    videoContainer: document.getElementById('videoContainer'),
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

    // 即時打擊與判定 HUD (影片右側)
    liveExact: document.getElementById('liveExact'),
    liveNearEarly: document.getElementById('liveNearEarly'),
    liveNearLate: document.getElementById('liveNearLate'),
    liveBreakEarly: document.getElementById('liveBreakEarly'),
    liveBreakLate: document.getElementById('liveBreakLate'),
    liveLane1: document.getElementById('liveLane1'),
    liveLane2: document.getElementById('liveLane2'),
    liveLane3: document.getElementById('liveLane3'),
    liveLane4: document.getElementById('liveLane4'),
    liveLane5: document.getElementById('liveLane5'),
    liveLane6: document.getElementById('liveLane6'),
    liveLaneSlide: document.getElementById('liveLaneSlide'),

    // 拖曳調整把手
    handleVideo: document.getElementById('handleVideo'),
    handleMean: document.getElementById('handleMean'),
    handleScatter: document.getElementById('handleScatter'),

    // 圖表與容器
    meanCanvasWrapper: document.getElementById('meanCanvasWrapper'),
    scatterCanvasWrapper: document.getElementById('scatterCanvasWrapper'),
    meanCanvas: document.getElementById('meanChartCanvas'),
    scatterCanvas: document.getElementById('scatterChartCanvas'),
    meanLiveBadge: document.getElementById('meanLiveBadge'),
    scatterLiveBadge: document.getElementById('scatterLiveBadge'),
    noteHoverTooltip: document.getElementById('noteHoverTooltip'),

    // 檔案頁面
    filesTableBody: document.getElementById('filesTableBody'),
    fileDropZone: document.getElementById('fileDropZone')
  };

  // ==========================================
  // 本地桌面 API 橋接器 (優先使用 pywebview 原生 JS API，完全離線免伺服器)
  // ==========================================
  const backend = {
    async waitForReady(timeoutMs = 3000) {
      if (window.pywebview && window.pywebview.api) return true;
      const start = Date.now();
      while (Date.now() - start < timeoutMs) {
        if (window.pywebview && window.pywebview.api) return true;
        await new Promise(r => setTimeout(r, 60));
      }
      return false;
    },
    async getVideos() {
      await this.waitForReady();
      if (window.pywebview && window.pywebview.api) {
        return await window.pywebview.api.get_videos();
      }
      const res = await fetch('/api/videos');
      return await res.json();
    },
    async getReplay(videoId) {
      await this.waitForReady();
      if (window.pywebview && window.pywebview.api) {
        return await window.pywebview.api.get_replay_data(videoId);
      }
      const res = await fetch(`/api/replay/${videoId}`);
      return await res.json();
    },
    async selectAndImportVideo() {
      await this.waitForReady();
      if (window.pywebview && window.pywebview.api) {
        return await window.pywebview.api.select_and_import_video();
      }
      return null;
    },
    async startAnalysis(videoId, step = 1) {
      await this.waitForReady();
      if (window.pywebview && window.pywebview.api) {
        return await window.pywebview.api.start_analysis(videoId, step);
      }
      const res = await fetch(`/api/analyze/${videoId}?step=${step}`, { method: 'POST' });
      return await res.json();
    },
    async getAnalysisStatus(videoId) {
      await this.waitForReady();
      if (window.pywebview && window.pywebview.api) {
        return await window.pywebview.api.get_analysis_status(videoId);
      }
      const res = await fetch(`/api/analyze_status/${videoId}`);
      return await res.json();
    },
    async deleteVideo(videoId) {
      await this.waitForReady();
      if (window.pywebview && window.pywebview.api) {
        return await window.pywebview.api.delete_video(videoId);
      }
      const res = await fetch(`/api/delete_video/${videoId}`, { method: 'DELETE' });
      return await res.json();
    },
    async openHtmlReport(videoId) {
      await this.waitForReady();
      if (window.pywebview && window.pywebview.api) {
        return await window.pywebview.api.open_html_report(videoId);
      }
      window.open(`/reports/${videoId}_report.html`, '_blank');
    },
    async getSystemInfo() {
      await this.waitForReady();
      if (window.pywebview && window.pywebview.api) {
        return await window.pywebview.api.get_system_info();
      }
      try {
        const res = await fetch('/api/system_info');
        return await res.json();
      } catch (e) {
        return { device: 'RTX 3070', cuda_available: true, model: { input_size: 960 } };
      }
    }
  };

  // ==========================================
  // 1. 初始化與事件綁定
  // ==========================================
  async function init() {
    setupTabNavigation();
    setupVideoControls();
    setupCanvasEvents();
    setupResizableSections();
    setupFileImport();
    await Promise.all([
      loadVideoList(),
      loadSystemInfo()
    ]);
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
  // 2. 上下滑動高度調整 (Resizable Splitters)
  // ==========================================
  function setupResizableSections() {
    // 載入持久化自訂高度
    const savedVideoH = localStorage.getItem('infalsus_video_h');
    const savedMeanH = localStorage.getItem('infalsus_mean_h');
    const savedScatterH = localStorage.getItem('infalsus_scatter_h');

    if (savedVideoH && dom.videoContainer) dom.videoContainer.style.height = `${savedVideoH}px`;
    if (savedMeanH && dom.meanCanvasWrapper) dom.meanCanvasWrapper.style.height = `${savedMeanH}px`;
    if (savedScatterH && dom.scatterCanvasWrapper) dom.scatterCanvasWrapper.style.height = `${savedScatterH}px`;

    function makeResizable(handle, targetElem, minH, maxH, storageKey, onResize) {
      if (!handle || !targetElem) return;

      let startY = 0;
      let startH = 0;
      let isDragging = false;

      handle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        isDragging = true;
        startY = e.clientY;
        startH = targetElem.getBoundingClientRect().height;
        handle.classList.add('active');
        document.body.style.cursor = 'ns-resize';
        document.body.style.userSelect = 'none';

        function onMouseMove(e) {
          if (!isDragging) return;
          const deltaY = e.clientY - startY;
          const newH = Math.max(minH, Math.min(maxH, startH + deltaY));
          targetElem.style.height = `${newH}px`;
          if (onResize) onResize();
        }

        function onMouseUp() {
          if (isDragging) {
            isDragging = false;
            handle.classList.remove('active');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            localStorage.setItem(storageKey, Math.round(targetElem.getBoundingClientRect().height));
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
            if (onResize) onResize();
          }
        }

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
      });

      // 雙擊把手還原預設
      handle.addEventListener('dblclick', () => {
        targetElem.style.height = '';
        localStorage.removeItem(storageKey);
        if (onResize) onResize();
      });
    }

    // 1. 調整影片高度 (160px ~ 750px)
    makeResizable(dom.handleVideo, dom.videoContainer, 160, 750, 'infalsus_video_h', () => {
      resizeCanvases();
      drawCharts();
    });

    // 2. 調整中間走勢表格高度 (55px ~ 380px)
    makeResizable(dom.handleMean, dom.meanCanvasWrapper, 55, 380, 'infalsus_mean_h', () => {
      resizeCanvases();
      drawCharts();
    });

    // 3. 調整最下方音符散點表格高度 (55px ~ 380px)
    makeResizable(dom.handleScatter, dom.scatterCanvasWrapper, 55, 380, 'infalsus_scatter_h', () => {
      resizeCanvases();
      drawCharts();
    });
  }

  // ==========================================
  // 3. 影片播放器與精準同步控制
  // ==========================================
  function setupVideoControls() {
    dom.btnPlayPause.addEventListener('click', togglePlayPause);
    
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT') {
        e.preventDefault();
        togglePlayPause();
      }
    });

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
      dom.btnPlayPause.textContent = '暫停';
      startSmoothRenderLoop();
    });

    dom.video.addEventListener('pause', () => {
      state.isPlaying = false;
      dom.btnPlayPause.textContent = '播放';
      cancelAnimationFrame(state.animFrameId);
      drawCharts();
    });

    dom.videoSeeker.addEventListener('input', () => {
      const targetTime = parseFloat(dom.videoSeeker.value);
      dom.video.currentTime = targetTime;
      onVideoTimeUpdate();
    });

    dom.stepBtns.forEach(btn => {
      const stepVal = btn.getAttribute('data-step');
      if (stepVal) {
        btn.addEventListener('click', () => {
          const delta = parseFloat(stepVal);
          dom.video.currentTime = Math.max(0, Math.min(state.videoDuration, dom.video.currentTime + delta));
        });
      }
    });

    const frameDuration = 1.0 / 60.0;
    dom.btnPrevFrame.addEventListener('click', () => {
      dom.video.pause();
      dom.video.currentTime = Math.max(0, dom.video.currentTime - frameDuration);
    });
    dom.btnNextFrame.addEventListener('click', () => {
      dom.video.pause();
      dom.video.currentTime = Math.min(state.videoDuration, dom.video.currentTime + frameDuration);
    });

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

  function onVideoTimeUpdate() {
    const curTime = dom.video.currentTime;
    dom.timeCurrent.textContent = formatTime(curTime);
    dom.videoSeeker.value = curTime;

    const songTime = Math.max(0, curTime - state.songStartSec);
    dom.timeSong.textContent = `曲中: ${formatTime(songTime)}`;
    dom.songTimeInfo.textContent = formatTime(songTime, false);

    updateCurrentJudgeCallout(songTime);
    updateLiveHud(songTime);
    drawCharts();
  }

  function startSmoothRenderLoop() {
    function loop() {
      if (state.isPlaying) {
        onVideoTimeUpdate();
        state.animFrameId = requestAnimationFrame(loop);
      }
    }
    state.animFrameId = requestAnimationFrame(loop);
  }

  function updateCurrentJudgeCallout(songTime) {
    if (!state.replayData || !state.replayData.events) return;
    const events = state.replayData.events;
    const hit = events.find(e => Math.abs(e.timestamp - songTime) <= 0.08);
    if (hit) {
      const cat = hit.category.toUpperCase();
      dom.currentJudgeBadge.textContent = `${hit.lane || 'Key'} | ${cat} (${hit.offset_ms > 0 ? '+' : ''}${hit.offset_ms}ms)`;
      dom.currentJudgeBadge.className = `overlay-badge ${hit.category.toLowerCase()}`;
    }
  }

  // 即時計算並更新右側 HUD (精準 / 早 / 晚 / 過早 / 過晚 + 六軌與滑軌)
  // 隨著影片播放位置累計增減，向後跳轉增加，向前跳轉減少
  function updateLiveHud(songTime) {
    if (!state.replayData || !state.replayData.events) {
      clearLiveHud();
      return;
    }
    const events = state.replayData.events;

    let exact = 0, early = 0, late = 0, breakEarly = 0, breakLate = 0;
    let l1 = 0, l2 = 0, l3 = 0, l4 = 0, l5 = 0, l6 = 0, slide = 0;

    for (let i = 0; i < events.length; i++) {
      const e = events[i];
      if (e.timestamp > songTime) break; // events 已由小到大排序

      const off = e.offset_ms;
      const cat = e.category;

      if (cat === 'exact' || Math.abs(off) <= 25.0) {
        exact++;
      } else if (cat === 'near' || (Math.abs(off) > 25.0 && Math.abs(off) <= 45.0)) {
        if (off < 0) early++;
        else late++;
      } else {
        if (off < 0) breakEarly++;
        else breakLate++;
      }

      const lane = e.lane;
      if (lane === 'lane_1') l1++;
      else if (lane === 'lane_2') l2++;
      else if (lane === 'lane_3') l3++;
      else if (lane === 'lane_4') l4++;
      else if (lane === 'lane_5') l5++;
      else if (lane === 'lane_6') l6++;
      else if (lane === 'slide') slide++;
    }

    if (dom.liveExact) dom.liveExact.textContent = exact;
    if (dom.liveNearEarly) dom.liveNearEarly.textContent = early;
    if (dom.liveNearLate) dom.liveNearLate.textContent = late;
    if (dom.liveBreakEarly) dom.liveBreakEarly.textContent = breakEarly;
    if (dom.liveBreakLate) dom.liveBreakLate.textContent = breakLate;
    if (dom.liveLane1) dom.liveLane1.textContent = l1;
    if (dom.liveLane2) dom.liveLane2.textContent = l2;
    if (dom.liveLane3) dom.liveLane3.textContent = l3;
    if (dom.liveLane4) dom.liveLane4.textContent = l4;
    if (dom.liveLane5) dom.liveLane5.textContent = l5;
    if (dom.liveLane6) dom.liveLane6.textContent = l6;
    if (dom.liveLaneSlide) dom.liveLaneSlide.textContent = slide;
  }
  window.updateLiveHud = updateLiveHud;

  function clearLiveHud() {
    if (dom.liveExact) dom.liveExact.textContent = '0';
    if (dom.liveNearEarly) dom.liveNearEarly.textContent = '0';
    if (dom.liveNearLate) dom.liveNearLate.textContent = '0';
    if (dom.liveBreakEarly) dom.liveBreakEarly.textContent = '0';
    if (dom.liveBreakLate) dom.liveBreakLate.textContent = '0';
    if (dom.liveLane1) dom.liveLane1.textContent = '0';
    if (dom.liveLane2) dom.liveLane2.textContent = '0';
    if (dom.liveLane3) dom.liveLane3.textContent = '0';
    if (dom.liveLane4) dom.liveLane4.textContent = '0';
    if (dom.liveLane5) dom.liveLane5.textContent = '0';
    if (dom.liveLane6) dom.liveLane6.textContent = '0';
    if (dom.liveLaneSlide) dom.liveLaneSlide.textContent = '0';
  }

  // ==========================================
  // 4. 雙圖表 Canvas 繪圖與定位線同步
  // ==========================================
  function setupCanvasEvents() {
    window.addEventListener('resize', () => {
      resizeCanvases();
      drawCharts();
    });

    [dom.meanCanvas, dom.scatterCanvas].forEach(canvas => {
      canvas.addEventListener('click', (e) => {
        if (!state.replayData) return;
        const rect = canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const padLeft = 45;
        const padRight = 15;
        const chartW = rect.width - padLeft - padRight;
        if (clickX >= padLeft && clickX <= rect.width - padRight) {
          const ratio = (clickX - padLeft) / chartW;
          const targetSongTime = ratio * state.songDuration;
          const targetVideoTime = targetSongTime + state.songStartSec;
          dom.video.currentTime = Math.max(0, Math.min(state.videoDuration, targetVideoTime));
        }
      });
    });

    dom.scatterCanvas.addEventListener('mousemove', (e) => {
      if (!state.replayData || !state.replayData.events) return;
      const rect = dom.scatterCanvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const padLeft = 45;
      const padRight = 15;
      const padTop = 10;
      const padBottom = 20;
      const chartW = rect.width - padLeft - padRight;
      const chartH = rect.height - padTop - padBottom;

      const timeRatio = (mouseX - padLeft) / chartW;
      const targetTime = timeRatio * state.songDuration;

      const events = state.replayData.events;
      let closest = null;
      let minDis = 15;

      for (let i = 0; i < events.length; i++) {
        const ev = events[i];
        if (Math.abs(ev.timestamp - targetTime) > 3.0) continue;
        const px = padLeft + (ev.timestamp / state.songDuration) * chartW;
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
        dom.noteHoverTooltip.style.left = `${closest.px + 10}px`;
        dom.noteHoverTooltip.style.top = `${closest.py - 16}px`;
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

  function drawCharts() {
    if (!state.replayData) return;
    const currentSongTime = Math.max(0, dom.video.currentTime - state.songStartSec);
    drawMeanChart(currentSongTime);
    drawScatterChart(currentSongTime);
  }

  // 繪製中間表格: 滾動平均偏差趨勢
  function drawMeanChart(currentSongTime) {
    const canvas = dom.meanCanvas;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;

    ctx.clearRect(0, 0, w, h);

    const padLeft = 45;
    const padRight = 15;
    const padTop = 10;
    const padBottom = 20;
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
    ctx.font = '9px "JetBrains Mono"';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    [-25, 0, 25].forEach(val => {
      const y = getY(val);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(w - padRight, y);
      ctx.stroke();
      ctx.fillText(`${val > 0 ? '+' : ''}${val}ms`, padLeft - 6, y);
    });

    // 0ms 中心基準線
    const yZero = getY(0);
    ctx.strokeStyle = '#27ae60';
    ctx.setLineDash([3, 3]);
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
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      series.forEach((pt, idx) => {
        const px = getX(pt.timestamp);
        const py = getY(pt.mean_offset_ms);
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
    }

    // 4. 垂直時間定位線
    if (currentSongTime >= 0 && currentSongTime <= maxT) {
      const cursorX = getX(currentSongTime);
      ctx.strokeStyle = '#ff4757';
      ctx.lineWidth = 1.8;
      ctx.shadowColor = '#ff4757';
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.moveTo(cursorX, padTop);
      ctx.lineTo(cursorX, h - padBottom);
      ctx.stroke();
      ctx.shadowBlur = 0;

      let curVal = 0;
      const pt = series.find(p => Math.abs(p.timestamp - currentSongTime) <= 0.6);
      if (pt) curVal = pt.mean_offset_ms;
      if (dom.meanLiveBadge) {
        dom.meanLiveBadge.classList.remove('hidden');
        dom.meanLiveBadge.textContent = `定位偏差: ${curVal > 0 ? '+' : ''}${curVal.toFixed(1)} ms`;
      }
    } else {
      if (dom.meanLiveBadge) dom.meanLiveBadge.classList.add('hidden');
    }
  }

  // 繪製最下面表格: 各音符偏差散點圖
  function drawScatterChart(currentSongTime) {
    const canvas = dom.scatterCanvas;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;

    ctx.clearRect(0, 0, w, h);

    const padLeft = 45;
    const padRight = 15;
    const padTop = 10;
    const padBottom = 20;
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
    ctx.font = '9px "JetBrains Mono"';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    [-50, -25, 0, 25, 50].forEach(val => {
      const y = getY(val);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(w - padRight, y);
      ctx.stroke();
      ctx.fillText(`${val > 0 ? '+' : ''}${val}ms`, padLeft - 6, y);
    });

    // 0ms 中心基準線
    const yZero = getY(0);
    ctx.strokeStyle = '#27ae60';
    ctx.setLineDash([3, 3]);
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
        ctx.beginPath();
        ctx.moveTo(px, py - 3.5);
        ctx.lineTo(px + 3.5, py);
        ctx.lineTo(px, py + 3.5);
        ctx.lineTo(px - 3.5, py);
        ctx.closePath();
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.arc(px, py, 2.4, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // 4. 垂直時間定位線
    if (currentSongTime >= 0 && currentSongTime <= maxT) {
      const cursorX = getX(currentSongTime);
      ctx.strokeStyle = '#ff4757';
      ctx.lineWidth = 1.8;
      ctx.shadowColor = '#ff4757';
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.moveTo(cursorX, padTop);
      ctx.lineTo(cursorX, h - padBottom);
      ctx.stroke();
      ctx.shadowBlur = 0;

      const nearEv = events.find(e => Math.abs(e.timestamp - currentSongTime) <= 0.2);
      if (nearEv && dom.scatterLiveBadge) {
        dom.scatterLiveBadge.classList.remove('hidden');
        const sign = nearEv.offset_ms > 0 ? '+' : '';
        dom.scatterLiveBadge.textContent = `定位音符: ${nearEv.lane || 'Key'} (${sign}${nearEv.offset_ms}ms)`;
      } else if (dom.scatterLiveBadge) {
        dom.scatterLiveBadge.classList.add('hidden');
      }
    } else {
      if (dom.scatterLiveBadge) dom.scatterLiveBadge.classList.add('hidden');
    }
  }

  // 繪製 X 軸時間刻度
  function drawTimeAxis(ctx, maxT, padLeft, chartW, axisY) {
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = '#64748b';
    ctx.font = '9px "JetBrains Mono"';

    const stepSec = maxT > 100 ? 15 : 10;
    for (let t = 0; t <= maxT; t += stepSec) {
      const x = padLeft + (t / maxT) * chartW;
      ctx.beginPath();
      ctx.moveTo(x, axisY);
      ctx.lineTo(x, axisY + 3);
      ctx.stroke();
      ctx.fillText(formatTime(t, false), x, axisY + 4);
    }
  }

  // ==========================================
  // 5. 資料載入與切換 (直接套用既有分析)
  // ==========================================
  async function loadVideoList() {
    try {
      const data = await backend.getVideos();
      state.videos = data.videos || [];

      dom.videoSelect.innerHTML = '';
      if (state.videos.length === 0) {
        dom.videoSelect.innerHTML = '<option value="">無可用影片，請匯入</option>';
        return;
      }

      state.videos.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = `${v.filename} (${v.analyzed ? '[已分析]' : '[未分析]'})`;
        dom.videoSelect.appendChild(opt);
      });

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

    if (vMeta && vMeta.analyzed) {
      dom.videoAnalyzedBadge.textContent = '已分析 (直接套用)';
      dom.videoAnalyzedBadge.className = 'badge';
      dom.btnStartAnalyze.textContent = '重新分析';
    } else {
      dom.videoAnalyzedBadge.textContent = '尚未分析';
      dom.videoAnalyzedBadge.className = 'badge pending';
      dom.btnStartAnalyze.textContent = '開始分析';
    }

    const filename = vMeta ? vMeta.filename : `${videoId}.mp4`;
    // 本機虛擬主機映射：直接透過 WebView2 串流本機影片，支援完整 60 FPS 與硬體解碼
    dom.video.src = `/data/videos/${filename}`;
    dom.video.load();

    await loadReplayData(videoId);
  }

  async function loadReplayData(videoId) {
    try {
      const data = await backend.getReplay(videoId);

      if (!data.analyzed) {
        state.replayData = null;
        clearKpiDisplay();
        return;
      }

      state.replayData = data;
      state.songStartSec = data.song_start_sec || 0;
      
      const events = data.events || [];
      state.songDuration = (data.video_info && data.video_info.song_duration) || (events.length > 0 ? Math.max(...events.map(e => e.timestamp)) : 120);

      updateKpiDisplay(data.stats);

      resizeCanvases();
      drawCharts();
      updateLiveHud(0);

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
    clearLiveHud();
  }

  // ==========================================
  // 6. 檔案管理與匯入 (支援已分析直接套用)
  // ==========================================
  function setupFileImport() {
    // 匯入影片按鈕：在原生桌面環境下叫出 Windows 檔案選取視窗，直接複製本機影片
    const btnUpload = document.querySelector('.btn-upload');
    if (btnUpload) {
      btnUpload.addEventListener('click', async (e) => {
        if (window.pywebview && window.pywebview.api) {
          e.preventDefault();
          const ret = await backend.selectAndImportVideo();
          if (ret && ret.success) {
            alert(ret.message);
            await loadVideoList();
            if (ret.id) selectVideo(ret.id);
          } else if (ret && ret.message) {
            alert(ret.message);
          }
        }
      });
    }

    dom.videoFileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (file) await uploadVideoFile(file);
    });

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

    dom.btnStartAnalyze.addEventListener('click', () => triggerAnalysis(state.currentVideoId));
    dom.btnReanalyze.addEventListener('click', () => triggerAnalysis(state.currentVideoId));

    dom.btnOpenHtmlReport.addEventListener('click', () => {
      if (state.currentVideoId) {
        backend.openHtmlReport(state.currentVideoId);
      }
    });
  }

  async function uploadVideoFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    dom.analyzeProgressContainer.classList.remove('hidden');
    dom.analyzeProgressBar.style.width = '30%';
    dom.analyzeProgressText.textContent = '正在匯入影片至本機目錄...';

    try {
      const res = await fetch('/api/import_video', { method: 'POST', body: formData });
      const ret = await res.json();
      
      dom.analyzeProgressBar.style.width = '100%';
      dom.analyzeProgressText.textContent = ret.message;
      alert(ret.message);

      await loadVideoList();
      selectVideo(ret.id);
    } catch (e) {
      alert('匯入失敗: ' + e);
    } finally {
      setTimeout(() => dom.analyzeProgressContainer.classList.add('hidden'), 3000);
    }
  }

  async function triggerAnalysis(videoId) {
    if (!videoId) return;
    dom.analyzeProgressContainer.classList.remove('hidden');
    dom.analyzeProgressBar.style.width = '5%';
    dom.analyzeProgressText.textContent = '正在啟動本機 AI 復盤分析...';

    try {
      const ret = await backend.startAnalysis(videoId, 1);

      const pollTimer = setInterval(async () => {
        const status = await backend.getAnalysisStatus(videoId);
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

  window.guiSelectVideo = (id) => {
    dom.navTabs[0].click();
    dom.videoSelect.value = id;
    selectVideo(id);
  };

  window.guiDeleteVideo = async (id) => {
    if (confirm(`確定要刪除 ${id} 影片與分析紀錄嗎？`)) {
      await backend.deleteVideo(id);
      await loadVideoList();
      renderFilesTable();
    }
  };

  async function loadSystemInfo() {
    try {
      const info = await backend.getSystemInfo();
      if (info.device) {
        dom.topGpuBadge.textContent = `GPU: ${info.device}`;
      }
      const modelCfg = info.model || {};
      dom.topModelBadge.textContent = `YOLOv11s Ultimate (${modelCfg.input_size || 960}px)`;
    } catch (e) {}
  }

  let initialized = false;
  async function startApp() {
    if (initialized) return;
    initialized = true;
    await init();
  }

  window.addEventListener('pywebviewready', startApp);
  window.addEventListener('DOMContentLoaded', () => {
    setTimeout(startApp, 500);
  });

})();
