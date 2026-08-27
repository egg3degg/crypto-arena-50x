// CryptoArena Web Master Control & Analytics Script
let chartInstance = null;
let allocationChartInstance = null;
let winLossChartInstance = null;
let strategyBarChartInstance = null;

let currentTab = 'leaderboard';
let activeBotsCache = [];
let activePositionsCache = [];
let activeTradesCache = [];

const BASE_BOT_COLORS = [
  '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#3b82f6', '#14b8a6', '#f97316'
];

document.addEventListener('DOMContentLoaded', () => {
  initWebSocket();
  initEquityChart();
  initAnalyticsCharts();
  fetchInitialData();
  setInterval(fetchInitialData, 7000);
});

function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  event.target.classList.add('active');
  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) targetPane.classList.add('active');

  if (tabId === 'chart') {
    updateEquityChartData();
  } else if (tabId === 'analytics') {
    updateAnalyticsCharts();
  }
}

// WebSocket Connection for Real-Time Telemetry
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'TELEMETRY_UPDATE') {
        renderLeaderboard(data.leaderboard);
        renderTickers(data.tickers);
        renderResearch(data.market_overview);
      }
    } catch (e) {
      console.error("WS Parse Error", e);
    }
  };

  ws.onclose = () => {
    setTimeout(initWebSocket, 4000);
  };
}

async function fetchInitialData() {
  try {
    const [leaderboardRes, tradesRes, positionsRes, researchRes, adjustmentsRes] = await Promise.all([
      fetch('/api/leaderboard').then(r => r.json()),
      fetch('/api/trades').then(r => r.json()),
      fetch('/api/positions').then(r => r.json()),
      fetch('/api/research').then(r => r.json()),
      fetch('/api/adjustments').then(r => r.json())
    ]);

    activeBotsCache = leaderboardRes || [];
    activePositionsCache = positionsRes || [];
    activeTradesCache = tradesRes || [];

    renderLeaderboard(leaderboardRes);
    renderTrades(tradesRes);
    renderPositions(positionsRes);
    renderResearchLogs(researchRes);
    renderAdjustments(adjustmentsRes);
    updateAnalyticsCharts();
    updateEquityChartData();
  } catch (e) {
    console.error("Fetch Data Error", e);
  }
}

// Render Leaderboard & Bot Controls
function renderLeaderboard(bots) {
  if (!bots || !bots.length) return;
  activeBotsCache = bots;
  const container = document.getElementById('leaderboard-container');
  let html = '';
  let totalArenaPnl = 0;

  bots.forEach((bot, index) => {
    const rank = index + 1;
    const rankClass = rank === 1 ? 'rank-1' : (rank === 2 ? 'rank-2' : (rank === 3 ? 'rank-3' : 'rank-other'));
    const rankLabel = rank === 1 ? '🥇 #1 Champion' : (rank === 2 ? '🥈 #2' : (rank === 3 ? '🥉 #3' : `#${rank}`));
    const pnlClass = bot.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
    const pnlSign = bot.total_pnl >= 0 ? '+' : '';
    const isActive = bot.is_active !== false;
    totalArenaPnl += bot.total_pnl;

    html += `
      <div class="bot-card ${isActive ? '' : 'paused'}" id="card-${bot.bot_id}">
        <div class="card-top-row">
          <div class="bot-status-pill ${isActive ? 'status-active' : 'status-paused'}" onclick="toggleBotStatus('${bot.bot_id}', ${!isActive})">
            ${isActive ? '● Active' : '⏸ Paused'}
          </div>
          <div class="rank-badge ${rankClass}">${rankLabel}</div>
        </div>

        <div class="bot-name">${bot.name}</div>
        <div class="bot-strat-tag">${bot.strategy_name}</div>

        <div class="bot-stats-grid">
          <div class="stat-item">
            <span class="k">Total Equity</span>
            <span class="v">$${bot.current_equity.toFixed(2)}</span>
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
            <span class="k">Max Drawdown</span>
            <span class="v ${bot.max_drawdown > 3 ? 'pnl-neg' : ''}">${bot.max_drawdown.toFixed(2)}%</span>
          </div>
        </div>

        <div style="font-size:11px; color:var(--accent-cyan); margin-bottom:12px;">
          Active Trades: <strong>${bot.open_positions_count}</strong> | Free Cash: <strong>$${bot.available_balance.toFixed(2)}</strong>
        </div>

        <div class="card-control-toolbar">
          <button class="btn-ctrl" onclick="openEditParamsModal('${bot.bot_id}')">⚙️ Params</button>
          <button class="btn-ctrl" onclick="openManualTradeModal('${bot.bot_id}')">⚡ Order</button>
          <button class="btn-ctrl btn-ctrl-danger" onclick="liquidateBot('${bot.bot_id}')">🛑 Liquidate</button>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;

  // Header metric update
  const pnlEl = document.getElementById('header-total-pnl');
  if (pnlEl) {
    pnlEl.textContent = `${totalArenaPnl >= 0 ? '+' : ''}$${totalArenaPnl.toFixed(2)}`;
    pnlEl.className = `metric-value ${totalArenaPnl >= 0 ? 'pnl-pos' : 'pnl-neg'}`;
  }
  const countEl = document.getElementById('header-bot-count');
  if (countEl) {
    countEl.textContent = `${bots.length} Bots`;
  }
}

// Bot Control Actions
async function toggleBotStatus(botId, newActiveState) {
  try {
    await fetch(`/api/bots/${botId}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: newActiveState })
    }).then(r => r.json());
    fetchInitialData();
  } catch (e) {
    alert("Error toggling bot status: " + e);
  }
}

