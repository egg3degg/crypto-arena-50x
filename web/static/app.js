// State Management
let chartInstance = null;
let candleChartInstance = null;
let trajectoryChartInstance = null;
let allocationChartInstance = null;
let winLossChartInstance = null;
let strategyBarChartInstance = null;

let currentTab = 'leaderboard';
let activeBotsCache = [];
let activePositionsCache = [];
let activeTradesCache = [];
let activePairsCache = [];

// Leaderboard Filtering & Sorting State
let currentLeaderboardCategory = 'ALL';
let currentLeaderboardSort = 'most_balance';
let currentLeaderboardStatus = 'ALL';
let currentLeaderboardSearch = '';

// Trajectory Chart Tools State
let trajectoryTimeframe = 'ALL';      // '1H', '4H', '12H', '24H', 'ALL'
let trajectoryPreset = 'ALL';         // 'ALL', 'TOP3', 'BOTTOM3', 'CRYPTO', 'POLYMARKET', 'INDIAN_COMM'
let trajectoryDotVisibility = 'ALL';  // 'ALL', 'WINS', 'LOSSES', 'NONE'
let trajectoryScaleMode = 'DOLLAR';   // 'DOLLAR', 'PERCENT'
let hiddenBotDatasetIds = new Set();  // Set of bot_ids manually toggled off
let rawTrajectoryData = null;         // Cached trajectory response

const BASE_BOT_COLORS = {
  'bot_1_alphatrend': '#06b6d4',       // Cyan
  'bot_2_meanrevert': '#ec4899',       // Pink
  'bot_3_breakouthunter': '#10b981',   // Emerald
  'bot_4_adaptivegrid': '#8b5cf6',     // Purple
  'bot_5_smartmoney': '#f59e0b',       // Amber
  'bot_6_polypredictor': '#14b8a6',   // Teal
  'bot_7_bharatbreakout': '#a855f7',  // Violet
  'bot_8_desimeanrevert': '#f97316',  // Orange
  'bot_9_hypergoldsilver': '#fbbf24', // Gold
  'bot_10_polywhalecopy': '#3b82f6',  // Blue
  'bot_11_polyleaderwhale': '#38bdf8',// Sky Blue
  'bot_12_polymicrobot': '#6366f1'    // Indigo
};

function getBotCategory(botId) {
  if (['bot_1_alphatrend', 'bot_2_meanrevert', 'bot_3_breakouthunter', 'bot_4_adaptivegrid', 'bot_5_smartmoney'].includes(botId)) {
    return 'CRYPTO';
  }
  if (['bot_6_polypredictor', 'bot_10_polywhalecopy', 'bot_11_polyleaderwhale', 'bot_12_polymicrobot'].includes(botId)) {
    return 'POLYMARKET';
  }
  if (['bot_7_bharatbreakout', 'bot_8_desimeanrevert'].includes(botId)) {
    return 'INDIAN_STOCKS';
  }
  if (botId === 'bot_9_hypergoldsilver') {
    return 'COMMODITIES';
  }
  return 'OTHER';
}

const ARENA_API_KEY = new URLSearchParams(window.location.search).get('api_key') || localStorage.getItem('arena_api_key') || 'arena-secret-key-2026';
let wsInstance = null;

async function apiPost(url, body = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': ARENA_API_KEY
    },
    body: JSON.stringify(body)
  });
  return res.json();
}

document.addEventListener('DOMContentLoaded', () => {
  initWebSocket();
  initAnalyticsCharts();
  fetchInitialData();
  fetchPolymarketData();
  fetchSentimentData();

  // Low-frequency safety fallback polling only if WebSocket is disconnected
  setInterval(() => {
    if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) {
      fetchInitialData();
    }
  }, 25000);
  setInterval(fetchPolymarketData, 30000);
  setInterval(fetchSentimentData, 45000);
});

function switchTab(tabId, el) {
  currentTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  if (el) {
    el.classList.add('active');
  } else {
    const btn = document.querySelector(`.tab-btn[onclick*="${tabId}"]`);
    if (btn) btn.classList.add('active');
  }

  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) targetPane.classList.add('active');

  if (tabId === 'trajectory') {
    renderTrajectoryChart();
  } else if (tabId === 'analytics') {
    updateAnalyticsCharts();
  } else if (tabId === 'candlestick') {
    const pairSelect = document.getElementById('candlestick-pair-select');
    if (pairSelect) loadCandlestickChart(pairSelect.value);
  } else if (tabId === 'polymarket') {
    fetchPolymarketData();
  } else if (tabId === 'performance') {
    fetchPerformanceReport();
  }
}

// WebSocket Connection for Real-Time Telemetry
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  wsInstance = new WebSocket(wsUrl);

  wsInstance.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'TELEMETRY_UPDATE') {
        renderLeaderboard(data.leaderboard);
        renderTickers(data.tickers);
        renderResearch(data.market_overview);
        if (currentTab === 'trajectory') {
          // Trigger smooth in-place trajectory update
          renderTrajectoryChart();
        }
      }
    } catch (e) {
      console.error("WS Parse Error", e);
    }
  };

  wsInstance.onclose = () => {
    setTimeout(initWebSocket, 4000);
  };
}

async function fetchInitialData() {
  try {
    const [leaderboardRes, tradesRes, positionsRes, researchRes, adjustmentsRes, pairsRes] = await Promise.all([
      fetch('/api/leaderboard').then(r => r.json()),
      fetch('/api/trades').then(r => r.json()),
      fetch('/api/positions').then(r => r.json()),
      fetch('/api/research').then(r => r.json()),
      fetch('/api/adjustments').then(r => r.json()),
      fetch('/api/pairs').then(r => r.json()).catch(() => [])
    ]);

    activeBotsCache = leaderboardRes || [];
    activePositionsCache = positionsRes || [];
    activeTradesCache = tradesRes || [];
    activePairsCache = pairsRes || [];

    renderLeaderboard(leaderboardRes);
    renderTrades(tradesRes);
    renderPositions(positionsRes);
    renderResearchLogs(researchRes);
    renderAdjustments(adjustmentsRes);
    updateAnalyticsCharts();
    if (currentTab === 'trajectory') renderTrajectoryChart();
  } catch (e) {
    console.error("Fetch Data Error", e);
  }
}

async function fetchPolymarketData() {
  try {
    const data = await fetch('/api/polymarket-events').then(r => r.json());
    renderPolymarketMarkets(data);
  } catch (e) {
    console.error("Polymarket Fetch Error", e);
  }
}

async function fetchSentimentData() {
  try {
    const data = await fetch('/api/sentiment').then(r => r.json());
    renderSentiment(data);
  } catch (e) {
    console.error("Sentiment Fetch Error", e);
  }
}

// -------------------------------------------------------------
// TAB 2: BALANCE TRAJECTORY WITH IN-PLACE ZOOM & PAN PRESERVATION
// -------------------------------------------------------------
async function renderTrajectoryChart() {
  try {
    const trajectories = await fetch('/api/equity-trajectory').then(r => r.json());
    if (!trajectories || Object.keys(trajectories).length === 0) return;
    rawTrajectoryData = trajectories;
    renderTrajectoryFromCache();
  } catch (e) {
    console.error("Trajectory chart load error", e);
  }
}

