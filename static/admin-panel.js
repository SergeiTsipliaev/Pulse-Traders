let adminToken = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Проверяем токены (сначала admin_token, потом auth_token)
    adminToken = localStorage.getItem('admin_token') || localStorage.getItem('auth_token');

    if (!adminToken) {
        show404Page();
        return;
    }

    // Проверяем права доступа
    try {
        const response = await fetch('/api/admin/stats', {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (response.status === 401 || response.status === 403) {
            // Нет прав доступа - показываем 404
            show404Page();
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to verify admin rights');
        }
    } catch (error) {
        console.error('Error checking admin rights:', error);
        show404Page();
        return;
    }

    // Загружаем данные
    await loadStats();
    await loadUsers();
});

function show404Page() {
    document.body.innerHTML = `
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #e8e8e8;
        ">
            <div style="
                background: #1a1f2e;
                border-radius: 20px;
                padding: 60px 40px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
                max-width: 500px;
            ">
                <h1 style="
                    font-size: 72px;
                    margin: 0 0 20px 0;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                ">404</h1>
                <h2 style="
                    font-size: 24px;
                    margin: 0 0 16px 0;
                    color: #e8e8e8;
                ">Страница не найдена</h2>
                <p style="
                    color: #8899a6;
                    margin: 0 0 30px 0;
                    font-size: 16px;
                ">У вас нет доступа к этой странице</p>
                <a href="/" style="
                    display: inline-block;
                    padding: 14px 32px;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    text-decoration: none;
                    border-radius: 10px;
                    font-weight: 600;
                    transition: transform 0.3s;
                " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                    Вернуться на главную
                </a>
            </div>
        </div>
    `;
}

async function loadStats() {
    try {
        const response = await fetch('/api/admin/stats', {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load stats');
        }

        const data = await response.json();

        if (data.success && data.data) {
            document.getElementById('totalUsers').textContent = data.data.total_users || 0;
            document.getElementById('activeUsers').textContent = data.data.active_users || 0;
            document.getElementById('adminUsers').textContent = data.data.admin_users || 0;
            document.getElementById('totalPredictions').textContent = data.data.total_predictions || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        showAlert('❌ Ошибка загрузки статистики', 'error');
    }
}

async function loadUsers() {
    try {
        document.getElementById('usersLoading').style.display = 'block';
        document.getElementById('usersTable').style.display = 'none';

        const response = await fetch('/api/admin/users?limit=100', {
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load users');
        }

        const data = await response.json();

        if (data.success && data.data) {
            const tbody = document.getElementById('usersTableBody');
            tbody.innerHTML = '';

            data.data.forEach(user => {
                const row = document.createElement('tr');

                const fullName = [user.first_name, user.last_name]
                    .filter(n => n && n !== 'null')
                    .join(' ') || 'Не указано';

                const email = user.email && user.email !== 'null' ? user.email : '—';
                const isActive = user.is_active;
                const isAdmin = user.is_admin;

                row.innerHTML = `
                    <td>#${user.id}</td>
                    <td>
                        <div class="user-avatar">👤</div>
                        ${fullName}
                    </td>
                    <td>${email}</td>
                    <td>
                        <span class="badge ${isActive ? 'badge-active' : 'badge-inactive'}">
                            ${isActive ? 'Активен' : 'Неактивен'}
                        </span>
                    </td>
                    <td>
                        <span class="badge ${isAdmin ? 'badge-admin' : 'badge-user'}">
                            ${isAdmin ? 'Администратор' : 'Пользователь'}
                        </span>
                    </td>
                    <td>
                        <button class="action-btn action-btn-toggle" onclick="toggleAdmin(${user.id}, ${isAdmin})">
                            ${isAdmin ? 'Отозвать права' : 'Выдать права'}
                        </button>
                    </td>
                `;

                tbody.appendChild(row);
            });

            document.getElementById('usersLoading').style.display = 'none';
            document.getElementById('usersTable').style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showAlert('❌ Ошибка загрузки пользователей', 'error');
        document.getElementById('usersLoading').style.display = 'none';
    }
}

async function toggleAdmin(userId, currentIsAdmin) {
    if (!confirm(`Вы уверены, что хотите ${currentIsAdmin ? 'отозвать' : 'выдать'} права администратора?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/users/${userId}/toggle-admin`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`
            }
        });

        const data = await response.json();

        if (data.success) {
            showAlert(`✅ ${data.message}`, 'success');
            await loadUsers();
            await loadStats();
        } else {
            showAlert('❌ Ошибка: ' + (data.error || 'Неизвестная ошибка'), 'error');
        }
    } catch (error) {
        console.error('Error toggling admin:', error);
        showAlert('❌ Ошибка изменения прав', 'error');
    }
}

function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        localStorage.removeItem('admin_token');
        localStorage.removeItem('auth_token');
        window.location.href = '/';
    }
}

function showAlert(message, type) {
    const alert = document.getElementById('alert');
    alert.textContent = message;
    alert.className = `alert alert-${type} show`;

    setTimeout(() => {
        alert.classList.remove('show');
    }, 4000);
}
