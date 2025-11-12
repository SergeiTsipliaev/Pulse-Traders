// Получаем user_id из Telegram Web App
let currentUserId = null;

document.addEventListener('DOMContentLoaded', () => {
    // Пытаемся получить ID пользователя из Telegram
    if (window.Telegram && window.Telegram.WebApp) {
        const webApp = window.Telegram.WebApp;
        const initData = webApp.initData;
        const user = webApp.initDataUnsafe?.user;
        if (user) {
            currentUserId = user.id;
        }
    }

    // Проверяем localStorage если Telegram недоступен
    if (!currentUserId) {
        currentUserId = localStorage.getItem('userId');
    }

    if (!currentUserId) {
        showAlert('❌ Ошибка: не удалось получить ID пользователя', 'error');
        return;
    }

    // Настраиваем обработчики вкладок
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });

    // Загружаем данные
    loadStats();
    loadUsers();
    loadTiers();
});

function switchTab(tabName) {
    // Скрываем все вкладки
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Скрываем все кнопки вкладок
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Показываем выбранную вкладку
    const content = document.getElementById(tabName);
    if (content) {
        content.classList.add('active');
    }

    // Выделяем кнопку вкладки
    document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');

    // Загружаем данные для вкладки
    if (tabName === 'dashboard') {
        loadStats();
    } else if (tabName === 'users') {
        loadUsers();
    } else if (tabName === 'subscriptions') {
        loadTiers();
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/admin/stats', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        if (data.success && data.data) {
            const stats = data.data;

            // Обновляем header
            document.getElementById('totalUsersHeader').textContent = stats.total_users;
            document.getElementById('activeUsersHeader').textContent = stats.active_users;
            document.getElementById('premiumUsersHeader').textContent = stats.premium_users;

            // Обновляем dashboard
            document.getElementById('totalUsers').textContent = stats.total_users;
            document.getElementById('activeUsers').textContent = stats.active_users;
            document.getElementById('premiumUsers').textContent = stats.premium_users;
            document.getElementById('totalPredictions').textContent = stats.total_predictions;
            document.getElementById('totalRevenue').textContent = `$${stats.total_revenue.toFixed(2)}`;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        showAlert('❌ Ошибка загрузки статистики', 'error');
    }
}

