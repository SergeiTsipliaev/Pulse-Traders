let currentUserId = null;

document.addEventListener('DOMContentLoaded', () => {
    // ✅ ИСПРАВЛЕНО: используем правильный ключ 'user_id' (не 'userId')
    const token = localStorage.getItem('auth_token');
    const userId = localStorage.getItem('user_id');

    console.log('✅ Token:', token ? 'есть' : 'нет');
    console.log('✅ User ID:', userId);

    // Получаем user_id
    if (window.Telegram && window.Telegram.WebApp) {
        const webApp = window.Telegram.WebApp;
        const user = webApp.initDataUnsafe?.user;
        if (user) {
            currentUserId = user.id;
        }
    }

    // Если из Telegram не получили, берем из localStorage
    if (!currentUserId) {
        currentUserId = userId;
    }

    if (!currentUserId) {
        showAlert('❌ Ошибка: не удалось получить ID пользователя', 'error');
        console.error('❌ No user ID found');
        return;
    }

    console.log('✅ Current User ID:', currentUserId);

    // Загружаем данные
    loadProfile();
    loadLimits();
    loadSubscription();
    loadPredictionHistory();

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
        console.log('📝 Loading profile for user:', currentUserId);

        const response = await fetch('/api/user/profile', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        console.log('Response status:', response.status);

        const data = await response.json();

        console.log('Profile data:', data);

        if (data.success && data.data) {
            const userData = data.data.user;
            const profileHTML = `
                <div class="info-item">
                    <div class="info-label">Имя</div>
                    <div class="info-value">${userData.first_name || 'Не указано'} ${userData.last_name || ''}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Username</div>
                    <div class="info-value">@${userData.username || 'unknown'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Telegram ID</div>
                    <div class="info-value">${userData.telegram_id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Присоединился</div>
                    <div class="info-value">${new Date(userData.created_at).toLocaleDateString('ru-RU')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Последний визит</div>
                    <div class="info-value">${new Date(userData.last_active).toLocaleString('ru-RU')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Статус</div>
                    <div class="subscription-badge ${data.data.subscription ? 'badge-premium' : 'badge-free'}">
                        ${data.data.subscription ? '💎 Premium' : '🆓 Бесплатный'}
                    </div>
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
        console.log('📊 Loading limits for user:', currentUserId);

        const response = await fetch('/api/user/limits', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        console.log('Limits data:', data);

        if (data.success && data.data) {
            const limits = data.data;

            const dailyPercent = (limits.predictions_used_today / limits.predictions_limit_daily) * 100;
            const monthlyPercent = (limits.predictions_used_month / limits.predictions_limit_monthly) * 100;

            const limitsHTML = `
                <div class="limit-card">
                    <div class="limit-label">📅 Прогнозы в день</div>
                    <div class="limit-value">${limits.predictions_limit_daily - limits.predictions_used_today}/${limits.predictions_limit_daily}</div>
                    <div class="limit-bar">
                        <div class="limit-bar-fill" style="width: ${dailyPercent}%"></div>
                    </div>
                </div>
                <div class="limit-card">
                    <div class="limit-label">📆 Прогнозы в месяц</div>
                    <div class="limit-value">${limits.predictions_limit_monthly - limits.predictions_used_month}/${limits.predictions_limit_monthly}</div>
                    <div class="limit-bar">
                        <div class="limit-bar-fill" style="width: ${monthlyPercent}%"></div>
                    </div>
                </div>
            `;

            document.getElementById('limitsInfo').innerHTML = limitsHTML;

            // Если исчерпаны лимиты, показываем сообщение
            if ((limits.predictions_limit_daily - limits.predictions_used_today) <= 0) {
                document.getElementById('dailyLimitAlert').innerHTML = `
                    <p style="color: #ff6b6b; font-weight: 600;">⚠️ Вы исчерпали дневной лимит!</p>
                    <p style="font-size: 13px; color: var(--text-secondary);">Купите подписку для получения дополнительных прогнозов.</p>
                    <button class="button btn-primary" onclick="switchToSubscription()">💳 Выбрать подписку</button>
                `;
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
        console.log('💳 Loading subscription for user:', currentUserId);

        const response = await fetch('/api/user/subscription', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        console.log('Subscription data:', data);

        if (data.success && data.data) {
            const subscription = data.data;

            if (subscription) {
                const subscriptionHTML = `
                    <div class="card-content">
                        <div class="subscription-info">
                            <div class="subscription-name">💎 ${subscription.name || 'Активная подписка'}</div>
                            <div class="subscription-price">${subscription.price || '∞'} USD/месяц</div>
                            <div style="margin-top: 12px; color: var(--text-secondary); font-size: 13px;">
                                ✅ ${subscription.daily_predictions || subscription.monthly_predictions || '∞'} прогнозов
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
                                5 прогнозов в день, 30 в месяц
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
        console.log('📈 Loading prediction history for user:', currentUserId);

        const response = await fetch('/api/user/predictions/history?limit=20', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        console.log('History data:', data);

        if (data.success && data.data) {
            if (data.data.length === 0) {
                document.getElementById('historyList').innerHTML = '<p style="text-align: center; color: var(--text-secondary);">История пуста</p>';
                return;
            }

            const historyHTML = data.data.map(prediction => `
                <div class="history-item">
                    <div>
                        <div class="history-symbol">${prediction.symbol}</div>
                        <div class="history-meta">
                            <span>📈 $${formatPrice(prediction.predicted_price)}</span>
                            <span>🎯 ${prediction.confidence.toFixed(0)}% уверенность</span>
                            <span>📅 ${new Date(prediction.timestamp).toLocaleString('ru-RU')}</span>
                        </div>
                    </div>
                    <span class="history-signal signal-${prediction.signal.toLowerCase()}">
                        ${prediction.signal}
                    </span>
                </div>
            `).join('');

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