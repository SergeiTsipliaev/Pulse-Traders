let authToken = null;

document.addEventListener('DOMContentLoaded', () => {
    // Получаем токен из localStorage
    const token = localStorage.getItem('auth_token');

    console.log('✅ Token:', token ? 'есть' : 'нет');

    if (!token) {
        showAlert('❌ Ошибка: токен авторизации не найден. Пожалуйста, войдите снова.', 'error');
        console.error('❌ No auth token found');
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
        return;
    }

    authToken = token;
    console.log('✅ Auth token loaded');

    // Загружаем данные
    Promise.all([
        loadProfile(),
        loadLimits(),
        loadSubscription(),
        loadPredictionHistory()
    ]).finally(() => {
        // Скрываем индикатор загрузки после загрузки всех данных
        const loadingEl = document.getElementById('loading');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    });

    // Обработчики вкладок
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });
});

function switchTab(tabName) {
    // Скрываем все вкладки
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Скрываем все кнопки
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Показываем выбранную вкладку
    document.getElementById(tabName)?.classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');

    // Перезагружаем данные для вкладки
    if (tabName === 'history') {
        loadPredictionHistory();
    } else if (tabName === 'subscription') {
        loadSubscription();
    }
}

function switchToSubscription() {
    switchTab('subscription');
}

