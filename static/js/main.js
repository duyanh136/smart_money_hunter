// Main JS
const isVercel = window.location.hostname.includes('vercel.app');

const socket = io({
    transports: isVercel ? ['polling'] : ['websocket', 'polling'], // Faster fallback on Vercel
    upgrade: !isVercel,
    reconnectionAttempts: 3,
    timeout: 10000
});

let priceChart, flowChart, rsiChart, macdChart;
let candleSeries, pocSeries, sharkSeries, retailSeries;
let rsiSeries, macdLineSeries, macdSignalSeries, macdHistSeries, ma20Series, ma50Series;

let currentSymbol = 'VND';
let currentPeriod = '1y';
let lastScanResults = []; // Cache for filtering

document.addEventListener('DOMContentLoaded', () => {
    try {
        initCharts();
        loadSymbols();
        loadData(currentSymbol);
        loadMarketHealth(); // Fetch market weather & health
        loadTopLeaders(); // Fetch Top 5 Leaders
    } catch (err) {
        console.error("Initialization error:", err);
    }

    // Setup Toast Container
    if (!document.getElementById('toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        document.body.appendChild(toastContainer);
    }

    // Event Listeners
    const symbolInput = document.getElementById('symbol-input');
    if (symbolInput) {
        symbolInput.addEventListener('change', (e) => {
            currentSymbol = e.target.value.toUpperCase();
            loadData(currentSymbol);
        });
    }

    // Save Symbols to DB
    const btnSaveSymbols = document.getElementById('btnSaveSymbols');
    if (btnSaveSymbols) {
        btnSaveSymbols.addEventListener('click', async () => {
            try {
                btnSaveSymbols.disabled = true;
                btnSaveSymbols.innerText = 'Đang lưu...';
                
                const res = await fetch('/api/save_symbols', { method: 'POST' });
                const result = await res.json();
                
                if (result.status === 'success') {
                    showToast('✅ Thành công', `Đã lưu ${result.count} mã vào Database.`, 'dip');
                } else {
                    showToast('❌ Lỗi', result.message || 'Không thể lưu mã.', 'fomo');
                }
            } catch (e) {
                console.error("Save Symbols Error", e);
                showToast('❌ Lỗi', 'Lỗi kết nối máy chủ.', 'fomo');
            } finally {
                btnSaveSymbols.disabled = false;
                btnSaveSymbols.innerText = 'Lưu mã vào DB';
            }
        });
    }

    // --- WebSocket Socket.IO ---
    socket.on('connect', () => {
        console.log("Connected to server");
    });

    socket.on('connect_error', (err) => {
        console.warn("Socket.IO connection error (expected on Vercel):", err.message);
        if (isVercel) socket.disconnect(); // Don't spam on Vercel
    });

    socket.on('server_status', (data) => {
        console.log("Server status:", data);
    });

    socket.on('price_update', (data) => {
        if (data.symbol === currentSymbol) {
            // Update Price Display
            const priceEl = document.getElementById('current-price');
            if (priceEl && data.price) {
                priceEl.innerText = parseFloat(data.price).toFixed(2);
                priceEl.style.color = '#e6b800';
                setTimeout(() => priceEl.style.color = '#fff', 500);
            }

            if (data.vol) {
                const volEl = document.getElementById('current-vol');
                if (volEl) volEl.innerText = new Intl.NumberFormat('en-US').format(data.vol);
            }
        }
    });
});

function initCharts() {
    // 1. Price Chart
    const priceContainer = document.getElementById('price-chart');
    priceChart = LightweightCharts.createChart(priceContainer, {
        width: priceContainer.clientWidth,
        height: priceContainer.clientHeight,
        layout: {
            backgroundColor: '#161b22',
            textColor: '#d1d4dc',
        },
        grid: {
            vertLines: { color: '#30363d' },
            horzLines: { color: '#30363d' },
        },
        timeScale: {
            timeVisible: true,
            secondsVisible: false,
        },
        rightPriceScale: {
            borderVisible: false,
            autoScale: true,
            scaleMargins: {
                top: 0.1,
                bottom: 0.2, // Leave space for indicators? No, MA is on top.
            },
        },
    });

    candleSeries = priceChart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350'
    });

    ma20Series = priceChart.addLineSeries({
        color: 'rgba(33, 150, 243, 0.8)',
        lineWidth: 1,
        title: 'MA20',
    });

    ma50Series = priceChart.addLineSeries({
        color: 'rgba(255, 152, 0, 0.8)',
        lineWidth: 1,
        title: 'MA50',
    });

    // POC Line
    pocSeries = priceChart.addLineSeries({
        color: '#e6b800', // Gold
        lineWidth: 2,
        lineStyle: 2, // Dashed
        title: 'POC (Giá Vốn)',
        crosshairMarkerVisible: false,
    });

    // 2. RSI Chart
    const rsiContainer = document.getElementById('rsi-chart');
    rsiChart = LightweightCharts.createChart(rsiContainer, {
        width: rsiContainer.clientWidth,
        height: rsiContainer.clientHeight,
        layout: { backgroundColor: '#161b22', textColor: '#d1d4dc' },
        grid: { vertLines: { color: '#30363d' }, horzLines: { color: '#30363d' } },
        timeScale: { visible: false },
        rightPriceScale: {
            scaleMargins: { top: 0.1, bottom: 0.1 },
            maxValue: 100,
            minValue: 0
        },
    });

    rsiSeries = rsiChart.addLineSeries({
        color: '#9c27b0', // Purple
        lineWidth: 2,
        title: 'RSI (14)',
    });

    // RSI Overbought/Oversold levels
    const rsiLevel70 = rsiChart.addLineSeries({ color: 'rgba(255, 82, 82, 0.3)', lineWidth: 1, lineStyle: 2 });
    const rsiLevel30 = rsiChart.addLineSeries({ color: 'rgba(76, 175, 80, 0.3)', lineWidth: 1, lineStyle: 2 });
    // We'll set static data for these levels later or use priceLines if supported

    // 3. MACD Chart
    const macdContainer = document.getElementById('macd-chart');
    macdChart = LightweightCharts.createChart(macdContainer, {
        width: macdContainer.clientWidth,
        height: macdContainer.clientHeight,
        layout: { backgroundColor: '#161b22', textColor: '#d1d4dc' },
        grid: { vertLines: { color: '#30363d' }, horzLines: { color: '#30363d' } },
        timeScale: { visible: false },
    });

    macdHistSeries = macdChart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        title: 'MACD Hist',
    });

    macdLineSeries = macdChart.addLineSeries({ color: '#2196f3', lineWidth: 1, title: 'MACD' });
    macdSignalSeries = macdChart.addLineSeries({ color: '#ff5252', lineWidth: 1, title: 'Signal' });

    // 4. Flow Chart (Shark vs Retail)
    const flowContainer = document.getElementById('flow-chart');
    flowChart = LightweightCharts.createChart(flowContainer, {
        width: flowContainer.clientWidth,
        height: flowContainer.clientHeight,
        layout: {
            backgroundColor: '#161b22',
            textColor: '#d1d4dc',
        },
        grid: {
            vertLines: { color: '#30363d' },
            horzLines: { color: '#30363d' },
        },
        timeScale: {
            visible: true,
            timeVisible: true,
        },
    });

    // Shark (Green) - Positive Values
    sharkSeries = flowChart.addHistogramSeries({
        color: 'rgba(35, 134, 54, 0.8)', // Strong Green
        priceFormat: { type: 'volume' },
        title: 'Tiền Lớn (Shark)',
    });

    // Retail (Red) - Negative Values
    retailSeries = flowChart.addHistogramSeries({
        color: 'rgba(218, 54, 51, 0.8)', // Strong Red
        priceFormat: { type: 'volume' },
        title: 'Nhỏ Lẻ (Retail)',
    });

    // --- Sync Charts Multi-Way ---
    const allCharts = [priceChart, rsiChart, macdChart, flowChart];
    let isBroadcasting = false;

    allCharts.forEach(sourceChart => {
        sourceChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
            if (isBroadcasting) return;
            isBroadcasting = true;
            allCharts.forEach(targetChart => {
                if (targetChart !== sourceChart) {
                    targetChart.timeScale().setVisibleLogicalRange(range);
                }
            });
            // Use setTimeout to allow target charts to apply the range before unblocking
            setTimeout(() => { isBroadcasting = false; }, 0);
        });
    });

    // Resize observer for all charts
    const containers = [
        { el: priceContainer, chart: priceChart },
        { el: rsiContainer, chart: rsiChart },
        { el: macdContainer, chart: macdChart },
        { el: flowContainer, chart: flowChart }
    ];

    new ResizeObserver(entries => {
        for (let entry of entries) {
            const container = containers.find(c => c.el === entry.target);
            if (container && container.chart) {
                const { width, height } = entry.contentRect;
                container.chart.applyOptions({ width, height });
            }
        }
    }).observe(priceContainer);

    // Observe others too
    containers.forEach(c => {
        if (c.el) new ResizeObserver(entries => {
            for (let entry of entries) {
                const { width, height } = entry.contentRect;
                c.chart.applyOptions({ width, height });
            }
        }).observe(c.el)
    });
}

