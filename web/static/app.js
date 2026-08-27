// CryptoArena Web Control Script
let chartInstance = null;
let currentTab = 'leaderboard';

const BOT_COLORS = {
  'bot_1_alphatrend': '#06b6d4',
  'bot_2_meanrevert': '#10b981',
  'bot_3_breakouthunter': '#f59e0b',
  'bot_4_adaptivegrid': '#8b5cf6',
  'bot_5_smartmoney': '#ec4899'
};

document.addEventListener('DOMContentLoaded', () => {
  initWebSocket();
  initChart();
  fetchInitialData();
  setInterval(fetchInitialData, 10000);
});

function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  event.target.classList.add('active');
  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) targetPane.classList.add('active');

  if (tabId === 'chart') {
    updateChartData();
  }
}

// WebSocket Connection
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

    renderLeaderboard(leaderboardRes);
    renderTrades(tradesRes);
    renderPositions(positionsRes);
    renderResearchLogs(researchRes);
    renderAdjustments(adjustmentsRes);
    updateChartData();
  } catch (e) {
    console.error("Fetch Data Error", e);
  }
}

// Render Leaderboard
function renderLeaderboard(bots) {
  if (!bots || !bots.length) return;
  const container = document.getElementById('leaderboard-container');
  let html = '';
  let totalArenaPnl = 0;

  bots.forEach((bot, index) => {
    const rank = index + 1;
    const rankClass = rank === 1 ? 'rank-1' : (rank === 2 ? 'rank-2' : (rank === 3 ? 'rank-3' : 'rank-other'));
    const rankLabel = rank === 1 ? '🥇 #1' : (rank === 2 ? '🥈 #2' : (rank === 3 ? '🥉 #3' : `#${rank}`));
    const pnlClass = bot.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
    const pnlSign = bot.total_pnl >= 0 ? '+' : '';
    totalArenaPnl += bot.total_pnl;

    html += `
      <div class="bot-card">
        <div class="rank-badge ${rankClass}">${rankLabel}</div>
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

        <div class="bot-desc">
          <span>${bot.description}</span>
          <div style="margin-top:6px; font-size:11px; color:var(--accent-cyan);">
            Active Trades: <strong>${bot.open_positions_count}</strong> | Free Cash: <strong>$${bot.available_balance.toFixed(2)}</strong>
          </div>
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
function initChart() {
  const ctx = document.getElementById('equityChart');
  if (!ctx) return;

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'AlphaTrend', data: [], borderColor: BOT_COLORS['bot_1_alphatrend'], tension: 0.2, fill: false },
        { label: 'MeanRevert', data: [], borderColor: BOT_COLORS['bot_2_meanrevert'], tension: 0.2, fill: false },
        { label: 'BreakoutHunter', data: [], borderColor: BOT_COLORS['bot_3_breakouthunter'], tension: 0.2, fill: false },
        { label: 'AdaptiveGrid', data: [], borderColor: BOT_COLORS['bot_4_adaptivegrid'], tension: 0.2, fill: false },
        { label: 'SmartMoneyTracker', data: [], borderColor: BOT_COLORS['bot_5_smartmoney'], tension: 0.2, fill: false }
      ]
    },
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
      plugins: {
        legend: { labels: { color: '#f8fafc', font: { family: 'JetBrains Mono' } } }
      }
    }
  });
}

async function updateChartData() {
  if (!chartInstance) return;
  try {
    const history = await fetch('/api/equity-history').then(r => r.json());
    if (!history || !history.length) return;

    // Group history by bot_id
    const timeLabels = [...new Set(history.map(h => new Date(h.timestamp).toLocaleTimeString()))].slice(-30);
    chartInstance.data.labels = timeLabels;

    const botKeys = ['bot_1_alphatrend', 'bot_2_meanrevert', 'bot_3_breakouthunter', 'bot_4_adaptivegrid', 'bot_5_smartmoney'];
    botKeys.forEach((key, idx) => {
      const botData = history.filter(h => h.bot_id === key).slice(-30).map(h => h.total_equity);
      chartInstance.data.datasets[idx].data = botData;
    });

    chartInstance.update();
  } catch (e) {
    console.error("Chart update error", e);
  }
}

// 1-Click Live Switch Modal
async function openLiveSwitchModal() {
  const modal = document.getElementById('live-switch-modal');
  const body = document.getElementById('modal-body-content');
  modal.classList.add('active');

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

function closeLiveSwitchModal() {
  document.getElementById('live-switch-modal').classList.remove('active');
}