function renderTrajectoryFromCache() {
  const ctx = document.getElementById('trajectoryChartCanvas');
  if (!ctx || !rawTrajectoryData) return;

  // 1. Gather & Filter Timestamps by Timeframe
  let allTimestamps = [];
  Object.values(rawTrajectoryData).forEach(t => {
    t.snapshots.forEach(s => allTimestamps.push(s.timestamp));
  });
  allTimestamps = [...new Set(allTimestamps)].sort();
  if (!allTimestamps.length) return;

  const latestTime = new Date(allTimestamps[allTimestamps.length - 1]).getTime();
  let filteredTimestamps = allTimestamps;

  if (trajectoryTimeframe !== 'ALL') {
    let cutoffMs = 3600 * 1000;
    if (trajectoryTimeframe === '1H') cutoffMs = 3600 * 1000;
    else if (trajectoryTimeframe === '4H') cutoffMs = 4 * 3600 * 1000;
    else if (trajectoryTimeframe === '12H') cutoffMs = 12 * 3600 * 1000;
    else if (trajectoryTimeframe === '24H') cutoffMs = 24 * 3600 * 1000;

    filteredTimestamps = allTimestamps.filter(ts => {
      return (latestTime - new Date(ts).getTime()) <= cutoffMs;
    });
    if (filteredTimestamps.length === 0) filteredTimestamps = allTimestamps;
  }

  const timeLabels = filteredTimestamps.map(ts => {
    const d = new Date(ts);
    return `${d.toLocaleDateString([], {month:'short', day:'numeric'})} ${d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}`;
  });

  // 2. Select & Rank Bots for Cohort Presets
  let botEntries = Object.entries(rawTrajectoryData);
  
  // Sort entries by latest equity for ranking
  const sortedByEquity = [...botEntries].sort((a, b) => {
    const aLast = a[1].snapshots.length ? a[1].snapshots[a[1].snapshots.length - 1].total_equity : 50;
    const bLast = b[1].snapshots.length ? b[1].snapshots[b[1].snapshots.length - 1].total_equity : 50;
    return bLast - aLast;
  });

  const selectEl = document.getElementById('trajectory-bot-select');
  const selectedSingleBot = selectEl ? selectEl.value : 'ALL';

  if (selectedSingleBot !== 'ALL') {
    botEntries = botEntries.filter(([id]) => id === selectedSingleBot);
  } else if (trajectoryPreset === 'TOP3') {
    botEntries = sortedByEquity.slice(0, 3);
  } else if (trajectoryPreset === 'BOTTOM3') {
    botEntries = sortedByEquity.slice(-3);
  } else if (trajectoryPreset === 'CRYPTO') {
    botEntries = botEntries.filter(([id]) => getBotCategory(id) === 'CRYPTO');
  } else if (trajectoryPreset === 'POLYMARKET') {
    botEntries = botEntries.filter(([id]) => getBotCategory(id) === 'POLYMARKET');
  } else if (trajectoryPreset === 'INDIAN_COMM') {
    botEntries = botEntries.filter(([id]) => ['INDIAN_STOCKS', 'COMMODITIES'].includes(getBotCategory(id)));
  }

  // 3. Build Datasets
  let datasets = [];
  botEntries.forEach(([botId, botData]) => {
    const isHidden = hiddenBotDatasetIds.has(botId);
    const color = BASE_BOT_COLORS[botId] || '#06b6d4';
    
    // Map snapshot equity
    const snapMap = {};
    botData.snapshots.forEach(s => {
      const eq = (s.total_equity !== undefined && s.total_equity !== null) ? Number(s.total_equity) : 50.0;
      snapMap[s.timestamp] = eq;
    });

    let lastVal = 50.0;
    if (botData.snapshots.length > 0) {
      lastVal = Number(botData.snapshots[0].total_equity || 50.0);
    }

    const dataPoints = filteredTimestamps.map(ts => {
      if (snapMap[ts] !== undefined) {
        lastVal = snapMap[ts];
      }
      if (trajectoryScaleMode === 'PERCENT') {
        return ((lastVal - 50.0) / 50.0) * 100.0; // ROI %
      }
      return lastVal; // Absolute $
    });

    // Trade Dot Overlays
    const pointBackgroundColors = [];
    const pointBorderColors = [];
    const pointRadiuses = [];
    const pointTradeData = [];

    filteredTimestamps.forEach((ts) => {
      const matchingTrades = botData.trade_markers.filter(m => {
        return Math.abs(new Date(m.timestamp) - new Date(ts)) < 25000;
      });

      let showDot = false;
      let tradeMatch = null;

      if (matchingTrades.length > 0 && trajectoryDotVisibility !== 'NONE') {
        const t = matchingTrades[0];
        if (trajectoryDotVisibility === 'ALL') {
          showDot = true;
        } else if (trajectoryDotVisibility === 'WINS' && (t.side === 'BUY' || t.realized_pnl >= 0)) {
          showDot = true;
        } else if (trajectoryDotVisibility === 'LOSSES' && t.side === 'SELL' && t.realized_pnl < 0) {
          showDot = true;
        }
        tradeMatch = t;
      }

      if (showDot && tradeMatch) {
        pointRadiuses.push(8);
        pointBackgroundColors.push(tradeMatch.dot_color);
        pointBorderColors.push('#ffffff');
        pointTradeData.push(tradeMatch);
      } else {
        pointRadiuses.push(0); // Clean continuous line without noisy baseline dots
        pointBackgroundColors.push(color);
        pointBorderColors.push(color);
        pointTradeData.push(null);
      }
    });

    datasets.push({
      botId: botId,
      label: botData.name,
      data: dataPoints,
      borderColor: color,
      backgroundColor: color + '1a',
      borderWidth: 2.2,
      hidden: isHidden,
      fill: botEntries.length === 1,
      tension: 0.2,
      pointRadius: pointRadiuses,
      pointBackgroundColor: pointBackgroundColors,
      pointBorderColor: pointBorderColors,
      pointHoverRadius: 10,
      tradeDetails: pointTradeData
    });
  });

  // 4. Render Interactive Legend Chips
  renderLegendChips(botEntries);

  // 5. Update in-place or Initialize Chart.js with Zoom Plugin
  if (trajectoryChartInstance) {
    trajectoryChartInstance.data.labels = timeLabels;
    trajectoryChartInstance.data.datasets = datasets;
    trajectoryChartInstance.update('none'); // In-place update preserving user zoom level & pan position!
    return;
  }

  trajectoryChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: timeLabels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'nearest', intersect: true },
      scales: {
        x: {
          grid: { color: '#1e293b' },
          ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 }, maxRotation: 0 }
        },
        y: {
          grid: { color: '#1e293b' },
          ticks: {
            color: '#94a3b8',
            font: { family: 'JetBrains Mono', size: 11 },
            callback: v => trajectoryScaleMode === 'PERCENT' ? `${v >= 0 ? '+' : ''}${v.toFixed(2)}%` : `$${v.toFixed(2)}`
          }
        }
      },
      plugins: {
        legend: { display: false }, // We use custom chips for better multi-touch & click control
        zoom: {
          pan: {
            enabled: true,
            mode: 'x'
          },
          zoom: {
            wheel: { enabled: true, speed: 0.1 },
            pinch: { enabled: true },
            mode: 'x'
          }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#38bdf8',
          bodyColor: '#f8fafc',
          borderColor: '#1e293b',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: function(context) {
              const dataset = context.dataset;
              const idx = context.dataIndex;
              const val = context.parsed.y;
              const trade = dataset.tradeDetails ? dataset.tradeDetails[idx] : null;

              const valFormatted = trajectoryScaleMode === 'PERCENT' ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}% ROI` : `$${val.toFixed(2)}`;

              if (trade) {
                const sideEmoji = trade.side === 'BUY' ? '🟢 BUY ENTRY' : (trade.realized_pnl >= 0 ? '🟢 WIN EXIT' : '🔴 LOSS EXIT');
                const pnlStr = trade.side === 'SELL' ? ` | PnL: ${trade.realized_pnl >= 0 ? '+' : ''}$${trade.realized_pnl.toFixed(2)}` : '';
                return [
                  `📊 ${dataset.label}: ${valFormatted}`,
                  `⚡ ${sideEmoji} ${trade.symbol} @ $${trade.price.toFixed(2)}${pnlStr}`,
                  `📝 ${trade.reason}`
                ];
              }
              return `📊 ${dataset.label}: ${valFormatted}`;
            }
          }
        }
      }
    }
  });
}

// Render Interactive Bot Toggle Chips
function renderLegendChips(botEntries) {
  const container = document.getElementById('interactive-legend-chips');
  if (!container) return;

  let html = '';
  botEntries.forEach(([botId, botData]) => {
    const isHidden = hiddenBotDatasetIds.has(botId);
    const color = BASE_BOT_COLORS[botId] || '#06b6d4';
    html += `
      <div class="legend-chip ${isHidden ? 'hidden' : ''}" onclick="toggleBotDatasetVisibility('${botId}')">
        <span class="chip-dot" style="background-color: ${color};"></span>
        <span>${botData.name}</span>
      </div>
    `;
  });
  container.innerHTML = html;
}

function toggleBotDatasetVisibility(botId) {
  if (hiddenBotDatasetIds.has(botId)) {
    hiddenBotDatasetIds.delete(botId);
  } else {
    hiddenBotDatasetIds.add(botId);
  }
  renderTrajectoryFromCache();
}

// Chart Controls Toolbar Handlers
function setTimeframe(tf) {
  trajectoryTimeframe = tf;
  document.querySelectorAll('#trajectory-timeframe-pills .chart-pill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.trim().startsWith(tf));
  });
  renderTrajectoryFromCache();
}

function setTrajectoryPreset(preset) {
  trajectoryPreset = preset;
  const selectEl = document.getElementById('trajectory-bot-select');
  if (selectEl) selectEl.value = 'ALL';

  document.querySelectorAll('#trajectory-preset-pills .chart-pill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('onclick').includes(preset));
  });
  renderTrajectoryFromCache();
}

function setDotVisibility(mode) {
  trajectoryDotVisibility = mode;
  document.querySelectorAll('#trajectory-dots-pills .chart-pill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('onclick').includes(mode));
  });
  renderTrajectoryFromCache();
}

function setScaleMode(mode) {
  trajectoryScaleMode = mode;
  document.querySelectorAll('#trajectory-scale-pills .chart-pill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('onclick').includes(mode));
  });
  renderTrajectoryFromCache();
}

function handleSingleBotSelect() {
  const selectEl = document.getElementById('trajectory-bot-select');
  const val = selectEl ? selectEl.value : 'ALL';
  if (val !== 'ALL') {
    trajectoryPreset = 'CUSTOM';
    document.querySelectorAll('#trajectory-preset-pills .chart-pill-btn').forEach(btn => btn.classList.remove('active'));
  } else {
    trajectoryPreset = 'ALL';
    document.querySelectorAll('#trajectory-preset-pills .chart-pill-btn').forEach(btn => {
      if (btn.textContent.includes('All')) btn.classList.add('active');
    });
  }
  renderTrajectoryFromCache();
}

function handleZoomIn() {
  if (trajectoryChartInstance) trajectoryChartInstance.zoom(1.25);
}

function handleZoomOut() {
  if (trajectoryChartInstance) trajectoryChartInstance.zoom(0.8);
}

function handleResetZoom() {
  if (trajectoryChartInstance) trajectoryChartInstance.resetZoom();
}

// Render Polymarket Prediction Events
function renderPolymarketMarkets(markets) {
  const container = document.getElementById('poly-markets-container');
  if (!container || !markets || !markets.length) return;

  let html = '';
  markets.forEach(m => {
    const yesPct = Math.round(m.yes_price * 100);
    const noPct = 100 - yesPct;
    html += `
      <div class="poly-card">
        <div style="font-size:11px; color:var(--accent-purple); font-weight:700; margin-bottom:4px;">${m.category}</div>
        <div class="poly-q">${m.question}</div>
        
        <div class="poly-odds-bar">
          <div class="poly-yes-bar" style="width: ${yesPct}%;"></div>
          <div class="poly-no-bar" style="width: ${noPct}%;"></div>
        </div>

        <div class="poly-odds-labels">
          <span style="color:var(--accent-green);">YES: $${m.yes_price.toFixed(2)} (${yesPct}%)</span>
          <span style="color:var(--accent-red);">NO: $${m.no_price.toFixed(2)} (${noPct}%)</span>
        </div>

        <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:11px; color:var(--text-muted);">
          <span>24h Vol: $${Math.round(m.volume_24h).toLocaleString()}</span>
          <span>Resolves: ${m.end_date || 'Upcoming'}</span>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// Render Sentiment Radar
function renderSentiment(data) {
  if (!data) return;
  const scoreEl = document.getElementById('fng-score');
  const descEl = document.getElementById('fng-desc');
  if (scoreEl) {
    const score = data.fear_greed_score || 50;
    scoreEl.textContent = `${score} / 100`;
    scoreEl.style.color = score > 60 ? 'var(--accent-green)' : (score < 40 ? 'var(--accent-red)' : 'var(--accent-yellow)');
  }
  if (descEl) {
    descEl.innerHTML = `Classification: <strong>${data.sentiment_classification || 'Neutral'}</strong> | Whale Sentiment: <strong>${data.whale_sentiment || 'Active'}</strong> | Risk: <strong>${data.market_risk_index || 'Moderate'}</strong>`;
  }
}

// Render Leaderboard & Bot Controls with Dynamic Sorting & Category Filtering
function renderLeaderboard(bots) {
  if (!bots || !bots.length) return;
  activeBotsCache = bots;
  renderFilteredLeaderboard();
}

function applyLeaderboardFilters() {
  const sortSelect = document.getElementById('leaderboard-sort-select');
  const statusSelect = document.getElementById('leaderboard-status-select');
  const searchInput = document.getElementById('leaderboard-search-input');

  if (sortSelect) currentLeaderboardSort = sortSelect.value;
  if (statusSelect) currentLeaderboardStatus = statusSelect.value;
  if (searchInput) currentLeaderboardSearch = searchInput.value.toLowerCase().trim();

  renderFilteredLeaderboard();
}

function setLeaderboardCategory(cat) {
  currentLeaderboardCategory = cat;
  document.querySelectorAll('#category-filter-pills .pill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('onclick').includes(cat));
  });
  renderFilteredLeaderboard();
}

function renderFilteredLeaderboard() {
  if (!activeBotsCache || !activeBotsCache.length) return;
  const container = document.getElementById('leaderboard-container');
  if (!container) return;

  let bots = [...activeBotsCache];
  let totalArenaPnl = 0;
  let totalCap = 0;

  activeBotsCache.forEach(b => {
    totalArenaPnl += b.total_pnl;
    totalCap += b.current_equity;
  });

  // 1. Market Category Filter
  if (currentLeaderboardCategory !== 'ALL') {
    bots = bots.filter(b => getBotCategory(b.bot_id) === currentLeaderboardCategory);
  }

  // 2. Status Filter
  if (currentLeaderboardStatus === 'ACTIVE') {
    bots = bots.filter(b => b.is_active !== false);
  } else if (currentLeaderboardStatus === 'PAUSED') {
    bots = bots.filter(b => b.is_active === false);
  }

  // 3. Search Filter
  if (currentLeaderboardSearch) {
    bots = bots.filter(b => 
      b.name.toLowerCase().includes(currentLeaderboardSearch) ||
      (b.strategy_name && b.strategy_name.toLowerCase().includes(currentLeaderboardSearch)) ||
      b.bot_id.toLowerCase().includes(currentLeaderboardSearch)
    );
  }

  // 4. Sorting
  switch (currentLeaderboardSort) {
    case 'most_balance':
      bots.sort((a, b) => b.current_equity - a.current_equity);
      break;
    case 'least_balance':
      bots.sort((a, b) => a.current_equity - b.current_equity);
      break;
    case 'most_trades':
      bots.sort((a, b) => (b.winning_trades + b.losing_trades + (b.open_positions_count || 0)) - (a.winning_trades + a.losing_trades + (a.open_positions_count || 0)));
      break;
    case 'least_trades':
      bots.sort((a, b) => (a.winning_trades + a.losing_trades + (a.open_positions_count || 0)) - (b.winning_trades + b.losing_trades + (b.open_positions_count || 0)));
      break;
    case 'highest_winrate':
      bots.sort((a, b) => b.win_rate - a.win_rate);
      break;
    case 'highest_pnl':
      bots.sort((a, b) => b.total_pnl - a.total_pnl);
      break;
    case 'lowest_pnl':
      bots.sort((a, b) => a.total_pnl - b.total_pnl);
      break;
    case 'alphabetical':
      bots.sort((a, b) => a.name.localeCompare(b.name));
      break;
    default:
      bots.sort((a, b) => b.current_equity - a.current_equity);
  }

  let html = '';
  if (bots.length === 0) {
    html = `<div style="grid-column: 1/-1; text-align:center; padding:40px; color:var(--text-muted);">No bots matched your search or category filter.</div>`;
  } else {
    bots.forEach((bot, index) => {
      const rank = index + 1;
      const rankClass = rank === 1 ? 'rank-1' : (rank === 2 ? 'rank-2' : (rank === 3 ? 'rank-3' : 'rank-other'));
      const rankLabel = rank === 1 ? '🥇 #1' : (rank === 2 ? '🥈 #2' : (rank === 3 ? '🥉 #3' : `#${rank}`));
      const pnlClass = bot.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
      const pnlSign = bot.total_pnl >= 0 ? '+' : '';
      const isActive = bot.is_active !== false;
      const totalTrades = bot.winning_trades + bot.losing_trades;

      // Category and Data Authenticity badge
      const cat = getBotCategory(bot.bot_id);
      let catBadge = '';
      if (cat === 'CRYPTO') {
        catBadge = '<span style="font-size:10px; background:rgba(6,182,212,0.15); border:1px solid rgba(6,182,212,0.35); padding:2px 6px; border-radius:4px; color:var(--accent-cyan);">🪙 Crypto (Live Binance Feed)</span>';
      } else if (cat === 'POLYMARKET') {
        catBadge = '<span style="font-size:10px; background:rgba(168,85,247,0.15); border:1px solid rgba(168,85,247,0.35); padding:2px 6px; border-radius:4px; color:var(--accent-purple);">🔮 Polymarket (Live Gamma + Whale Model)</span>';
      } else if (cat === 'INDIAN_STOCKS') {
        catBadge = '<span style="font-size:10px; background:rgba(245,158,11,0.18); border:1px solid rgba(245,158,11,0.45); padding:2px 6px; border-radius:4px; color:var(--accent-yellow);" title="Paper model using simulated price motion">⚠️ 🇮🇳 NSE (Simulated Model)</span>';
      } else if (cat === 'COMMODITIES') {
        catBadge = '<span style="font-size:10px; background:rgba(245,158,11,0.18); border:1px solid rgba(245,158,11,0.45); padding:2px 6px; border-radius:4px; color:var(--accent-yellow);" title="Paper model using synthetic spread">⚠️ 🥇 Gold/Silver (Synthetic Model)</span>';
      } else {
        catBadge = '<span style="font-size:10px; background:rgba(255,255,255,0.06); padding:2px 6px; border-radius:4px; color:var(--text-muted);">Generic</span>';
      }

      html += `
        <div class="bot-card ${isActive ? '' : 'paused'}" id="card-${bot.bot_id}">
          <div class="card-top-row">
            <div class="bot-status-pill ${isActive ? 'status-active' : 'status-paused'}" onclick="toggleBotStatus('${bot.bot_id}', ${!isActive})">
              ${isActive ? '● Active' : '⏸ Paused'}
            </div>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; justify-content:flex-end;">
              ${catBadge}
              <div class="rank-badge ${rankClass}">${rankLabel}</div>
            </div>
          </div>

          <div class="bot-name" style="display:flex; justify-content:space-between; align-items:center;">
            <span>${bot.name}</span>
            <span style="font-size:11px; font-weight:600;">${bot.health_status === 'DEGRADING' ? '🟡 Degrading' : (bot.health_status === 'PAUSED_DECAY' ? '🔴 Paused' : '🟢 Healthy')}</span>
          </div>
          <div class="bot-strat-tag">${bot.strategy_name}</div>

          <div class="bot-stats-grid">
            <div class="stat-item">
              <span class="k">Total Equity</span>
              <span class="v" style="color:var(--text-main); font-weight:800;">$${bot.current_equity.toFixed(2)}</span>
            </div>
            <div class="stat-item">
              <span class="k">PnL / ROI</span>
              <span class="v ${pnlClass}">${pnlSign}$${bot.total_pnl.toFixed(2)} (${pnlSign}${bot.roi_pct.toFixed(2)}%)</span>
            </div>
            <div class="stat-item">
              <span class="k">Win Rate</span>
              <span class="v">${bot.win_rate.toFixed(1)}% <small style="color:var(--text-muted)">(${bot.winning_trades}W / ${bot.losing_trades}L)</small></span>
            </div>
            <div class="stat-item">
              <span class="k">Allocated Stake</span>
              <span class="v" style="color:var(--accent-cyan); font-weight:700;">$${(bot.allocated_stake_usd || 25.0).toFixed(2)}</span>
            </div>
          </div>

          <div style="font-size:11px; color:var(--text-muted); margin-bottom:12px; display:flex; justify-content:space-between;">
            <span>Free Cash: <strong style="color:var(--accent-green);">$${bot.available_balance.toFixed(2)}</strong></span>
            <span>Max DD: <strong style="color:${bot.max_drawdown > 3 ? 'var(--accent-red)' : 'var(--text-muted)'};">${bot.max_drawdown.toFixed(2)}%</strong></span>
          </div>

          <div class="card-control-toolbar">
            <button class="btn-ctrl" onclick="openEditParamsModal('${bot.bot_id}')">⚙️ Params</button>
            <button class="btn-ctrl" onclick="openManualTradeModal('${bot.bot_id}')">⚡ Order</button>
            <button class="btn-ctrl btn-ctrl-danger" onclick="liquidateBot('${bot.bot_id}')">🛑 Liquidate</button>
          </div>
        </div>
      `;
    });
  }

  container.innerHTML = html;

  // Header metric update
  const pnlEl = document.getElementById('header-total-pnl');
  if (pnlEl) {
    pnlEl.textContent = `${totalArenaPnl >= 0 ? '+' : ''}$${totalArenaPnl.toFixed(2)}`;
    pnlEl.className = `metric-value ${totalArenaPnl >= 0 ? 'pnl-pos' : 'pnl-neg'}`;
  }
  const countEl = document.getElementById('header-bot-count');
  if (countEl) {
    countEl.textContent = `${activeBotsCache.length} Bots ($${totalCap.toFixed(0)})`;
  }
}

// Candlestick Chart (Tab 4)
async function loadCandlestickChart(symbol) {
  try {
    const candles = await fetch(`/api/ohlcv/${encodeURIComponent(symbol)}`).then(r => r.json());
    if (!candles || !candles.length) return;

    const ctx = document.getElementById('candleChartCanvas');
    if (!ctx) return;

    if (candleChartInstance) {
      candleChartInstance.destroy();
    }

    const labels = candles.map(c => new Date(c.time).toLocaleTimeString());
    const closePrices = candles.map(c => c.close);
    const highPrices = candles.map(c => c.high);
    const lowPrices = candles.map(c => c.low);

    candleChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: `${symbol} Price`,
            data: closePrices,
            borderColor: '#06b6d4',
            backgroundColor: 'rgba(6, 182, 212, 0.1)',
            fill: true,
            tension: 0.1,
            pointRadius: 2
          },
          {
            label: 'High Price',
            data: highPrices,
            borderColor: 'rgba(16, 185, 129, 0.4)',
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false
          },
          {
            label: 'Low Price',
            data: lowPrices,
            borderColor: 'rgba(239, 68, 68, 0.4)',
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', callback: v => `$${v.toFixed(2)}` } }
        },
        plugins: { legend: { labels: { color: '#f8fafc', font: { family: 'JetBrains Mono' } } } }
      }
    });
  } catch (e) {
    console.error("Candle chart load error", e);
  }
}