async function loadSymbols() {
    try {
        const watchlist = ["VND", "SSI", "DIG", "CEO", "HPG", "HSG", "NVL", "PDR", "GVR", "KBC", "IDC", "SCZ", "VGC", "DGC", "FPT", "MWG", "PNJ", "VIC", "VHM", "VRE", "VCB", "BID", "CTG", "TCB", "VPB", "MBB", "ACB", "STB", "SHB", "SSB", "MSN", "GAS", "PLX", "POW"];
        const datalist = document.getElementById('stock-suggestions');
        if (!datalist) return;
        datalist.innerHTML = '';
        watchlist.forEach(s => {
            const option = document.createElement('option');
            option.value = s;
            datalist.appendChild(option);
        });
    } catch (e) {
        console.error("Failed to load symbols", e);
    }
}

async function loadData(symbol, period = '1y') {
    try {
        const res = await fetch(`/api/history?symbol=${symbol}&period=${period}`);
        const data = await res.json();

        if (data.error) {
            alert('Không tìm thấy mã này');
            return;
        }

        // Update Stock Info Metadata
        document.getElementById('stock-symbol').innerText = data.symbol;
        document.getElementById('stock-group').innerText = data.group;
        document.getElementById('stock-strategy').innerText = data.strategy;
        document.getElementById('stock-phase').innerText = data.market_phase;
        document.getElementById('stock-action').innerText = data.action;
        document.getElementById('stock-base').innerText = `${data.base_distance_pct}% (Độ thắt chặt)`;

        // --- NEW: Update Badges & Vietnamese Buy Signal Status ---
        const badgeContainer = document.getElementById('badges-container');
        if (badgeContainer) {
            badgeContainer.innerHTML = '';
            if (data.is_shark_dominated) {
                badgeContainer.innerHTML += '<span class="badge badge-shark">💎 Tiền Lớn</span>';
            }
            if (data.is_storm_resistant) {
                badgeContainer.innerHTML += '<span class="badge badge-storm">🛡️ Kháng Bão</span>';
            }
        }
        
        const signalStatusEl = document.getElementById('buy-signal-status');
        if (signalStatusEl) {
            signalStatusEl.innerText = data.buy_signal_status || "Quan Sát / Chờ Điểm Mua";
            if (data.buy_signal_status === "🚨 BÁO ĐỘNG MÚC") signalStatusEl.style.color = '#4CAF50';
            else if (data.buy_signal_status === "🛑 CẤM ĐU XANH TÍM") signalStatusEl.style.color = '#ff6b6b';
            else signalStatusEl.style.color = '#e4e6eb';
        }

        // Update Volume Info
        const last = data.data[data.data.length - 1];
        const volEl = document.getElementById('current-vol');
        if (volEl) volEl.innerText = new Intl.NumberFormat('en-US').format(last.volume);

        document.getElementById('current-price').innerText = last.close.toFixed(2);

        // Update Phase & Action
        const phaseVal = document.getElementById('phase-value');
        const actionVal = document.getElementById('action-value');

        phaseVal.innerText = data.market_phase;
        actionVal.innerText = data.action;

        // Color coding for Phase
        const phaseCard = document.getElementById('phase-card');
        if (data.market_phase.includes("PHÂN PHỐI") || data.market_phase.includes("Nguy Hiểm")) {
            phaseCard.style.borderColor = '#da3633';
            phaseVal.style.color = '#da3633';
            actionVal.style.color = '#da3633';
        } else if (data.market_phase.includes("RUNG LẮC") || data.market_phase.includes("Uptrend")) {
            phaseCard.style.borderColor = '#238636';
            phaseVal.style.color = '#238636';
            actionVal.style.color = '#238636';
        } else if (data.market_phase.includes("QUÁ MUA") || data.market_phase.includes("Nắng Gắt")) {
            phaseCard.style.borderColor = '#e6b800';
            phaseVal.style.color = '#e6b800';
            actionVal.style.color = '#e6b800';
        } else {
            phaseCard.style.borderColor = '#30363d';
            phaseVal.style.color = '#f0f6fc';
            actionVal.style.color = '#4CAF50';
        }

        // Anti-FOMO & Signals Banner
        const banner = document.getElementById('psy-banner');
        const bannerText = document.getElementById('psy-text');

        if (last.signal_goldensell || last.signal_distribution) {
            showBanner(banner, bannerText, "CẢNH BÁO: ĐIỂM BÁN (Phân phối/Golden Sell)! Hạ tỷ trọng.", '#da3633', 'rgba(218, 54, 51, 0.3)');
        } else if (last.rsi > 75) {
            showBanner(banner, bannerText, "CẢNH BÁO: RSI > 75 (QUÁ MUA). HẠN CHẾ FOMO!", '#e6b800', 'rgba(230, 184, 0, 0.3)');
        } else if (last.signal_breakout) {
            showBanner(banner, bannerText, "BREAKOUT! Dòng tiền vào mạnh. Canh chỉnh là MUC.", '#238636', 'rgba(35, 134, 54, 0.3)');
        } else if (last.signal_buydip && last.signal_voteo) {
            showBanner(banner, bannerText, "CƠ HỘI VÀNG: Uptrend + Vô Teo + Test Cung. MUA GOM NGAY.", '#238636', 'rgba(35, 134, 54, 0.3)');
        } else {
            banner.style.display = 'none';
        }

        // --- Prepare Chart Data ---
        const candles = [];
        const ma20Data = [];
        const ma50Data = [];
        const pocData = [];
        const rsiData = [];
        const macdLineData = [];
        const macdSignalData = [];
        const macdHistData = [];
        const sharkData = [];
        const retailData = [];
        const markers = [];

        data.data.forEach(d => {
            candles.push({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close });
            if (d.ma20 > 0) ma20Data.push({ time: d.time, value: d.ma20 });
            if (d.ma50 > 0) ma50Data.push({ time: d.time, value: d.ma50 });
            if (d.poc > 0) pocData.push({ time: d.time, value: d.poc });
            rsiData.push({ time: d.time, value: d.rsi });
            macdLineData.push({ time: d.time, value: d.macd_line });
            macdSignalData.push({ time: d.time, value: d.macd_signal });
            macdHistData.push({
                time: d.time,
                value: d.macd_hist,
                color: d.macd_hist >= 0 ? '#26a69a' : '#ef5350'
            });
            sharkData.push({ time: d.time, value: d.shark_bar });
            retailData.push({ time: d.time, value: d.retail_bar });

            // Golden Buy Markers
            if (d.signal_super) {
                markers.push({
                    time: d.time,
                    offset: 1,
                    position: 'belowBar',
                    color: '#e6b800', // Gold color
                    shape: 'arrowUp',
                    text: 'MUA VÀNG'
                });
            }
            // Golden Sell Markers
            if (d.signal_goldensell) {
                markers.push({
                    time: d.time,
                    position: 'aboveBar',
                    color: '#e6b800', // Gold color
                    shape: 'arrowDown',
                    text: 'BÁN VÀNG'
                });
            }
        });

        candleSeries.setData(candles);
        ma20Series.setData(ma20Data);
        ma50Series.setData(ma50Data);
        pocSeries.setData(pocData);
        rsiSeries.setData(rsiData);
        macdLineSeries.setData(macdLineData);
        macdSignalSeries.setData(macdSignalData);
        macdHistSeries.setData(macdHistData);
        sharkSeries.setData(sharkData);
        retailSeries.setData(retailData);

        candleSeries.setMarkers(markers);

        // Update Signals List UI
        updateSignal('sig-voteo', last.signal_voteo);
        updateSignal('sig-buydip', last.signal_buydip || last.signal_ma50_test);
        updateSignal('sig-super', last.signal_super);
        updateSignal('sig-upbo', last.signal_upbo);
        updateSignal('sig-breakout', last.signal_breakout);
        updateSignal('sig-squeeze', last.signal_squeeze);
        updateSignal('sig-distribution', last.signal_distribution);
        // Auto-scroll to latest price for all charts
        const charts = [priceChart, rsiChart, macdChart, flowChart];
        charts.forEach(chart => {
            if (chart) {
                chart.timeScale().scrollToPosition(0, false);
            }
        });

    } catch (e) {
        console.error(e);
    }
}

