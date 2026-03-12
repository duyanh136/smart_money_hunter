// Main JS
const socket = io({
    transports: ['websocket', 'polling'],
    upgrade: true
});
let priceChart, flowChart, rsiChart, macdChart;
let candleSeries, pocSeries, sharkSeries, retailSeries;
let rsiSeries, macdLineSeries, macdSignalSeries, macdHistSeries, ma20Series, ma50Series;

let currentSymbol = 'VND';
let currentPeriod = '1y';
let lastScanResults = []; // Cache for filtering

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    loadSymbols();
    loadData(currentSymbol);
    loadMarketHealth(); // Fetch market weather & health
    loadTopLeaders(); // Fetch Top 5 Leaders

    // Setup Toast Container
    if (!document.getElementById('toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        document.body.appendChild(toastContainer);
    }

    // Event Listeners
    document.getElementById('symbol-input').addEventListener('change', (e) => {
        currentSymbol = e.target.value.toUpperCase();
        loadData(currentSymbol);
    });

    // --- WebSocket Socket.IO ---
    socket.on('connect', () => {
        console.log("Connected to server");
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
                // Simple nudge/flash effect
                priceEl.style.color = '#e6b800';
                setTimeout(() => priceEl.style.color = '#fff', 500);
            }

            // Update Volume if present
            if (data.vol) {
                const volEl = document.getElementById('current-vol');
                if (volEl) volEl.innerText = new Intl.NumberFormat('en-US').format(data.vol);
            }

            // Real-time chart update (Daily candle)
            // We assume the update is for the CURRENT day (last bar)
            // Ideally we'd compare data.time with the last bar time.
            // For now, let's just update the UI price.
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

        // Update UI Info
        document.getElementById('stock-symbol').innerText = data.symbol;
        document.getElementById('stock-group').innerText = data.group;
        document.getElementById('strategy-text').innerText = data.strategy;

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

        leaders.forEach((leader, index) => {
            const changeClass = leader.change >= 0 ? 'positive' : 'negative';
            const sign = leader.change > 0 ? '+' : '';

            // Format tag safely
            let tagHtml = leader.tag || "🔥 Siêu cổ / Leader";
            // Replace newlines or make it compact if needed

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

    } catch (e) {
        console.error("Top Leaders Error", e);
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
        const row = `<tr>
            <td style="font-weight:bold; text-align: left; color:#a5d6ff;">${item.symbol}</td>
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

    // Check if exists
    let ext = smh_portfolio.find(i => i.symbol === sym);
    if (ext) {
        ext.cost = parseFloat(cost) || ext.cost;
        ext.volume = parseFloat(volume) || ext.volume;
    } else {
        smh_portfolio.push({
            symbol: sym,
            cost: parseFloat(cost) || 0,
            volume: parseFloat(volume) || 0
        });
    }
    document.getElementById('sl-input-symbol').value = '';
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
        const res = await fetch('/api/top_leaders?limit=10');
        const leaders = await res.json();

        if (!leaders || leaders.length === 0) {
            alert('Không có dữ liệu để xuất.');
            return;
        }

        // CSV Header and mapping
        const columns = [
            { label: 'Symbol', key: 'symbol' },
            { label: 'Price', key: 'price' },
            { label: 'ChangePct', key: 'change' },
            { label: 'VolRatio', key: 'vol_ratio' },
            { label: 'RSI', key: 'rsi' },
            { label: 'MarketPhase', key: 'market_phase' },
            { label: 'ActionRecommendation', key: 'action' },
            { label: 'LeaderScore', key: 'score' },
            { label: 'IsSharkDominated', key: 'is_shark_dominated' },
            { label: 'IsStormResistant', key: 'is_storm_resistant' },
            { label: 'Tag', key: 'tag' },
            { label: 'SignalVoTeo', key: 'signal_voteo' },
            { label: 'SignalBuyDip', key: 'signal_buydip' },
            { label: 'SignalBreakout', key: 'signal_breakout' },
            { label: 'SignalGoldenSell', key: 'signal_goldensell' },
            { label: 'SignalWarning', key: 'signal_warning' },
            { label: 'RadarPanicSell', key: 'radar_panicsell' },
            { label: 'RadarSangTay', key: 'radar_sangtay' },
            { label: 'RadarGayNen', key: 'radar_gaynen' },
            { label: 'RadarPhanKyAm', key: 'radar_phankyam' },
            { label: 'RadarDaoDong', key: 'radar_daodong' },
            { label: 'RadarChamMay', key: 'radar_chammay' },
            { label: 'PyramidAction', key: 'pyramid_action' },
            { label: 'BaseDistancePct', key: 'base_distance_pct' },
            { label: 'Rank', key: 'rank' },
            { label: 'BuySignalStatus', key: 'buy_signal_status' },
            { label: 'UpdatedAt', key: 'updated_at' }
        ];

        let csvContent = "\uFEFF"; // Add BOM for Excel UTF-8 support
        csvContent += columns.map(c => c.label).join('\t') + '\n'; 

        csvContent += leaders.map(leader => {
            return columns.map(c => {
                let val = leader[c.key];
                if (val === undefined || val === null) return '';
                if (typeof val === 'boolean') return val ? 'TRUE' : 'FALSE';
                if (typeof val === 'string') return val.replace(/\t/g, ' ').replace(/\n/g, ' ');
                return val;
            }).join('\t');
        }).join('\n');

        // Download File
        const blob = new Blob([csvContent], { type: 'text/tab-separated-values;charset=utf-8;' });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        
        link.setAttribute("href", url);
        link.setAttribute("download", `Top_10_Leaders_${timestamp}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showToast('📥 Xuất thành công', `Đã tải về danh sách Top 10 Leaders.`, 'dip');
    } catch (e) {
        console.error("Export Error", e);
        alert('Lỗi khi xuất dữ liệu: ' + e.message);
    }
}

// Initial render for Stop Loss Table when opening or loading
document.addEventListener('DOMContentLoaded', () => {
    renderStopLossTable();
    loadTopLeaders();
});