// Backtest Execution (Tab 6)
async function handleRunBacktest(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-run-bt');
  btn.textContent = "⏳ Running Vectorized Simulation...";
  btn.disabled = true;

  const payload = {
    strategy_type: document.getElementById('bt-strat-type').value,
    symbol: document.getElementById('bt-symbol').value,
    take_profit_pct: parseFloat(document.getElementById('bt-tp').value),
    stop_loss_pct: parseFloat(document.getElementById('bt-sl').value),
    stake_usd: parseFloat(document.getElementById('bt-stake').value)
  };

  try {
    const res = await fetch('/api/backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    btn.textContent = "⚡ Execute 30-Day Backtest";
    btn.disabled = false;

    const resBox = document.getElementById('bt-results-content');
    if (res.error) {
      resBox.innerHTML = `<p style="color:var(--accent-red);">${res.error}</p>`;
      return;
    }

    const pnlClass = res.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
    const pnlSign = res.total_pnl >= 0 ? '+' : '';

    resBox.innerHTML = `
      <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; margin-bottom:18px;">
        <div class="bt-stat-badge">
          <div class="num ${pnlClass}">${pnlSign}$${res.total_pnl.toFixed(2)}</div>
          <div class="lbl">Total PnL (${pnlSign}${res.roi_pct.toFixed(2)}%)</div>
        </div>
        <div class="bt-stat-badge">
          <div class="num">${res.win_rate.toFixed(1)}%</div>
          <div class="lbl">Win Rate (${res.total_trades} Trades)</div>
        </div>
        <div class="bt-stat-badge">
          <div class="num">${res.profit_factor.toFixed(2)}</div>
          <div class="lbl">Profit Factor</div>
        </div>
        <div class="bt-stat-badge">
          <div class="num pnl-neg">${res.max_drawdown.toFixed(2)}%</div>
          <div class="lbl">Max Drawdown</div>
        </div>
      </div>

      <h4 style="font-size:13px; color:var(--text-muted); margin-bottom:8px;">Recent Simulated Trades:</h4>
      <div class="log-table-wrapper">
        <table class="data-table">
          <thead>
            <tr><th>Entry Time</th><th>Entry Price</th><th>Exit Price</th><th>Trade PnL</th><th>Outcome</th></tr>
          </thead>
          <tbody>
            ${res.trades.map(t => `
              <tr>
                <td style="color:var(--text-muted);">${new Date(t.entry_time).toLocaleDateString()}</td>
                <td>$${t.entry_price.toFixed(2)}</td>
                <td>$${t.exit_price.toFixed(2)}</td>
                <td class="${t.is_win ? 'pnl-pos' : 'pnl-neg'}">${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)} (${t.pnl_pct}%)</td>
                <td>${t.is_win ? '🟢 WIN' : '🔴 LOSS'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    btn.textContent = "⚡ Execute 30-Day Backtest";
    btn.disabled = false;
    alert("Backtest error: " + err);
  }
}

// Bot Control Actions
async function toggleBotStatus(botId, newActiveState) {
  try {
    await apiPost(`/api/bots/${botId}/toggle`, { is_active: newActiveState });
    fetchInitialData();
  } catch (e) {
    alert("Error toggling bot: " + e);
  }
}

async function toggleAllBots(isActive) {
  if (!activeBotsCache.length) return;
  for (const b of activeBotsCache) {
    await apiPost(`/api/bots/${b.bot_id}/toggle`, { is_active: isActive });
  }
  fetchInitialData();
}

async function liquidateBot(botId) {
  if (!confirm(`Are you sure you want to emergency close all open positions for bot '${botId}' at market price?`)) return;
  try {
    const res = await apiPost(`/api/bots/${botId}/liquidate`);
    alert(`Successfully closed ${res.closed_trades_count} open positions.`);
    fetchInitialData();
  } catch (e) {
    alert("Error liquidating bot: " + e);
  }
}

// Modals
function openModal(modalId) { document.getElementById(modalId).classList.add('active'); }
function closeModal(modalId) { document.getElementById(modalId).classList.remove('active'); }

function openCreateBotModal() { openModal('create-bot-modal'); }

async function handleCreateBotSubmit(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById('new-bot-name').value,
    strategy_type: document.getElementById('new-bot-strat-type').value,
    initial_capital: parseFloat(document.getElementById('new-bot-capital').value),
    description: document.getElementById('new-bot-desc').value,
    params: {
      stake_usd: parseFloat(document.getElementById('new-bot-stake').value),
      take_profit_pct: parseFloat(document.getElementById('new-bot-tp').value) / 100.0,
      stop_loss_pct: parseFloat(document.getElementById('new-bot-sl').value) / 100.0
    }
  };

  try {
    const res = await apiPost('/api/bots/create', payload);
    if (res.success) {
      closeModal('create-bot-modal');
      alert(`Bot '${payload.name}' deployed successfully into the arena!`);
      fetchInitialData();
    }
  } catch (err) {
    alert("Error creating bot: " + err);
  }
}