async function loadMarketHealth() {
    try {
        const res = await fetch('/api/market_health');
        const data = await res.json();

        if (!data || !data.weather) return;

        // Update Weather Banner
        const weather = data.weather;
        const banner = document.getElementById('weather-banner');

        document.getElementById('weather-status').innerText = weather.weather;
        document.getElementById('weather-action').innerText = weather.action;
        document.getElementById('weather-macro').innerText = weather.macro;

        banner.className = `weather-banner ${weather.class}`;

        // Market health chart removed per user request.
    } catch (e) {
        console.error("Market Health Error", e);
    }
}

async function loadTopLeaders() {
    try {
        const res = await fetch('/api/top_leaders?limit=10');
        const leaders = await res.json();

        if (!leaders || leaders.length === 0) return;

        const container = document.getElementById('top-leaders-container');
        const grid = document.getElementById('leaders-grid');

        if (container) container.style.display = 'block';
        if (grid) grid.innerHTML = '';

        renderLeadersGrid(leaders);

    } catch (e) {
        console.error("Top Leaders Error", e);
    }
}

function renderLeadersGrid(leaders) {
    const grid = document.getElementById('leaders-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    leaders.forEach((leader, index) => {
        const changeClass = leader.change >= 0 ? 'positive' : 'negative';
        const sign = leader.change > 0 ? '+' : '';

        // Format tag safely
        let tagHtml = leader.tag || "🔥 Siêu cổ / Leader";

        let badgesHtml = '';
        if (leader.is_shark_dominated) {
            badgesHtml += '<span class="badge" style="font-size:0.65rem; padding: 2px 4px; background: #238636; color: white; border-radius: 4px; margin-right: 4px;" title="Cá mập gom mạnh, nhỏ lẻ thoát hàng">💎 Tiền Lớn</span>';
        }
        if (leader.is_storm_resistant) {
            badgesHtml += '<span class="badge" style="font-size:0.65rem; padding: 2px 4px; background: #9e6a03; color: white; border-radius: 4px; margin-right: 4px;" title="Cổ phiếu trơ với nhịp sập của VN-Index">🛡️ Kháng Bão</span>';
        }

        if (badgesHtml) {
            tagHtml = '<div style="margin-bottom: 4px;">' + badgesHtml + '</div>' + tagHtml;
        }

        const cardHtml = `
            <div class="leader-card" onclick="loadData('${leader.symbol}')">
                <div class="leader-symbol">
                    <span>${leader.symbol}</span>
                    <span class="leader-score">Top ${index + 1} (${leader.score}đ)</span>
                </div>
                <div class="leader-tag" style="line-height: 1.4;">${tagHtml}</div>
                
                <div class="leader-price-row">
                    <span class="leader-price">${new Intl.NumberFormat('en-US').format(leader.price)}</span>
                    <span class="leader-change ${changeClass}">${sign}${leader.change}%</span>
                </div>
                
                <div class="leader-actions">
                    <button class="btn-buy-leader" onclick="event.stopPropagation(); handleLeaderAction('BUY', '${leader.symbol}', ${leader.price}, ${leader.signal_buydip}, ${leader.rsi})">MUA</button>
                    <button class="btn-sell-leader" onclick="event.stopPropagation(); handleLeaderAction('SELL', '${leader.symbol}', ${leader.price}, false, 0)">BÁN</button>
                </div>
            </div>
        `;
        grid.innerHTML += cardHtml;
    });
}