async function loadProfile() {
    try {
        console.log('📝 Loading profile...');

        const response = await fetch('/api/user/profile', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        console.log('Response status:', response.status);

        const data = await response.json();

        console.log('Profile data:', data);

        if (data.success && data.data) {
            const userData = data.data.user;
            const fullName = [userData.first_name, userData.last_name]
                .filter(n => n && n !== 'null')
                .join(' ') || 'Не указано';

            const username = userData.username && userData.username !== 'null'
                ? `@${userData.username}`
                : '—';

            const telegramId = userData.telegram_id && userData.telegram_id !== 'null'
                ? userData.telegram_id
                : '—';

            const email = userData.email && userData.email !== 'null'
                ? userData.email
                : '—';

            // Определяем тариф
            const tariffName = data.data.subscription
                ? (data.data.subscription.name || 'Premium')
                : 'Бесплатный';

            const tariffBadge = data.data.subscription
                ? '💎 ' + tariffName
                : '🆓 ' + tariffName;

            // Telegram: показываем username если есть, иначе ID
            const telegram = username !== '—' ? username : telegramId;

            // Всего прогнозов (получаем из данных, если доступно)
            const totalPredictions = userData.total_predictions || 0;

            // Устанавливаем аватар в заголовок
            const headerAvatar = document.getElementById('headerAvatar');
            if (headerAvatar && userData.avatar_url && userData.avatar_url.trim() !== '') {
                headerAvatar.innerHTML = `<img src="${userData.avatar_url}" alt="" style="width: 100%; height: 100%; object-fit: cover;">`;
            }

            const profileHTML = `
                <div class="info-item">
                    <div class="info-label">Имя</div>
                    <div class="info-value">${fullName}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Тариф</div>
                    <div class="subscription-badge ${data.data.subscription ? 'badge-premium' : 'badge-free'}">
                        ${tariffBadge}
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">Email</div>
                    <div class="info-value">${email}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Присоединился</div>
                    <div class="info-value">${new Date(userData.created_at).toLocaleDateString('ru-RU')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Telegram</div>
                    <div class="info-value">${telegram}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Всего прогнозов</div>
                    <div class="info-value">${totalPredictions}</div>
                </div>
            `;

            document.getElementById('profileInfo').innerHTML = profileHTML;
        } else {
            showAlert('❌ ' + (data.error || 'Ошибка загрузки профиля'), 'error');
        }
    } catch (error) {
        console.error('❌ Error loading profile:', error);
        showAlert('❌ Ошибка загрузки профиля: ' + error.message, 'error');
    }
}

async function loadLimits() {
    try {
        console.log('📊 Loading limits...');

        const response = await fetch('/api/user/limits', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const data = await response.json();

        console.log('Limits data:', data);

        if (data.success && data.data) {
            const limits = data.data;

            const dailyPercent = (limits.daily.used / limits.daily.limit) * 100;
            const monthlyPercent = (limits.monthly.used / limits.monthly.limit) * 100;

            const limitsHTML = `
                <div class="limit-card">
                    <div class="limit-label">📅 Прогнозы в день</div>
                    <div class="limit-value">${limits.daily.remaining}/${limits.daily.limit}</div>
                    <div class="limit-bar">
                        <div class="limit-bar-fill" style="width: ${dailyPercent}%"></div>
                    </div>
                </div>
                <div class="limit-card">
                    <div class="limit-label">📆 Прогнозы в месяц</div>
                    <div class="limit-value">${limits.monthly.remaining}/${limits.monthly.limit}</div>
                    <div class="limit-bar">
                        <div class="limit-bar-fill" style="width: ${monthlyPercent}%"></div>
                    </div>
                </div>
            `;

            const limitsContainer = document.getElementById('limitsSection');
            if (limitsContainer) {
                limitsContainer.innerHTML = limitsHTML;
            }

            // Если исчерпаны лимиты, показываем баннер
            const upgradeBanner = document.getElementById('upgradeBanner');
            if (upgradeBanner) {
                if (limits.daily.remaining <= 0 || limits.monthly.remaining <= 0) {
                    upgradeBanner.style.display = 'block';
                } else {
                    upgradeBanner.style.display = 'none';
                }
            }
        } else {
            showAlert('❌ ' + (data.error || 'Ошибка загрузки лимитов'), 'error');
        }
    } catch (error) {
        console.error('❌ Error loading limits:', error);
        showAlert('❌ Ошибка загрузки лимитов: ' + error.message, 'error');
    }
}

async function loadSubscription() {
    try {
        console.log('💳 Loading subscription...');

        const response = await fetch('/api/user/subscription', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const data = await response.json();

        console.log('Subscription data:', data);

        if (data.success && data.data) {
            const subscription = data.data;

            if (subscription) {
                const subName = subscription.name && subscription.name !== 'null'
                    ? subscription.name
                    : 'Активная подписка';

                const subPrice = subscription.price && subscription.price !== 'null'
                    ? `${subscription.price} USD/месяц`
                    : '∞';

                const predictions = subscription.daily_predictions && subscription.daily_predictions !== 'null'
                    ? subscription.daily_predictions
                    : (subscription.monthly_predictions && subscription.monthly_predictions !== 'null'
                        ? subscription.monthly_predictions
                        : '∞');

                const subscriptionHTML = `
                    <div class="card-content">
                        <div class="subscription-info">
                            <div class="subscription-name">💎 ${subName}</div>
                            <div class="subscription-price">${subPrice}</div>
                            <div style="margin-top: 12px; color: var(--text-secondary); font-size: 13px;">
                                ✅ ${predictions} прогнозов
                            </div>
                        </div>
                    </div>
                `;
                document.getElementById('currentSubscription').innerHTML = subscriptionHTML;
            } else {
                document.getElementById('currentSubscription').innerHTML = `
                    <div class="card-content">
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 24px; margin-bottom: 8px;">🆓</div>
                            <div style="font-weight: 600;">Бесплатный план</div>
                            <div style="color: var(--text-secondary); font-size: 13px; margin-top: 8px;">
                                5 прогнозов в день, 5 в месяц
                            </div>
                        </div>
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('❌ Error loading subscription:', error);
    }
}

async function loadPredictionHistory() {
    try {
        console.log('📈 Loading prediction history...');

        const response = await fetch('/api/user/predictions/history?limit=20', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const data = await response.json();

        console.log('History data:', data);

        if (data.success && data.data) {
            if (data.data.length === 0) {
                document.getElementById('historyList').innerHTML = '<p style="text-align: center; color: var(--text-secondary);">История пуста</p>';
                return;
            }

            const historyHTML = data.data.map(prediction => {
                const symbol = prediction.symbol && prediction.symbol !== 'null' ? prediction.symbol : 'N/A';
                const price = prediction.predicted_price && prediction.predicted_price !== 'null'
                    ? `$${formatPrice(prediction.predicted_price)}`
                    : '—';
                const confidence = prediction.confidence && prediction.confidence !== 'null'
                    ? `${prediction.confidence.toFixed(0)}% уверенность`
                    : '—';
                const signal = prediction.signal && prediction.signal !== 'null' ? prediction.signal : 'UNKNOWN';
                const timestamp = prediction.timestamp && prediction.timestamp !== 'null'
                    ? new Date(prediction.timestamp).toLocaleString('ru-RU')
                    : '—';

                return `
                    <div class="history-item">
                        <div>
                            <div class="history-symbol">${symbol}</div>
                            <div class="history-meta">
                                <span>📈 ${price}</span>
                                <span>🎯 ${confidence}</span>
                                <span>📅 ${timestamp}</span>
                            </div>
                        </div>
                        <span class="history-signal signal-${signal.toLowerCase()}">
                            ${signal}
                        </span>
                    </div>
                `;
            }).join('');

            document.getElementById('historyList').innerHTML = historyHTML;
        }
    } catch (error) {
        console.error('❌ Error loading history:', error);
        showAlert('❌ Ошибка загрузки истории: ' + error.message, 'error');
    }
}

function formatPrice(price) {
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

function showAlert(message, type = 'success') {
    const alertEl = document.getElementById('alert');
    const alertText = document.getElementById('alertText');

    alertText.textContent = message;
    alertEl.className = `alert show alert-${type}`;

    setTimeout(() => {
        alertEl.classList.remove('show');
    }, 4000);
}

async function uploadAvatar(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Проверка размера (макс 20MB)
    const maxSize = 20 * 1024 * 1024; // 20MB в байтах
    if (file.size > maxSize) {
        showAlert('❌ Файл слишком большой! Максимальный размер: 20 МБ', 'error');
        return;
    }

    // Проверка типа файла
    if (!file.type.startsWith('image/')) {
        showAlert('❌ Пожалуйста, выберите изображение', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('avatar', file);

    try {
        showAlert('⏳ Загрузка фото...', 'warning');

        const response = await fetch('/api/user/upload-avatar', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            showAlert('✅ Фото профиля обновлено!', 'success');

            // Обновляем аватар в заголовке
            const headerAvatar = document.getElementById('headerAvatar');
            if (headerAvatar && data.avatar_url) {
                headerAvatar.innerHTML = `<img src="${data.avatar_url}?t=${Date.now()}" alt="" style="width: 100%; height: 100%; object-fit: cover;">`;
            }
        } else {
            showAlert('❌ ' + (data.error || 'Ошибка загрузки фото'), 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showAlert('❌ Ошибка загрузки: ' + error.message, 'error');
    }
}