function openEditParamsModal(botId) {
  const bot = activeBotsCache.find(b => b.bot_id === botId);
  if (!bot) return;

  document.getElementById('edit-bot-id').value = botId;
  document.getElementById('edit-bot-title').textContent = bot.name;
  const p = bot.active_strategy_params || {};

  document.getElementById('edit-tp-pct').value = ((p.take_profit_pct || 0.04) * 100).toFixed(1);
  document.getElementById('edit-sl-pct').value = ((p.stop_loss_pct || 0.02) * 100).toFixed(1);
  document.getElementById('edit-trail-pct').value = p.trailing_stop_pct ? (p.trailing_stop_pct * 100).toFixed(1) : '0';
  document.getElementById('edit-stake-usd').value = p.stake_usd || 25.0;

  openModal('edit-params-modal');
}

async function handleEditParamsSubmit(e) {
  e.preventDefault();
  const botId = document.getElementById('edit-bot-id').value;
  const trailVal = parseFloat(document.getElementById('edit-trail-pct').value);

  const payload = {
    take_profit_pct: parseFloat(document.getElementById('edit-tp-pct').value) / 100.0,
    stop_loss_pct: parseFloat(document.getElementById('edit-sl-pct').value) / 100.0,
    trailing_stop_pct: trailVal > 0 ? trailVal / 100.0 : null,
    stake_usd: parseFloat(document.getElementById('edit-stake-usd').value)
  };

  try {
    const res = await apiPost(`/api/bots/${botId}/params`, payload);
    if (res.success) {
      closeModal('edit-params-modal');
      alert(`Parameters for '${botId}' updated live!`);
      fetchInitialData();
    }
  } catch (err) {
    alert("Error updating parameters: " + err);
  }
}