async function toggleHistory() {
    const select = document.getElementById('history-date-select');
    const btn = document.getElementById('btn-show-history');
    
    if (select.style.display === 'none') {
        // Show select, load dates
        select.style.display = 'inline-block';
        btn.innerText = '🔙 Hiện tại';
        btn.style.borderColor = '#30363d';
        btn.style.color = '#fff';
        
        const res = await fetch('/api/top_leaders_dates');
        const dates = await res.json();
        
        select.innerHTML = '<option value="">Chọn ngày...</option>';
        dates.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.innerText = d;
            select.appendChild(opt);
        });
    } else {
        // Hide select, back to current
        select.style.display = 'none';
        btn.innerText = '🕒 Lịch sử';
        btn.style.borderColor = '#f9c513';
        btn.style.color = '#f9c513';
        loadTopLeaders();
    }
}

async function loadLeaderHistory() {
    const date = document.getElementById('history-date-select').value;
    if (!date) return;
    
    try {
        const res = await fetch(`/api/top_leaders_history?date=${date}`);
        const leaders = await res.json();
        
        if (leaders && !leaders.error) {
            renderLeadersGrid(leaders);
        } else {
            alert('Không có dữ liệu cho ngày này.');
        }
    } catch (e) {
        console.error("Load leader history error", e);
    }
}

