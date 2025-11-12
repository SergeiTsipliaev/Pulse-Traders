// 📊 ПРАВИЛЬНАЯ ВЕРСИЯ - Фиксированные отступы и ширина свечей
// На всех экранах свечи выглядят одинаково, просто видно разное количество

const API_URL = '/api';
let priceChart = null;
let predictionChart = null;
let currentCryptoData = null;
let priceUpdateInterval = null;
let selectedCrypto = null;
let currentTimeframe = '60';
let chartType = 'line';
let currentKlines = [];

document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const symbol = urlParams.get('symbol');

    if (!symbol) {
        window.location.href = '/';
        return;
    }

    selectedCrypto = symbol;
    await loadCryptoData(symbol);
    setupEventListeners();
    setupTimeframeMenu();
});

function setupTimeframeMenu() {
    const btn = document.getElementById('timeframeBtn');
    const menu = document.getElementById('timeframeMenu');
    const options = document.querySelectorAll('.timeframe-option');

    btn.onclick = (e) => {
        e.stopPropagation();
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    };

    options.forEach(option => {
        option.onclick = () => {
            const interval = option.dataset.interval;
            const label = option.textContent;

            currentTimeframe = interval;
            btn.textContent = `${label} ▼`;
            menu.style.display = 'none';

            loadKlines(selectedCrypto, interval);
        };
    });

    document.addEventListener('click', (e) => {
        if (!btn.contains(e.target) && !menu.contains(e.target)) {
            menu.style.display = 'none';
        }
    });
}

function setupEventListeners() {
    document.getElementById('predictBtn').onclick = makePrediction;

    document.getElementById('chartTypeBtn').onclick = () => {
        chartType = chartType === 'line' ? 'candlestick' : 'line';
        const btn = document.getElementById('chartTypeBtn');
        btn.textContent = chartType === 'line' ? '📈 Линия' : '📊 Свечи';

        if (currentKlines.length > 0) {
            displayPriceChartFromKlines(currentKlines, currentTimeframe);
        }
    };
}