function openManualTradeModal(botId) {
  const bot = activeBotsCache.find(b => b.bot_id === botId);
  document.getElementById('manual-bot-id').value = botId;
  document.getElementById('manual-bot-title').textContent = bot ? bot.name : botId;
  openModal('manual-trade-modal');
}

async function handleManualTradeSubmit(e) {
  e.preventDefault();
  const botId = document.getElementById('manual-bot-id').value;
  const payload = {
    symbol: document.getElementById('manual-symbol').value,
    side: document.getElementById('manual-side').value,
    usd_amount: parseFloat(document.getElementById('manual-amount').value)
  };

  try {
    const res = await apiPost(`/api/bots/${botId}/manual-order`, payload);
    closeModal('manual-trade-modal');
    if (res.success) {
      alert(`Manual ${payload.side} order executed for ${payload.symbol}!`);
      fetchInitialData();
    } else {
      alert("Order rejected: Insufficient balance or maximum open trades reached.");
    }
  } catch (err) {
    alert("Error executing order: " + err);
  }
}

// Multi-Coin Manager Modal
function openPairsModal() {
  renderPairsList();
  openModal('pairs-modal');
}

function renderPairsList() {
  const container = document.getElementById('active-pairs-list');
  if (!container) return;
  container.innerHTML = activePairsCache.map(p => `
    <div style="background:rgba(255,255,255,0.06); padding:6px 12px; border-radius:6px; font-family:'JetBrains Mono'; font-size:12px; display:flex; align-items:center; gap:8px;">
      <span>${p}</span>
      <span onclick="handleRemovePair('${p}')" style="cursor:pointer; color:var(--accent-red); font-weight:800;">&times;</span>
    </div>
  `).join('');
}