function handleLeaderAction(action, symbol, price, isBuyDip, rsi) {
    if (action === 'BUY') {
        if (rsi > 70) {
            // Anti-FOMO
            showToast('🛑 CẤM ĐU XANH TÍM', `Siêu cổ ${symbol} đang chạy nước rút (RSI > 70). Mua đuổi lúc này rất dễ dính nhịp rũ!`, 'fomo');
            // Trigger visual feedback on the main banner too if symbol is selected
            if (currentSymbol === symbol) {
                const banner = document.getElementById('psy-banner');
                const bannerText = document.getElementById('psy-text');
                showBanner(banner, bannerText, `Khóa nút MUA: ${symbol} đang FOMO quá đà!`, '#da3633', 'rgba(218, 54, 51, 0.3)');
            }
        } else if (isBuyDip) {
            // Good to buy
            showToast('🚨 BÁO ĐỘNG MÚC', `Cơ hội vàng cho ${symbol}. Đang test hỗ trợ thành công. Múc Buy Dip!`, 'dip');
        } else {
            // Normal Buy
            showToast('✅ Đã nạp đạn', `Chuẩn bị lệnh Mua cho ${symbol} giá ${price}.`, 'dip');
        }
    } else if (action === 'SELL') {
        // Hold Tight Mode
        const confirmSell = confirm(`⚠️ Chế độ Ôm Chặt Lãi: \nCổ phiếu ${symbol} đang là Leader khỏe nhất nhì Index, tiền lớn vẫn đang bảo kê.\nLướt sóng lúc này rất dễ mất hàng và phải cover giá cao hơn.\n\nBạn có chắc chắn muốn CHỐT LỜI non không?`);
        if (confirmSell) {
            showToast('💰 Chốt lời', `Đã đặt lệnh Bán ${symbol} giá ${price}. Đừng tiếc nếu mai nó Trần nhé!`, 'dip');
        } else {
            showToast('🛡️ Giữ hàng', `Quyết định sáng suốt! Tiếp tục gồng lãi ${symbol}.`, 'dip');
        }
    }
}

function showToast(title, message, type = 'dip') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';

    // Icon based on type
    let icon = '🚀';
    if (type === 'fomo') icon = '🛑';
    if (title.includes('BÁO ĐỘNG')) icon = '🚨';
    if (title.includes('Chốt')) icon = '💰';

    toast.innerHTML = `
        <div class="toast-title ${type}">${icon} ${title}</div>
        <div class="toast-message">${message}</div>
    `;

    container.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 100);

    // Auto remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400); // Wait for transition
    }, 5000);
}