async function loadCryptoData(symbol) {
    if (priceUpdateInterval) {
        clearInterval(priceUpdateInterval);
        priceUpdateInterval = null;
    }

    showLoading('Загрузка...');

    try {
        const response = await fetch(`${API_URL}/crypto/${symbol}`);
        const data = await response.json();

        if (data.success) {
            currentCryptoData = data.data;
            displayCryptoData(data.data);

            priceUpdateInterval = setInterval(() => {
                updatePriceRealtime(symbol);
            }, 10000);
        } else {
            alert('Ошибка: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка подключения');
    } finally {
        hideLoading();
    }
}

async function updatePriceRealtime(symbol) {
    try {
        const response = await fetch(`${API_URL}/crypto/${symbol}`);
        const data = await response.json();

        if (data.success && data.data) {
            const newData = data.data;
            const currentPrice = newData.current.price;
            document.getElementById('currentPrice').textContent = `$${formatPrice(currentPrice)}`;

            const change = newData.current.change_24h || 0;
            const changeEl = document.getElementById('priceChange');
            const changeIcon = change >= 0 ? '↑' : '↓';
            const changeColor = change >= 0 ? '#10b981' : '#ef4444';

            changeEl.textContent = `${changeIcon} ${Math.abs(change).toFixed(2)}%`;
            changeEl.style.color = changeColor;
            changeEl.style.background = changeColor + '20';

            document.getElementById('high24h').textContent = `$${formatPrice(newData.current.high_24h)}`;
            document.getElementById('low24h').textContent = `$${formatPrice(newData.current.low_24h)}`;

            currentCryptoData = newData;
        }
    } catch (error) {
        console.error('Error updating price:', error);
    }
}

async function displayCryptoData(data) {
    document.getElementById('cryptoName').textContent = data.symbol.slice(0, -4);
    document.getElementById('cryptoSymbol').textContent = data.symbol;

    const currentPrice = data.current.price;
    document.getElementById('currentPrice').textContent = `$${formatPrice(currentPrice)}`;

    const change = data.current.change_24h || 0;
    const changeEl = document.getElementById('priceChange');
    const changeIcon = change >= 0 ? '↑' : '↓';
    const changeColor = change >= 0 ? '#10b981' : '#ef4444';

    changeEl.textContent = `${changeIcon} ${Math.abs(change).toFixed(2)}%`;
    changeEl.style.color = changeColor;
    changeEl.style.background = changeColor + '20';

    document.getElementById('high24h').textContent = `$${formatPrice(data.current.high_24h)}`;
    document.getElementById('low24h').textContent = `$${formatPrice(data.current.low_24h)}`;

    loadKlines(data.symbol, currentTimeframe);

    if (data.logo) {
        document.getElementById('cryptoLogo').src = data.logo;
        document.getElementById('cryptoLogo').onerror = function() {
            // Fallback на эмодзи если логотип не загрузился
            this.style.display = 'none';
        };
    }
}



async function loadKlines(symbol, interval) {
    try {
        const response = await fetch(`${API_URL}/klines/${symbol}?interval=${interval}&limit=100`);
        const data = await response.json();

        if (data.success && data.data && data.data.length > 0) {
            currentKlines = data.data;
            displayPriceChartFromKlines(data.data, interval);
        }
    } catch (error) {
        console.error('Error loading klines:', error);
    }
}

function displayPriceChartFromKlines(klines, interval) {
    const ctx = document.getElementById('priceChart');

    if (priceChart) {
        priceChart.destroy();
    }

    if (chartType === 'line') {
        displayLineChart(klines, interval, ctx);
    } else {
        displayCandlestickChart(klines, interval, ctx);
    }
}

function displayLineChart(klines, interval, ctx) {
    const labels = klines.map(kline => {
        const date = new Date(kline.timestamp);
        if (['D', 'W', 'M'].includes(interval)) {
            return date.toLocaleDateString('ru-RU');
        } else {
            return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        }
    });

    const closePrices = klines.map(k => k.close);

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Цена (USDT)',
                data: closePrices,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 6,
                borderWidth: 2.5,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        padding: 15,
                        font: { size: 12, weight: '600' },
                        usePointStyle: true,
                        color: '#ffffff'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    padding: 12,
                    cornerRadius: 8,
                    titleFont: { size: 13, weight: 'bold' },
                    bodyFont: { size: 12 },
                    callbacks: {
                        label: (context) => `  Цена: $${formatPrice(context.parsed.y)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255,255,255,0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: (value) => `$${formatNumber(value)}`,
                        font: { size: 11 },
                        color: '#ffffff'
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        maxTicksLimit: 8,
                        font: { size: 11 },
                        color: '#ffffff'
                    }
                }
            }
        }
    });

    ctx.style.height = '250px';
}

function displayCandlestickChart(klines, interval, ctx) {
    const labels = klines.map(kline => {
        const date = new Date(kline.timestamp);
        if (['D', 'W', 'M'].includes(interval)) {
            return date.toLocaleDateString('ru-RU');
        } else {
            return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        }
    });

    const closePrices = klines.map(k => k.close);

    let tooltipElement = document.getElementById('candleTooltip');
    if (!tooltipElement) {
        tooltipElement = document.createElement('div');
        tooltipElement.id = 'candleTooltip';
        tooltipElement.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.95);
            color: white;
            padding: 12px;
            border-radius: 8px;
            font-size: 12px;
            font-family: 'Courier New', monospace;
            display: none;
            z-index: 1000;
            border: 1px solid #333;
            pointer-events: none;
            min-width: 140px;
            line-height: 1.7;
        `;
        document.body.appendChild(tooltipElement);
    }

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Цена (USDT)',
                data: closePrices,
                borderColor: 'transparent',
                backgroundColor: 'transparent',
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                intersect: false
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255,255,255,0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: (value) => `$${formatNumber(value)}`,
                        font: { size: 11 },
                        color: '#ffffff'
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        maxTicksLimit: 8,
                        font: { size: 11 },
                        color: '#ffffff'
                    }
                }
            }
        },
        plugins: [{
            id: 'candlestickPlugin',
            afterDraw(chart) {
                const { ctx: canvasCtx, chartArea, scales } = chart;
                const xScale = scales.x;
                const yScale = scales.y;

                canvasCtx.save();

                // ✅ ПРАВИЛЬНОЕ РЕШЕНИЕ: Фиксированные отступы и ширина
                // Вместо растягивания всех свечей, используем фиксированные размеры

                const chartWidth = chartArea.right - chartArea.left;

                // Фиксированные параметры (одинаковые для всех экранов)
                const FIXED_CANDLE_WIDTH = 8;  // Ширина свечи: 8px
                const FIXED_SPACING = 10;       // Отступ между свечами: 10px
                const candleAndSpacing = FIXED_CANDLE_WIDTH + FIXED_SPACING; // 18px всего на одну свечу

                // Сколько свечей вмещается на экран?
                const maxCandlesInView = Math.floor(chartWidth / candleAndSpacing);

                // Берем последние свечи (самые свежие данные)
                const displayKlines = klines.slice(-maxCandlesInView);
                const startIdx = klines.length - displayKlines.length;

                console.log(`📊 Фиксированные параметры:`);
                console.log(`   Ширина графика: ${chartWidth}px`);
                console.log(`   Ширина свечи: ${FIXED_CANDLE_WIDTH}px`);
                console.log(`   Отступ: ${FIXED_SPACING}px`);
                console.log(`   Всего свечей: ${klines.length}, показываем: ${displayKlines.length}`);

                // Рисуем только видимые свечи
                displayKlines.forEach((kline, displayIdx) => {
                    // X позиция основана на фиксированном шаге
                    const x = chartArea.left + (displayIdx + 0.5) * candleAndSpacing;

                    const highY = yScale.getPixelForValue(kline.high);
                    const lowY = yScale.getPixelForValue(kline.low);
                    const openY = yScale.getPixelForValue(kline.open);
                    const closeY = yScale.getPixelForValue(kline.close);

                    const isGreen = kline.close >= kline.open;
                    const color = isGreen ? '#10b981' : '#ef4444';
                    const bodyTop = Math.min(openY, closeY);
                    const bodyHeight = Math.max(Math.abs(closeY - openY), 1);

                    // Wick (фитиль) - 0.5px
                    canvasCtx.strokeStyle = color;
                    canvasCtx.lineWidth = 0.5;
                    canvasCtx.beginPath();
                    canvasCtx.moveTo(x, highY);
                    canvasCtx.lineTo(x, lowY);
                    canvasCtx.stroke();

                    // Body (тело свечи)
                    canvasCtx.fillStyle = color;
                    canvasCtx.globalAlpha = 0.85;
                    canvasCtx.fillRect(
                        x - FIXED_CANDLE_WIDTH / 2,
                        bodyTop,
                        FIXED_CANDLE_WIDTH,
                        bodyHeight
                    );

                    // Контур свечи
                    canvasCtx.strokeStyle = color;
                    canvasCtx.lineWidth = 0.5;
                    canvasCtx.globalAlpha = 1;
                    canvasCtx.strokeRect(
                        x - FIXED_CANDLE_WIDTH / 2,
                        bodyTop,
                        FIXED_CANDLE_WIDTH,
                        bodyHeight
                    );
                });

                canvasCtx.restore();

                const canvas = chart.canvas;

                const handleMouseMove = (e) => {
                    const rect = canvas.getBoundingClientRect();
                    const canvasX = e.clientX - rect.left;
                    const canvasY = e.clientY - rect.top;

                    let hoveredIdx = -1;
                    const tolerance = FIXED_CANDLE_WIDTH;

                    displayKlines.forEach((kline, displayIdx) => {
                        const x = chartArea.left + (displayIdx + 0.5) * candleAndSpacing;
                        if (Math.abs(canvasX - x) < tolerance &&
                            canvasY > chartArea.top && canvasY < chartArea.bottom) {
                            hoveredIdx = startIdx + displayIdx;
                        }
                    });

                    if (hoveredIdx >= 0) {
                        const kline = klines[hoveredIdx];
                        const tooltipText = `${labels[hoveredIdx]}\nO $${formatPrice(kline.open)}\nH $${formatPrice(kline.high)}\nL $${formatPrice(kline.low)}\nC $${formatPrice(kline.close)}`;

                        tooltipElement.textContent = tooltipText;
                        tooltipElement.style.display = 'block';
                        
                        let tooltipX = e.clientX + 10;
                        let tooltipY = e.clientY - 80;
                        
                        if (tooltipX + 150 > window.innerWidth) {
                            tooltipX = e.clientX - 160;
                        }
                        
                        tooltipElement.style.left = tooltipX + 'px';
                        tooltipElement.style.top = tooltipY + 'px';
                    } else {
                        tooltipElement.style.display = 'none';
                    }
                };

                const handleMouseLeave = () => {
                    tooltipElement.style.display = 'none';
                };

                canvas.addEventListener('mousemove', handleMouseMove);
                canvas.addEventListener('mouseleave', handleMouseLeave);
            }
        }]
    });

    ctx.style.height = '250px';
}