async function handleAddPair() {
  const input = document.getElementById('add-pair-input');
  const val = input.value.trim().toUpperCase();
  if (!val) return;
  const res = await apiPost('/api/pairs/add', { symbol: val });
  if (res.success) {
    activePairsCache = res.pairs;
    renderPairsList();
    input.value = '';
  }
}

async function handleRemovePair(pair) {
  const res = await apiPost('/api/pairs/remove', { symbol: pair });
  if (res.success) {
    activePairsCache = res.pairs;
    renderPairsList();
  }
}

// Telegram Setup Modal
function openTelegramModal() { openModal('telegram-modal'); }

async function handleSaveTelegram() {
  const token = document.getElementById('tg-token').value.trim();
  const chat_id = document.getElementById('tg-chat-id').value.trim();
  if (!token || !chat_id) {
    alert("Please enter both Bot Token and Chat ID.");
    return;
  }
  const res = await apiPost('/api/telegram/test', { token, chat_id });
  if (res.success) {
    closeModal('telegram-modal');
    alert("✔ " + res.message);
  } else {
    alert("Error: " + res.message);
  }
}

// Visual Analytics & Pie Charts (Tab 5)
function initAnalyticsCharts() {
  const allocCtx = document.getElementById('allocationPieChart');
  if (allocCtx) {
    allocationChartInstance = new Chart(allocCtx, {
      type: 'doughnut',
      data: {
        labels: ['Liquid USDT', 'SOL', 'ETH', 'BTC', 'AVAX', 'NEAR', 'SUI', 'PENGU', 'NSE Stocks', 'Gold/Silver', 'Polymarket'],
        datasets: [{
          data: [450, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          backgroundColor: ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#ef4444', '#10b981', '#ec4899', '#14b8a6', '#fbbf24', '#f97316', '#a855f7'],
          borderWidth: 2,
          borderColor: '#111927'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: '#f8fafc', font: { family: 'JetBrains Mono', size: 11 } } } }
      }
    });
  }

  const winLossCtx = document.getElementById('winLossDonutChart');
  if (winLossCtx) {
    winLossChartInstance = new Chart(winLossCtx, {
      type: 'pie',
      data: {
        labels: ['Winning Trades', 'Losing Trades'],
        datasets: [{
          data: [1, 0],
          backgroundColor: ['#10b981', '#ef4444'],
          borderWidth: 2,
          borderColor: '#111927'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { color: '#f8fafc', font: { family: 'JetBrains Mono', size: 11 } } } }
      }
    });
  }

  const barCtx = document.getElementById('strategyBarChart');
  if (barCtx) {
    strategyBarChartInstance = new Chart(barCtx, {
      type: 'bar',
      data: {
        labels: ['AlphaTrend', 'MeanRevert', 'Breakout', 'Grid', 'SmartMoney', 'PolyPredictor', 'BharatBreakout', 'DesiMeanRevert', 'HyperGoldSilver'],
        datasets: [{
          label: 'Total PnL ($)',
          data: [0, 0, 0, 0, 0, 0, 0, 0, 0],
          backgroundColor: BASE_BOT_COLORS,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } } },
          y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', callback: v => `$${v}` } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }
}

function updateAnalyticsCharts() {
  if (!activeBotsCache.length) return;

  let totalCap = 0;
  let totalAvailable = 0;
  let totalWins = 0;
  let totalLosses = 0;
  let grossProfit = 0;
  let grossLoss = 0;
  let totalVol = 0;

  activeBotsCache.forEach(b => {
    totalCap += b.current_equity;
    totalAvailable += b.available_balance;
    totalWins += b.winning_trades;
    totalLosses += b.losing_trades;
  });

  const pairAlloc = { 'SOL/USDT': 0, 'ETH/USDT': 0, 'BTC/USDT': 0, 'AVAX/USDT': 0, 'NEAR/USDT': 0, 'SUI/USDT': 0, 'PENGU/USDT': 0, 'NSE': 0, 'COMMODITY': 0, 'POLY': 0 };
  activePositionsCache.forEach(p => {
    const sym = p.symbol;
    if (pairAlloc[sym] !== undefined) {
      pairAlloc[sym] += p.cost_basis || 0;
    } else if (sym.includes('RELIANCE') || sym.includes('TATAMOTORS') || sym.includes('NIFTY')) {
      pairAlloc['NSE'] += p.cost_basis || 0;
    } else if (sym.includes('GOLD') || sym.includes('SILVER')) {
      pairAlloc['COMMODITY'] += p.cost_basis || 0;
    } else {
      pairAlloc['POLY'] += p.cost_basis || 0;
    }
  });

  activeTradesCache.forEach(t => {
    totalVol += t.cost_or_proceeds || 0;
    if (t.realized_pnl > 0) grossProfit += t.realized_pnl;
    else if (t.realized_pnl < 0) grossLoss += Math.abs(t.realized_pnl);
  });

  const kpiCap = document.getElementById('kpi-total-capital');
  if (kpiCap) kpiCap.textContent = `$${totalCap.toFixed(2)}`;

  const totalTrades = totalWins + totalLosses;
  const overallWinRate = totalTrades > 0 ? (totalWins / totalTrades * 100.0) : 0.0;
  const kpiWin = document.getElementById('kpi-win-rate');
  if (kpiWin) kpiWin.textContent = `${overallWinRate.toFixed(1)}%`;

  const kpiTrades = document.getElementById('kpi-trades-count');
  if (kpiTrades) kpiTrades.textContent = `${totalTrades} Closed Trades (${totalWins}W / ${totalLosses}L)`;

  const profitFactor = grossLoss > 0 ? (grossProfit / grossLoss) : (grossProfit > 0 ? 9.99 : 1.00);
  const kpiPf = document.getElementById('kpi-profit-factor');
  if (kpiPf) kpiPf.textContent = profitFactor.toFixed(2);

  const kpiVol = document.getElementById('kpi-total-volume');
  if (kpiVol) kpiVol.textContent = `$${totalVol.toFixed(2)}`;

  const kpiFees = document.getElementById('kpi-fees-paid');
  if (kpiFees) kpiFees.textContent = `Est. Fees: $${(totalVol * 0.00075).toFixed(3)}`;

  if (allocationChartInstance) {
    allocationChartInstance.data.datasets[0].data = [
      Math.max(0, totalAvailable),
      pairAlloc['SOL/USDT'] || 0,
      pairAlloc['ETH/USDT'] || 0,
      pairAlloc['BTC/USDT'] || 0,
      pairAlloc['AVAX/USDT'] || 0,
      pairAlloc['NEAR/USDT'] || 0,
      pairAlloc['SUI/USDT'] || 0,
      pairAlloc['PENGU/USDT'] || 0,
      pairAlloc['NSE'] || 0,
      pairAlloc['COMMODITY'] || 0,
      pairAlloc['POLY'] || 0
    ];
    allocationChartInstance.update();
  }

  if (winLossChartInstance) {
    winLossChartInstance.data.datasets[0].data = [totalWins || 1, totalLosses || (totalWins > 0 ? 0 : 1)];
    winLossChartInstance.update();
  }

  if (strategyBarChartInstance) {
    strategyBarChartInstance.data.labels = activeBotsCache.map(b => b.name);
    strategyBarChartInstance.data.datasets[0].data = activeBotsCache.map(b => b.total_pnl);
    strategyBarChartInstance.data.datasets[0].backgroundColor = activeBotsCache.map(b => b.total_pnl >= 0 ? '#10b981' : '#ef4444');
    strategyBarChartInstance.update();
  }
}

// Render Tickers Marquee
function renderTickers(tickers) {
  if (!tickers) return;
  const container = document.getElementById('tickers-bar');
  let html = '';
  Object.values(tickers).forEach(t => {
    const chgClass = (t.change_24h_pct || 0) >= 0 ? 'pnl-pos' : 'pnl-neg';
    const currSym = t.symbol.includes('(NSE)') ? '₹' : '$';
    html += `
      <div class="ticker-item">
        <span class="sym">${t.symbol}</span>
        <span class="price">${currSym}${t.price ? t.price.toFixed(2) : '---'}</span>
        <span class="${chgClass}" style="font-size:11px;">${t.change_24h_pct >= 0 ? '+' : ''}${(t.change_24h_pct || 0).toFixed(2)}%</span>
      </div>
    `;
  });
  if (html) container.innerHTML = html;
}

// Render Research
function renderResearch(overview) {
  if (!overview || !overview.overall_market_state) return;
  const regimeEl = document.getElementById('regime-content');
  if (regimeEl) {
    regimeEl.innerHTML = `
      <div style="margin-bottom:10px;">
        <strong>Market State:</strong> <span class="highlight" style="font-weight:700;">${overview.overall_market_state}</span>
      </div>
      <div style="display:flex; gap:12px; margin-bottom:12px;">
        <span>🟢 Bullish: <strong>${overview.bullish_pairs_count || 0}</strong></span>
        <span>🟡 Ranging: <strong>${overview.ranging_pairs_count || 0}</strong></span>
        <span>🔴 Bearish: <strong>${overview.bearish_pairs_count || 0}</strong></span>
      </div>
    `;
  }
}

function renderResearchLogs(logs) {
  const tbody = document.getElementById('research-log-rows');
  if (!tbody || !logs || !logs.length) return;
  let html = '';
  logs.forEach(l => {
    const timeStr = new Date(l.timestamp).toLocaleTimeString();
    html += `
      <tr>
        <td style="color:var(--text-muted);">${timeStr}</td>
        <td><span style="color:var(--accent-purple); font-weight:700;">${l.category}</span></td>
        <td>${l.title}</td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

function renderAdjustments(adjustments) {
  const tbody = document.getElementById('adjustments-rows');
  if (!tbody || !adjustments || !adjustments.length) return;
  let html = '';
  adjustments.forEach(a => {
    const timeStr = new Date(a.timestamp).toLocaleTimeString();
    html += `
      <tr>
        <td style="color:var(--text-muted);">${timeStr}</td>
        <td><strong style="color:var(--accent-cyan);">${a.bot_id}</strong></td>
        <td><code>${a.parameter_name}</code></td>
        <td style="color:var(--accent-red);">${a.old_value}</td>
        <td style="color:var(--accent-green); font-weight:700;">${a.new_value}</td>
        <td style="color:var(--text-muted);">${a.reason}</td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

function renderPositions(positions) {
  const tbody = document.getElementById('open-positions-rows');
  if (!tbody) return;
  if (!positions || !positions.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No active open positions.</td></tr>';
    return;
  }
  let html = '';
  positions.forEach(p => {
    const pnlClass = p.unrealized_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
    const pnlSign = p.unrealized_pnl >= 0 ? '+' : '';
    html += `
      <tr>
        <td><strong>${p.bot_id}</strong></td>
        <td><span style="color:var(--accent-cyan); font-weight:700;">${p.symbol}</span></td>
        <td>$${p.entry_price.toFixed(2)}</td>
        <td>$${p.current_price.toFixed(2)}</td>
        <td class="${pnlClass}">${pnlSign}$${p.unrealized_pnl.toFixed(2)} (${pnlSign}${p.unrealized_pnl_pct.toFixed(2)}%)</td>
        <td>SL: $${p.stop_loss ? p.stop_loss.toFixed(2) : '-'} | TP: $${p.take_profit ? p.take_profit.toFixed(2) : '-'}</td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

function renderTrades(trades) {
  const tbody = document.getElementById('trades-rows');
  if (!tbody) return;
  if (!trades || !trades.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No trade executions yet.</td></tr>';
    return;
  }
  let html = '';
  trades.forEach(t => {
    const timeStr = new Date(t.timestamp).toLocaleTimeString();
    const sideClass = t.side === 'BUY' ? 'tag-buy' : 'tag-sell';
    const pnlClass = (t.realized_pnl || 0) >= 0 ? 'pnl-pos' : 'pnl-neg';
    const pnlText = t.side === 'SELL' ? `${t.realized_pnl >= 0 ? '+' : ''}$${t.realized_pnl.toFixed(2)} (${t.realized_pnl_pct.toFixed(2)}%)` : '-';
    html += `
      <tr>
        <td style="color:var(--text-muted);">${timeStr}</td>
        <td><strong>${t.bot_id}</strong></td>
        <td>${t.symbol}</td>
        <td class="${sideClass}">${t.side}</td>
        <td>$${t.price.toFixed(2)}</td>
        <td class="${pnlClass}">${pnlText}</td>
        <td style="color:var(--text-muted); font-size:11px;">${t.reason}</td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

// 1-Click Live Switch Modal
async function openLiveSwitchModal() {
  openModal('live-switch-modal');
  const body = document.getElementById('modal-body-content');

  try {
    const winner = await fetch('/api/export-winner', { method: 'POST' }).then(r => r.json());
    body.innerHTML = `
      <div style="margin-bottom:14px;">
        <span style="font-size:13px; color:var(--text-muted);">Leading Tournament Champion:</span>
        <h3 style="color:var(--gold); font-size:20px;">🏆 ${winner.winner_name} (${winner.strategy_name})</h3>
        <div style="display:flex; gap:16px; margin-top:8px;">
          <span>ROI: <strong class="pnl-pos">+${winner.roi_pct.toFixed(2)}%</strong></span>
          <span>Win Rate: <strong>${winner.win_rate.toFixed(1)}%</strong></span>
          <span>Simulated PnL: <strong class="pnl-pos">+$${winner.total_pnl.toFixed(2)}</strong></span>
        </div>
      </div>
      <p style="font-size:13px; color:var(--text-muted); margin-bottom:10px;">
        To deploy this exact winning configuration with real <strong>$50.00 capital</strong>:
      </p>
      <div class="code-box">
        python live_switch.py --deploy --capital 50 --api-key YOUR_KEY --api-secret YOUR_SECRET
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<p style="color:var(--accent-red);">Failed to export winner metrics. Ensure tournament is active.</p>`;
  }
}

// -------------------------------------------------------------
// TAB 10: QUANTITATIVE PERFORMANCE & PORTFOLIO RISK REPORT
// -------------------------------------------------------------
async function fetchPerformanceReport() {
  try {
    const data = await fetch('/api/performance-report').then(r => r.json());
    renderPerformanceTab(data);
  } catch (e) {
    console.error("Performance report fetch error", e);
  }
}

function renderPerformanceTab(data) {
  if (!data || !data.portfolio) return;

  const port = data.portfolio;
  const exposureEl = document.getElementById('risk-exposure-pct');
  const equityEl = document.getElementById('risk-total-equity');
  const cbEl = document.getElementById('risk-circuit-breaker-status');
  const clusterEl = document.getElementById('risk-open-clusters');

  if (exposureEl) {
    exposureEl.textContent = `${port.exposure_pct}%`;
    exposureEl.style.color = port.exposure_pct > 60 ? 'var(--accent-red)' : 'var(--accent-cyan)';
  }
  if (equityEl) {
    equityEl.textContent = `$${port.total_equity.toFixed(2)}`;
  }
  if (cbEl) {
    if (data.circuit_breaker_active) {
      cbEl.textContent = '🚨 TRIGGERED (PAUSED)';
      cbEl.style.color = 'var(--accent-red)';
    } else {
      cbEl.textContent = '🟢 SECURE';
      cbEl.style.color = 'var(--accent-green)';
    }
  }
  if (clusterEl && port.cluster_counts) {
    const activeClusters = Object.entries(port.cluster_counts).filter(([k, v]) => v > 0).length;
    clusterEl.textContent = `${activeClusters} Active Clusters`;
  }

  // Render Bot Health Matrix Table
  const tbody = document.getElementById('performance-bot-rows');
  if (!tbody || !data.bots || !data.bots.length) return;

  let html = '';
  data.bots.forEach(b => {
    const healthBadge = b.health_status === 'HEALTHY' ? '<span style="color:var(--accent-green); font-weight:700;">🟢 Healthy</span>' : (b.health_status === 'DEGRADING' ? '<span style="color:var(--accent-yellow); font-weight:700;">🟡 Degrading</span>' : '<span style="color:var(--accent-red); font-weight:700;">🔴 Paused Decay</span>');
    const sharpeClass = b.sharpe_ratio >= 1.0 ? 'pnl-pos' : (b.sharpe_ratio < 0 ? 'pnl-neg' : '');

    html += `
      <tr>
        <td><strong>${b.name}</strong> <small style="color:var(--text-muted);">(${b.bot_id})</small></td>
        <td>${healthBadge}</td>
        <td class="${sharpeClass}">${b.sharpe_ratio >= 0 ? '+' : ''}${b.sharpe_ratio.toFixed(2)}</td>
        <td>${b.sortino_ratio >= 0 ? '+' : ''}${b.sortino_ratio.toFixed(2)}</td>
        <td>${b.win_rate.toFixed(1)}% <small style="color:var(--text-muted);">(${b.total_trades}T)</small></td>
        <td style="font-weight:700;">${b.profit_factor.toFixed(2)}</td>
        <td style="color:var(--accent-cyan); font-weight:800;">$${b.allocated_stake_usd.toFixed(2)}</td>
        <td>$${b.current_equity.toFixed(2)}</td>
        <td style="color:${b.max_drawdown > 3 ? 'var(--accent-red)' : 'var(--text-muted)'};">${b.max_drawdown.toFixed(2)}%</td>
        <td><span class="${b.is_active ? 'tag-buy' : 'tag-sell'}">${b.is_active ? 'ACTIVE' : 'PAUSED'}</span></td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}