function showBanner(banner, textEl, text, borderColor, bgColor) {
    banner.style.display = 'block';
    banner.style.backgroundColor = bgColor;
    banner.style.border = `1px solid ${borderColor}`;
    textEl.innerText = text;
    textEl.style.color = borderColor;
}

function updateSignal(id, isActive) {
    const el = document.getElementById(id);
    if (!el) return;

    const statusText = el.querySelector('.status');
    if (isActive) {
        el.className = 'signal-item active'; // Add glow
        statusText.innerText = "XÁC NHẬN";

        if (id.includes('distribution') || id.includes('upbo') || id.includes('loose')) {
            statusText.style.color = '#ff6b6b';
            el.style.borderLeft = '3px solid #ff6b6b';
        } else {
            statusText.style.color = '#4CAF50';
            el.style.borderLeft = '3px solid #4CAF50';
        }
    } else {
        el.className = 'signal-item';
        statusText.innerText = "--";
        statusText.style.color = '#666';
        el.style.borderLeft = '3px solid transparent';
    }
}

async function runScan() {
    const tableElement = document.getElementById('scanner-table');
    const tbody = tableElement.querySelector('tbody');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">Đang quét toàn thị trường... Vui lòng đợi...</td></tr>';

    try {
        const res = await fetch('/api/scan');
        const results = await res.json();
        lastScanResults = results;

        renderScannerTable(results);

        // Reset filter UI
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        const allBtn = document.querySelector('.filter-btn[onclick*="all"]');
        if (allBtn) allBtn.classList.add('active');

    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color: red;">Lỗi kết nối máy chủ.</td></tr>';
    }
}

function renderScannerTable(data) {
    const tbody = document.getElementById('scanner-table').querySelector('tbody');
    tbody.innerHTML = '';

    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Không tìm thấy cổ phiếu nào.</td></tr>';
        return;
    }

    data.forEach(r => {
        // 1. Radar signals (5 algorithms + Panic Sell)
        let radarStr = '';
        if (r.radar_panicsell) radarStr += '<span class="badge badge-error" style="background:#da3633" title="Bán tháo hoảng loạn">🚨 BÁN THÁO</span> ';
        if (r.radar_phankyam) radarStr += '<span class="badge badge-error" title="Phân kỳ âm MACD">🛑 PhânKỳ</span> ';
        if (r.radar_sangtay) radarStr += '<span class="badge badge-warning" title="Lái sang tay">🚨 SangTay</span> ';
        if (r.radar_daodong) radarStr += '<span class="badge badge-warning" title="Dao động lỏng lẻo">⚠️ LỏngLẻo</span> ';
        if (r.radar_gaynen) radarStr += '<span class="badge badge-error" title="Gãy nền test lại">❌ GãyNền</span> ';
        if (r.radar_chammay) radarStr += '<span class="badge badge-warning" title="Chạm mây kháng cự">☁️ ChạmMây</span> ';

        // 2. Technical signals
        let sigs = [];
        if (r.signal_breakout) sigs.push('<span style="color:#4CAF50">Break</span>');
        if (r.signal_buydip) sigs.push('<span style="color:#4CAF50">Dip</span>');
        if (r.signal_voteo) sigs.push('<span style="color:#2196F3">VôTeo</span>');
        if (r.signal_warning) sigs.push('<span style="color:#f44336">WARN</span>');

        let sigHtml = radarStr + sigs.join(' ');
        if (!sigHtml) sigHtml = '<span style="color:#666">-</span>';

        // 3. Pyramid Sizing Badge Logic
        let pyramidClass = 'badge-success';
        if (r.pyramid_action && r.pyramid_action.includes('CẤM')) pyramidClass = 'badge-error';
        else if (r.pyramid_action && r.pyramid_action.includes('Hạ Quy Mô')) pyramidClass = 'badge-warning';

        let pyramidStr = '';
        if (r.pyramid_action && r.pyramid_action !== "N/A" && r.pyramid_action !== "Quan Sát") {
            let sign = r.base_distance_pct > 0 ? '+' : '';
            pyramidStr = '<div class="badge ' + pyramidClass + ' mt-1" style="font-size:0.7rem; padding: 2px 4px;">' + r.pyramid_action + ' (Từ Nền: ' + sign + r.base_distance_pct + '%)</div>';
        }

        const row = `<tr>
            <td style="font-weight:bold; color: #a5d6ff;">${r.symbol}</td>
            <td style="font-weight:bold; ${r.change >= 0 ? 'color:#7ee787' : 'color:#ff7b72'}">
                ${new Intl.NumberFormat('en-US').format(r.price)} (${r.change >= 0 ? '+' : ''}${r.change}%)
            </td>
            <td>${sigHtml}</td>
            <td style="font-size:0.9em; font-weight:bold;">
                <div>${r.action || 'Theo dõi'}</div>
                ${pyramidStr}
            </td>
            <td><button class="btn-primary" onclick="loadData('${r.symbol}')" style="padding: 2px 8px; font-size: 11px;">Xem</button></td>
        </tr>`;

        tbody.innerHTML += row;
    });
}