async function toggleAllBots(isActive) {
  if (!activeBotsCache.length) return;
  for (const b of activeBotsCache) {
    await fetch(`/api/bots/${b.bot_id}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive })
    });
  }
  fetchInitialData();
}

async function liquidateBot(botId) {
  if (!confirm(`Are you sure you want to emergency close all open positions for bot '${botId}' at market price?`)) return;
  try {
    const res = await fetch(`/api/bots/${botId}/liquidate`, { method: 'POST' }).then(r => r.json());
    alert(`Successfully closed ${res.closed_trades_count} open positions.`);
    fetchInitialData();
  } catch (e) {
    alert("Error liquidating bot: " + e);
  }
}

// Modal Handlers
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
    const res = await fetch('/api/bots/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json());

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
    const res = await fetch(`/api/bots/${botId}/params`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json());

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
    const res = await fetch(`/api/bots/${botId}/manual-order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json());

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

// Visual Analytics & Pie Charts (Tab 2)
function initAnalyticsCharts() {
  // 1. Asset Allocation Pie Chart
  const allocCtx = document.getElementById('allocationPieChart');
  if (allocCtx) {
    allocationChartInstance = new Chart(allocCtx, {
      type: 'doughnut',
      data: {
        labels: ['Liquid USDT', 'SOL', 'ETH', 'BTC', 'AVAX', 'NEAR'],
        datasets: [{
          data: [250, 0, 0, 0, 0, 0],
          backgroundColor: ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#ef4444', '#10b981'],
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

  // 2. Win vs Loss Donut Chart
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

  // 3. Strategy Contribution Bar Chart
  const barCtx = document.getElementById('strategyBarChart');
  if (barCtx) {
    strategyBarChartInstance = new Chart(barCtx, {
      type: 'bar',
      data: {
        labels: ['AlphaTrend', 'MeanRevert', 'Breakout', 'Grid', 'SmartMoney'],
        datasets: [{
          label: 'Total PnL ($)',
          data: [0, 0, 0, 0, 0],
          backgroundColor: BASE_BOT_COLORS,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } } },
          y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', callback: (v) => `$${v}` } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }
}

function updateAnalyticsCharts() {
  if (!activeBotsCache.length) return;

  // Calculate totals
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

  const pairAlloc = { 'SOL/USDT': 0, 'ETH/USDT': 0, 'BTC/USDT': 0, 'AVAX/USDT': 0, 'NEAR/USDT': 0 };
  activePositionsCache.forEach(p => {
    const sym = p.symbol;
    if (pairAlloc[sym] !== undefined) {
      pairAlloc[sym] += p.cost_basis || 0;
    }
  });

  activeTradesCache.forEach(t => {
    totalVol += t.cost_or_proceeds || 0;
    if (t.realized_pnl > 0) grossProfit += t.realized_pnl;
    else if (t.realized_pnl < 0) grossLoss += Math.abs(t.realized_pnl);
  });

  // Update KPI Cards
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

  // 1. Update Allocation Donut Chart
  if (allocationChartInstance) {
    allocationChartInstance.data.datasets[0].data = [
      Math.max(0, totalAvailable),
      pairAlloc['SOL/USDT'] || 0,
      pairAlloc['ETH/USDT'] || 0,
      pairAlloc['BTC/USDT'] || 0,
      pairAlloc['AVAX/USDT'] || 0,
      pairAlloc['NEAR/USDT'] || 0
    ];
    allocationChartInstance.update();
  }

  // 2. Update Win/Loss Chart
  if (winLossChartInstance) {
    winLossChartInstance.data.datasets[0].data = [totalWins || 1, totalLosses || (totalWins > 0 ? 0 : 1)];
    winLossChartInstance.update();
  }

  // 3. Update Strategy Bar Chart
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
    html += `
      <div class="ticker-item">
        <span class="sym">${t.symbol}</span>
        <span class="price">$${t.price ? t.price.toFixed(2) : '---'}</span>
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

// Render Research Log Table
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

// Render Self-Improvement Adjustments
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

// Render Positions Table
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

// Render Closed Trades
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

// Chart.js Equity Curve
function initEquityChart() {
  const ctx = document.getElementById('equityChart');
  if (!ctx) return;

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
        y: {
          grid: { color: '#1e293b' },
          ticks: { color: '#94a3b8', callback: (v) => `$${v.toFixed(2)}` },
          title: { display: true, text: 'Portfolio Equity ($ USD)', color: '#94a3b8' }
        }
      },
      plugins: { legend: { labels: { color: '#f8fafc', font: { family: 'JetBrains Mono' } } } }
    }
  });
}

async function updateEquityChartData() {
  if (!chartInstance) return;
  try {
    const history = await fetch('/api/equity-history').then(r => r.json());
    if (!history || !history.length) return;

    const timeLabels = [...new Set(history.map(h => new Date(h.timestamp).toLocaleTimeString()))].slice(-30);
    chartInstance.data.labels = timeLabels;

    const botIds = [...new Set(history.map(h => h.bot_id))];
    chartInstance.data.datasets = botIds.map((bId, idx) => {
      const color = BASE_BOT_COLORS[idx % BASE_BOT_COLORS.length];
      const botData = history.filter(h => h.bot_id === bId).slice(-30).map(h => h.total_equity);
      return {
        label: bId,
        data: botData,
        borderColor: color,
        backgroundColor: color,
        tension: 0.2,
        fill: false
      };
    });

    chartInstance.update();
  } catch (e) {
    console.error("Chart update error", e);
  }
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
        To deploy this exact winning configuration with real <strong>$50.00 capital</strong> on Binance or Bybit:
      </p>

      <div class="code-box">
        # 1. Export ready-to-run live bot script<br>
        python live_switch.py --deploy --capital 50 --api-key YOUR_KEY --api-secret YOUR_SECRET
      </div>

      <div style="margin-top:16px; font-size:12px; color:var(--accent-cyan);">
        🔒 Security Note: When creating your exchange API key, enable only <strong>Spot Trading</strong> and keep <strong>Withdrawals DISABLED</strong>.
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<p style="color:var(--accent-red);">Failed to export winner metrics. Please ensure tournament is active.</p>`;
  }
}