async function loadUsers(page = 0) {
    const limit = 20;
    const offset = page * limit;

    document.getElementById('usersLoading').style.display = 'block';

    try {
        const response = await fetch(`/api/admin/users?limit=${limit}&offset=${offset}`, {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        if (data.success && data.data) {
            displayUsers(data.data);
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showAlert('❌ Ошибка загрузки пользователей', 'error');
    } finally {
        document.getElementById('usersLoading').style.display = 'none';
    }
}

function displayUsers(users) {
    const container = document.getElementById('usersList');

    if (users.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Пользователей не найдено</p>';
        return;
    }

    container.innerHTML = users.map(user => `
        <div class="user-card">
            <div class="user-info">
                <div class="user-name">
                    ${user.first_name || ''} ${user.last_name || ''}
                    <span style="color: var(--text-secondary);">@${user.username || 'unknown'}</span>
                </div>
                <div class="user-meta">
                    <span>ID: ${user.telegram_id}</span>
                    <span>Присоединился: ${new Date(user.created_at).toLocaleDateString()}</span>
                    <span>Прогнозов: ${user.predictions_used_month || 0}/${user.predictions_limit_monthly || 'N/A'}</span>
                    ${user.subscription_tier ? `<span class="badge premium">${user.subscription_tier}</span>` : '<span class="badge free">Бесплатный</span>'}
                    ${user.is_admin ? '<span class="badge" style="background: #8b5cf6;">Admin</span>' : ''}
                </div>
            </div>
            <div class="user-actions">
                ${user.is_admin ? '' : `
                    <button class="btn-secondary btn-small" onclick="makeAdmin(${user.id})">👑 Admin</button>
                `}
                ${user.is_banned ? `
                    <button class="btn-secondary btn-small" onclick="unbanUser(${user.id})">✅ Разбан</button>
                ` : `
                    <button class="btn-danger btn-small" onclick="banUser(${user.id})">🚫 Бан</button>
                `}
                <button class="btn-primary btn-small" onclick="viewUser(${user.id})">👁️ Смотреть</button>
            </div>
        </div>
    `).join('');
}

async function loadTiers() {
    try {
        const response = await fetch('/api/admin/tiers', {
            headers: {
                'x-user-id': currentUserId
            }
        });

        const data = await response.json();

        if (data.success && data.data) {
            displayTiers(data.data);
        }
    } catch (error) {
        console.error('Error loading tiers:', error);
        showAlert('❌ Ошибка загрузки тарифов', 'error');
    }
}

function displayTiers(tiers) {
    const container = document.getElementById('tiersList');

    if (tiers.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Тарифов не найдено</p>';
        return;
    }

    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Название</th>
                    <th>Цена</th>
                    <th>В день</th>
                    <th>В месяц</th>
                    <th>Статус</th>
                    <th>Действие</th>
                </tr>
            </thead>
            <tbody>
                ${tiers.map(tier => `
                    <tr>
                        <td>
                            <strong>${tier.display_name}</strong>
                            <div style="font-size: 11px; color: var(--text-secondary);">${tier.description || ''}</div>
                        </td>
                        <td>$${tier.price}</td>
                        <td>${tier.daily_predictions}</td>
                        <td>${tier.monthly_predictions}</td>
                        <td>
                            ${tier.is_active ?
                                '<span class="badge active">Активный</span>' :
                                '<span class="badge inactive">Неактивный</span>'
                            }
                        </td>
                        <td>
                            <button class="btn-secondary btn-small" onclick="editTier(${tier.id})">✏️ Редак.</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function showCreateTierForm() {
    document.getElementById('createTierForm').style.display = 'block';
}

function hideCreateTierForm() {
    document.getElementById('createTierForm').style.display = 'none';
}

async function handleCreateTier(event) {
    event.preventDefault();

    const tierData = {
        name: document.getElementById('tierName').value,
        display_name: document.getElementById('tierDisplayName').value,
        price: parseFloat(document.getElementById('tierPrice').value),
        monthly_predictions: parseInt(document.getElementById('tierMonthly').value),
        daily_predictions: parseInt(document.getElementById('tierDaily').value),
        description: document.getElementById('tierDescription').value
    };

    try {
        const response = await fetch('/api/admin/tiers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-user-id': currentUserId
            },
            body: JSON.stringify(tierData)
        });

        const data = await response.json();

        if (data.success) {
            showAlert('✅ Тариф создан успешно', 'success');
            hideCreateTierForm();
            event.target.reset();
            loadTiers();
        } else {
            showAlert(`❌ ${data.error || 'Ошибка создания тарифа'}`, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('❌ Ошибка создания тарифа', 'error');
    }
}

async function makeAdmin(userId) {
    if (!confirm('Сделать пользователя администратором?')) return;

    try {
        const response = await fetch(`/api/admin/users/${userId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'x-user-id': currentUserId
            },
            body: JSON.stringify({ is_admin: true })
        });

        const data = await response.json();

        if (data.success) {
            showAlert('✅ Пользователь - администратор', 'success');
            loadUsers();
        } else {
            showAlert('❌ Ошибка обновления статуса', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('❌ Ошибка', 'error');
    }
}

async function banUser(userId) {
    if (!confirm('Забанить пользователя?')) return;

    try {
        const response = await fetch(`/api/admin/users/${userId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'x-user-id': currentUserId
            },
            body: JSON.stringify({ is_banned: true })
        });

        const data = await response.json();

        if (data.success) {
            showAlert('✅ Пользователь забанен', 'success');
            loadUsers();
        } else {
            showAlert('❌ Ошибка бана', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('❌ Ошибка', 'error');
    }
}

async function unbanUser(userId) {
    if (!confirm('Разбанить пользователя?')) return;

    try {
        const response = await fetch(`/api/admin/users/${userId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'x-user-id': currentUserId
            },
            body: JSON.stringify({ is_banned: false })
        });

        const data = await response.json();

        if (data.success) {
            showAlert('✅ Пользователь разбанен', 'success');
            loadUsers();
        } else {
            showAlert('❌ Ошибка разбана', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('❌ Ошибка', 'error');
    }
}

function viewUser(userId) {
    alert(`Просмотр пользователя ${userId} - функция в разработке`);
}

function editTier(tierId) {
    alert(`Редактирование тарифа ${tierId} - функция в разработке`);
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