function filterByAction(type) {
    const buttons = document.querySelectorAll('.btn-filter');
    buttons.forEach(b => b.classList.remove('active'));
    // Use window.event or the passed event if available
    if (window.event && window.event.target) {
        window.event.target.classList.add('active');
    }

    let filtered = lastScanResults;

    if (type !== '') {
        const typeLower = type.toLowerCase();
        filtered = lastScanResults.filter(r => {
            const act = (r.action || '').toLowerCase();
            const phase = (r.market_phase || '').toLowerCase();

            if (typeLower === 'bán') {
                return act.includes('bán') ||
                    act.includes('sút') ||
                    act.includes('cắt lỗ') ||
                    phase.includes('phân phối') ||
                    phase.includes('bán tháo') ||
                    r.signal_warning ||
                    r.radar_panicsell || r.radar_phankyam || r.radar_gaynen || r.radar_sangtay || r.radar_daodong || r.radar_chammay;
            } else if (typeLower === 'mua') {
                return act.includes('mua') ||
                    act.includes('gom') ||
                    r.signal_breakout ||
                    r.signal_buydip;
            }
            return act.includes(typeLower);
        });
    }

    renderScannerTable(filtered);
}

function filterByRadar() {
    const buttons = document.querySelectorAll('.btn-filter');
    buttons.forEach(b => b.classList.remove('active'));
    if (window.event && window.event.target) {
        window.event.target.classList.add('active');
    }

    const filtered = lastScanResults.filter(r =>
        r.radar_panicsell ||
        r.radar_phankyam ||
        r.radar_sangtay ||
        r.radar_daodong ||
        r.radar_gaynen ||
        r.radar_chammay
    );

    renderScannerTable(filtered);
}

function changePeriod(p) {
    document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    currentPeriod = p;
    loadData(currentSymbol, p);
}

// --- STOPLOSS TOOL LOGIC ---
let smh_portfolio = JSON.parse(localStorage.getItem('smh_portfolio') || '[]');

function savePortfolio() {
    localStorage.setItem('smh_portfolio', JSON.stringify(smh_portfolio));
}

function renderStopLossTable() {
    const tbody = document.querySelector('#sl-table tbody');
    tbody.innerHTML = '';

    if (smh_portfolio.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding: 20px;">Chưa có dữ liệu. Hãy thêm mã cổ phiếu.</td></tr>';
        return;
    }

    smh_portfolio.forEach((item, index) => {
        let holdingDays = '-';
        let formattedDate = '-';
        if (item.buy_date) {
            const buyDate = new Date(item.buy_date);
            const today = new Date();
            const diffTime = Math.abs(today - buyDate);
            holdingDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            // Format dd/mm/yyyy
            const d = buyDate.getDate().toString().padStart(2, '0');
            const m = (buyDate.getMonth() + 1).toString().padStart(2, '0');
            const y = buyDate.getFullYear();
            formattedDate = `${d}/${m}/${y}`;
        }

        const row = `<tr>
            <td style="font-weight:bold; text-align: left; color:#a5d6ff;">${item.symbol}</td>
            <td style="font-size: 0.85em; color: #8b949e;">${formattedDate}</td>
            <td style="font-weight: bold; color: #f9c513;">${holdingDays}</td>
            <td>${item.cost || 0}</td>
            <td>${item.price || '-'}</td>
            <td style="${item.pnl_percent >= 0 ? 'color: #4CAF50' : 'color: #ff5252'}">${item.pnl_percent !== undefined ? item.pnl_percent + '%' : '-'}</td>
            <td style="color: #f9c513; font-weight: bold;">${item.radar_alert || '-'}</td>
            <td style="font-size: 0.9em; font-weight: bold;">${item.action || '-'}</td>
            <td><button onclick="removeStopLossItem(${index})" style="background: none; border:none; color: #ff5252; cursor: pointer;">Xóa</button></td>
        </tr>`;
        tbody.innerHTML += row;
    });
}

function addStopLossItem() {
    let sym = document.getElementById('sl-input-symbol').value.toUpperCase();
    if (!sym) return;
    let cost = document.getElementById('sl-input-cost').value;
    let volume = document.getElementById('sl-input-vol').value;
    let buyDate = document.getElementById('sl-input-buydate').value;

    // Check if exists
    let ext = smh_portfolio.find(i => i.symbol === sym);
    if (ext) {
        ext.cost = parseFloat(cost) || ext.cost;
        ext.volume = parseFloat(volume) || ext.volume;
        ext.buy_date = buyDate || ext.buy_date;
    } else {
        smh_portfolio.push({
            symbol: sym,
            cost: parseFloat(cost) || 0,
            volume: parseFloat(volume) || 0,
            buy_date: buyDate || null
        });
    }
    document.getElementById('sl-input-symbol').value = '';
    document.getElementById('sl-input-cost').value = '';
    document.getElementById('sl-input-vol').value = '';
    document.getElementById('sl-input-buydate').value = '';
    savePortfolio();
    renderStopLossTable();
}