async function makePrediction() {
    if (!selectedCrypto) return;

    const btn = document.getElementById('predictBtn');
    btn.disabled = true;
    btn.textContent = '🧠 Обучение...';

    showLoading('Обработка...');

    try {
        const response = await fetch(`${API_URL}/predict/${selectedCrypto}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            displayPrediction(data.data);
        } else {
            alert('Ошибка: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка подключения');
    } finally {
        hideLoading();
        btn.disabled = false;
        btn.textContent = '🔮 Прогноз на 7 дней';
    }
}

function displayPrediction(prediction) {
    const section = document.getElementById('predictionSection');
    section.classList.add('show');

    const signalEmojis = {
        'STRONG_BUY': '🟢',
        'BUY': '🟢',
        'HOLD': '🟡',
        'SELL': '🔴',
        'STRONG_SELL': '🔴'
    };

    document.getElementById('signalEmoji').textContent = signalEmojis[prediction.signal] || '🟡';
    document.getElementById('signalText').textContent = prediction.signal_text;

    const change = prediction.predicted_change;
    const changeEl = document.getElementById('predictedChange');
    changeEl.textContent = `${change > 0 ? '+' : ''}${change.toFixed(2)}%`;
    changeEl.className = change > 0 ? 'predicted-change positive' : 'predicted-change negative';

    document.getElementById('expectedPrice').textContent = `$${formatPrice(prediction.expected_price)}`;
    document.getElementById('support').textContent = `$${formatPrice(prediction.support)}`;
    document.getElementById('resistance').textContent = `$${formatPrice(prediction.resistance)}`;

    document.getElementById('confidence').textContent = `${prediction.confidence.toFixed(0)}%`;

    // ✅ ИСПРАВЛЕНИЕ: Градиент confidence bar зависит от направления тренда
    const confidenceFill = document.getElementById('confidenceFill');

    if (prediction.predicted_change > 0) {
        // ПОКУПАТЬ (тренд вверх) - зелёный слева → жёлтый справа (восходящий наклон)
        confidenceFill.style.background = 'linear-gradient(90deg, #10b981, #fbbf24)';
        confidenceFill.style.width = `${prediction.confidence}%`;
    } else if (prediction.predicted_change < 0) {
        // ПРОДАВАТЬ (тренд вниз) - красный слева → жёлтый справа (всё ещё левый край)
        confidenceFill.style.background = 'linear-gradient(90deg, #ef4444, #fbbf24)';
        confidenceFill.style.width = `${prediction.confidence}%`;
    } else {
        // УДЕРЖИВАТЬ - жёлтый слева, жёлтый справа (нейтраль)
        confidenceFill.style.background = 'linear-gradient(90deg, #fbbf24, #f59e0b)';
        confidenceFill.style.width = `${prediction.confidence}%`;
    }

    document.getElementById('rmse').textContent = `$${formatPrice(prediction.rmse)}`;

    if (currentCryptoData && currentCryptoData.indicators) {
        displayPredictionIndicators(currentCryptoData.indicators);
    }

    displayPredictionChart(prediction);

    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayPredictionIndicators(indicators) {
    const grid = document.getElementById('predictionIndicators');
    if (!grid) return;

    grid.classList.add('show');
    grid.innerHTML = '';

    const items = [
        {
            label: 'RSI (14)',
            value: indicators.rsi.toFixed(1),
            color: getRSIColor(indicators.rsi)
        },
        {
            label: 'MA-7',
            value: `$${formatPrice(indicators.ma_7)}`
        },
        {
            label: 'MA-25',
            value: `$${formatPrice(indicators.ma_25)}`
        },
        {
            label: 'MA-50',
            value: `$${formatPrice(indicators.ma_50)}`
        },
        {
            label: 'Волатильность',
            value: `${indicators.volatility.toFixed(2)}%`,
            color: indicators.volatility > 5 ? '#ef4444' : '#10b981'
        },
        {
            label: 'Тренд',
            value: `${indicators.trend_strength > 0 ? '+' : ''}${indicators.trend_strength.toFixed(1)}%`,
            color: indicators.trend_strength > 0 ? '#10b981' : '#ef4444'
        }
    ];

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'indicator-card';
        card.innerHTML = `
            <div class="indicator-label">${item.label}</div>
            <div class="indicator-value" style="color: ${item.color || '#3390ec'}">${item.value}</div>
        `;
        grid.appendChild(card);
    });
}

function getRSIColor(rsi) {
    if (rsi > 70) return '#ef4444';
    if (rsi < 30) return '#10b981';
    return '#f59e0b';
}

function displayPredictionChart(prediction) {
    const ctx = document.getElementById('predictionChart');

    if (predictionChart) {
        predictionChart.destroy();
    }

    const labels = Array.from({ length: prediction.days }, (_, i) => `День ${i + 1}`);
    const trendColor = prediction.predicted_change > 0 ? '#06b6d4' : '#ef4444';
    const bgColor = prediction.predicted_change > 0 ? 'rgba(6, 182, 212, 0.15)' : 'rgba(239, 68, 68, 0.15)';

    predictionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Прогноз цены',
                    data: prediction.predictions,
                    borderColor: trendColor,
                    backgroundColor: bgColor,
                    tension: 0.45,
                    fill: true,
                    pointRadius: 6,
                    pointBackgroundColor: trendColor,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2.5,
                    pointHoverRadius: 8,
                    borderWidth: 3,
                    borderCapStyle: 'round',
                    borderJoinStyle: 'round'
                },
                {
                    label: 'Текущая цена',
                    data: Array(prediction.days).fill(prediction.current_price),
                    borderColor: '#667eea',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        padding: 15,
                        font: { size: 12, weight: '600' },
                        usePointStyle: true,
                        color: '#ffffff'
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0,0,0,0.9)',
                    padding: 12,
                    cornerRadius: 10,
                    titleFont: { size: 13, weight: 'bold' },
                    bodyFont: { size: 12 },
                    borderColor: trendColor,
                    borderWidth: 2,
                    displayColors: true,
                    callbacks: {
                        title: (context) => context[0].label,
                        label: (context) => {
                            const value = context.parsed.y;
                            if (value === null) return '';
                            return `  ${context.dataset.label}: $${formatPrice(value)}`;
                        },
                        afterLabel: (context) => {
                            if (context.datasetIndex === 0) {
                                const current = prediction.current_price;
                                const value = context.parsed.y;
                                const diff = value - current;
                                const percent = (diff / current * 100).toFixed(2);
                                return `  Изменение: ${diff > 0 ? '+' : ''}${percent}%`;
                            }
                        }
                    }
                },
                filler: {
                    propagate: true
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255,255,255,0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: (value) => `$${formatNumber(value)}`,
                        font: { size: 11 },
                        color: '#ffffff'
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        font: { size: 11 },
                        color: '#ffffff'
                    }
                }
            }
        }
    });

    ctx.style.height = '350px';
}

function showLoading(text = 'Загрузка...') {
    const loading = document.getElementById('loading');
    document.getElementById('loadingText').textContent = text;
    loading.classList.add('show');
}

function hideLoading() {
    document.getElementById('loading').classList.remove('show');
}

function formatPrice(price) {
    if (price === undefined || price === null) return '0.00';

    if (price >= 1) {
        return parseFloat(price).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    } else {
        return parseFloat(price).toLocaleString('en-US', {
            minimumFractionDigits: 4,
            maximumFractionDigits: 8
        });
    }
}

function formatNumber(num) {
    if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toFixed(0);
}