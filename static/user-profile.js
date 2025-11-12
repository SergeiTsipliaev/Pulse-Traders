let currentUserId = null;

document.addEventListener('DOMContentLoaded', () => {
    // Получаем user_id
    if (window.Telegram && window.Telegram.WebApp) {
        const webApp = window.Telegram.WebApp;
        const user = webApp.initDataUnsafe?.user;
        if (user) {
            currentUserId = user.id;
            localStorage.setItem('userId', user.id);
        }
    }

    if (!currentUserId) {
        currentUserId = localStorage.getItem('userId');
    }

    if (!currentUserId) {
        showAlert('❌ Ошибка: не удалось получить ID пользователя', 'error');
        return;
    }

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
        const response = await fetch('/api/user/profile', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

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
        }
    } catch (error) {
        console.error('Error loading profile:', error);
        showAlert('❌ Ошибка загрузки профиля', 'error');
    }
}

async function loadLimits() {
    try {
        const response = await fetch('/api/user/limits', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        if (data.success && data.data) {
            const limits = data.data;

            const dailyPercent = (limits.daily.used / limits.daily.limit) * 100;
            const monthlyPercent = (limits.monthly.used / limits.monthly.limit) * 100;

            const limitsHTML = `
                <div class="limit-card">
                    <div class="limit-label">📅 Прогнозы в день</div>
                    <div class="limit-value">${limits.daily.remaining}/${limits.daily.limit}</div>
                    <div class="limit-bar">
                        <div class="limit-fill" style="width: ${dailyPercent}%"></div>
                    </div>
                    <div class="limit-percent">Использовано: ${limits.daily.used} (${Math.round(dailyPercent)}%)</div>
                </div>
                <div class="limit-card">
                    <div class="limit-label">📊 Прогнозы в месяц</div>
                    <div class="limit-value">${limits.monthly.remaining}/${limits.monthly.limit}</div>
                    <div class="limit-bar">
                        <div class="limit-fill" style="width: ${monthlyPercent}%"></div>
                    </div>
                    <div class="limit-percent">Использовано: ${limits.monthly.used} (${Math.round(monthlyPercent)}%)</div>
                </div>
            `;

            document.getElementById('limitsSection').innerHTML = limitsHTML;

            // Показываем баннер если лимит исчерпан
            if (!limits.can_predict && limits.needs_premium) {
                document.getElementById('upgradeBanner').style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error loading limits:', error);
        showAlert('❌ Ошибка загрузки лимитов', 'error');
    }
}

async function loadSubscription() {
    try {
        const response = await fetch('/api/user/subscription', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        if (data.success && data.data) {
            const subData = data.data;

            let currentSubHTML = '';
            if (subData.status === 'active' && subData.subscription) {
                const sub = subData.subscription;
                currentSubHTML = `
                    <div class="tier-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); margin-bottom: 20px;">
                        <div class="tier-name">💎 ${sub.display_name}</div>
                        <div class="tier-features">
                            <span>💵 $${sub.price}/месяц</span>
                            <span>📊 ${sub.daily_predictions} прогнозов в день</span>
                            <span>📅 ${sub.monthly_predictions} прогнозов в месяц</span>
                            ${sub.expires_at ? `<span>⏰ Действует до: ${new Date(sub.expires_at).toLocaleDateString('ru-RU')}</span>` : ''}
                        </div>
                        <button class="tier-button active">✅ Текущий план</button>
                    </div>
                `;
            } else if (subData.status === 'expired') {
                currentSubHTML = `
                    <div class="card" style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--danger); margin-bottom: 20px;">
                        <div class="card-title" style="color: var(--danger);">⏰ Подписка истекла</div>
                        <p>Ваша подписка закончилась ${new Date(subData.subscription.expires_at).toLocaleDateString('ru-RU')}. Обновите подписку ниже.</p>
                    </div>
                `;
            } else {
                currentSubHTML = `
                    <div class="tier-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); margin-bottom: 20px;">
                        <div class="tier-name">🆓 Бесплатный тариф</div>
                        <div class="tier-features">
                            <span>💵 Бесплатно</span>
                            <span>📊 5 прогнозов в день</span>
                            <span>📅 30 прогнозов в месяц</span>
                        </div>
                        <button class="tier-button active">✅ Текущий план</button>
                    </div>
                `;
            }

            document.getElementById('currentSubscription').innerHTML = currentSubHTML;

            // Загружаем доступные тарифы
            loadAvailableTiers();
        }
    } catch (error) {
        console.error('Error loading subscription:', error);
        showAlert('❌ Ошибка загрузки подписки', 'error');
    }
}

async function loadAvailableTiers() {
    try {
        const response = await fetch('/api/user/subscription/available-tiers', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        if (data.success && data.data) {
            const tiersHTML = data.data.map(tier => `
                <div class="tier-card">
                    <div class="tier-name">⭐ ${tier.display_name}</div>
                    <div style="font-size: 28px; font-weight: 700; margin: 10px 0;">$${tier.price}</div>
                    <div style="font-size: 12px; color: rgba(255, 255, 255, 0.8); margin-bottom: 10px;">/месяц</div>
                    <div class="tier-features">
                        <span>📊 ${tier.daily_predictions} в день</span>
                        <span>📅 ${tier.monthly_predictions} в месяц</span>
                        ${tier.description ? `<span>${tier.description}</span>` : ''}
                    </div>
                    <button class="tier-button" onclick="subscribeToPlan(${tier.id}, '${tier.display_name}')">
                        🔒 Выбрать план
                    </button>
                </div>
            `).join('');

            document.getElementById('tiersGrid').innerHTML = tiersHTML;
        }
    } catch (error) {
        console.error('Error loading tiers:', error);
    }
}

async function subscribeToPlan(tierId, tierName) {
    alert(`Функция оплаты в разработке.\n\nТариф: ${tierName}\n\nПосле интеграции платежей (Stripe/Yoo.Kassa) можно будет подписаться здесь.`);

    // TODO: Интегрировать Stripe/Yoo.Kassa API
    // Логика:
    // 1. Отправить запрос на /api/payment/create-session
    // 2. Перенаправить на платежную форму
    // 3. После успешной оплаты обновить подписку
}

async function loadPredictionHistory() {
    try {
        const response = await fetch('/api/user/predictions/history?limit=20', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

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
        console.error('Error loading history:', error);
        showAlert('❌ Ошибка загрузки истории', 'error');
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