function removeStopLossItem(index) {
    smh_portfolio.splice(index, 1);
    savePortfolio();
    renderStopLossTable();
}

async function processStopLoss() {
    if (smh_portfolio.length === 0) return alert('Hãy nhập ít nhất 1 mã cổ phiếu!');
    const btn = event.target;
    const originalText = btn.innerText;
    btn.innerText = '⏳ Đang quét...';
    try {
        const res = await fetch('/api/stoploss_tool', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ portfolio: smh_portfolio })
        });
        const data = await res.json();

        if (data.status === 'success') {
            data.data.forEach(updated => {
                let p = smh_portfolio.find(i => i.symbol === updated.symbol);
                if (p) {
                    p.price = updated.price;
                    p.pnl_percent = updated.pnl_percent;
                    p.radar_alert = updated.radar_alert;
                    p.action = updated.action;
                }
            });
            savePortfolio();
            renderStopLossTable();
        }
    } catch (e) {
        console.error("Stoploss calculation failed", e);
    } finally {
        btn.innerText = originalText;
    }
}

async function exportTopLeaders() {
    try {
        // Show loading state
        const btn = document.querySelector('.leaders-header .btn-primary');
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Đang xuất...';
        btn.disabled = true;

        // Directly trigger download via window.location for formatted Excel
        window.location.href = '/api/export_excel?limit=10';
        
        // Restore button after a short delay
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            showToast('📥 Xuất thành công', `Đã tải về file Excel Top 10 Leaders.`, 'dip');
        }, 2000);

    } catch (e) {
        console.error("Export Error", e);
        alert('Lỗi khi xuất dữ liệu: ' + e.message);
    }
}

// --- BACKTEST PERFORMANCE DASHBOARD ---
let equityChartInstance = null;

window.openBacktestModal = async function() {
    const modal = document.getElementById('backtest-modal');
    modal.style.display = 'flex';
    
    showToast('🚀 Đang tính toán hiệu quả chiến thuật...', 'info');
    
    try {
        const response = await fetch('/api/strategy_performance');
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        const summary = data.summary;
        
        // Populate Stats
        document.getElementById('bt-win-rate').innerText = summary.win_rate_t10 + '%';
        document.getElementById('bt-avg-ret').innerText = (summary.avg_return_t10 > 0 ? '+' : '') + summary.avg_return_t10 + '%';
        document.getElementById('bt-total-days').innerText = summary.total_days_analyzed;
        
        // Recommendation Logic
        let recommendation = '';
        if (summary.avg_return_t10 > 2) {
            recommendation = `🔥 <b>CHIẾN THUẬT SIÊU VIỆT:</b> Top 10 mang lại lợi nhuận trung bình <b>${summary.avg_return_t10}%</b> sau mỗi 10 ngày. Xác suất thắng <b>${summary.win_rate_t10}%</b> là cực kỳ ấn tượng. Khuyến nghị: Ưu tiên giải ngân tỷ trọng cao vào các mã đứng đầu danh sách.`;
        } else if (summary.avg_return_t10 > 0) {
            recommendation = `✅ <b>HIỆU QUẢ ỔN ĐỊNH:</b> Chiến thuật đang mang lại lợi nhuận dương. Thời gian nắm giữ tối ưu thường rơi vào khoảng <b>10-15 ngày (T+10 đến T+15)</b>. Hãy kiên nhẫn nắm giữ để dòng tiền lan tỏa.`;
        } else {
            recommendation = `⚠️ <b>RỦI RO THỊ TRƯỜNG:</b> Hiện tại hiệu suất Top 10 đang đi ngang hoặc sụt giảm do thị trường chung xấu. Hãy hạ tỷ trọng và chỉ tham gia với khối lượng nhỏ cho đến khi đường cong lợi nhuận hướng lên.`;
        }
        document.getElementById('bt-recommendation').innerHTML = recommendation;
        
        // Render Chart
        renderEquityChart(summary.equity_curve);
        
    } catch (error) {
        console.error('Backtest Error:', error);
        showToast('Lỗi khi tải dữ liệu backtest', 'error');
    }
}

function renderEquityChart(curve) {
    const ctx = document.getElementById('equity-chart').getContext('2d');
    
    if (equityChartInstance) {
        equityChartInstance.destroy();
    }
    
    const labels = curve.map(point => point.date);
    const data = curve.map(point => point.profit);
    
    equityChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Lợi nhuận lũy kế (% Sum T+10)',
                data: data,
                borderColor: '#9c27b0',
                backgroundColor: 'rgba(156, 39, 176, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#9c27b0'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#8b949e', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { 
                        color: '#8b949e',
                        callback: function(value) { return value + '%'; }
                    }
                }
            }
        }
    });
}

// Initial render for Stop Loss Table when opening or loading
document.addEventListener('DOMContentLoaded', () => {
    renderStopLossTable();
    loadTopLeaders();
});
