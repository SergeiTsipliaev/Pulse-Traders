const API_URL = '/api';
let searchTimeout = null;

document.addEventListener('DOMContentLoaded', async () => {
    console.log('App loaded');

    // Проверяем авторизацию и обновляем кнопки
    await updateAuthButtons();

    // Загружаем криптовалюты
    await renderCryptoGrid();

    // Поиск
    setupSearch();
});

// ==================== АВТОРИЗАЦИЯ ====================

async function updateAuthButtons() {
    const authButtonsDiv = document.getElementById('authButtons');
    // ✅ ИСПРАВЛЕНО: используем 'auth_token' вместо 'token'
    const token = localStorage.getItem('auth_token');
    const userId = localStorage.getItem('user_id');

    console.log('🔐 Auth check - Token:', token ? 'есть' : 'нет', 'User ID:', userId);

    if (token && userId) {
        // Пользователь авторизован - показываем профиль
        authButtonsDiv.innerHTML = `
            <div class="profile-menu">
                <button class="profile-btn" onclick="toggleProfileMenu()">👤</button>
                <div class="dropdown-menu" id="profileMenu">
                    <div class="user-info">
                        <div style="font-weight: 600;">Мой профиль</div>
                        <div class="user-email" id="userEmail">user@example.com</div>
                    </div>
                    <a href="/dashboard" class="dropdown-item">👤 Личный кабинет</a>
                    <button onclick="logout()" class="dropdown-item danger">🚪 Выйти</button>
                </div>
            </div>
        `;

        // Загружаем имя пользователя
        try {
            const response = await fetch(`${API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data) {
                    const user = data.data;
                    document.getElementById('userEmail').textContent = user.email || user.username || 'User';
                }
            }
        } catch (error) {
            console.error('Error loading user:', error);
        }
    } else {
        // Пользователь не авторизован - показываем кнопку входа
        authButtonsDiv.innerHTML = `
            <a href="/auth.html" class="btn-header">🔐 Войти</a>
        `;
    }
}

function toggleProfileMenu() {
    const menu = document.getElementById('profileMenu');
    if (menu) {
        menu.classList.toggle('show');
    }
}

function logout() {
    if (confirm('Вы уверены?')) {
        // ✅ ИСПРАВЛЕНО: удаляем 'auth_token' вместо 'token'
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_id');
        sessionStorage.removeItem('auth_token');
        window.location.href = '/';
    }
}

// ==================== КРИПТОВАЛЮТЫ ====================

async function renderCryptoGrid() {
    console.log('Loading cryptos...');
    const grid = document.getElementById('cryptoGrid');

    if (!grid) {
        console.error('Grid element not found');
        return;
    }

    grid.innerHTML = '';

    try {
        const response = await fetch(`${API_URL}/cryptos/all`);
        const data = await response.json();

        console.log('Cryptos response:', data);

        if (data.success && data.data) {
            const cryptos = data.data.slice(0, 6);

            console.log('Showing cryptos:', cryptos.length);

            if (cryptos.length === 0) {
                grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #999;">Нет криптовалют</div>';
                return;
            }

            cryptos.forEach(crypto => {
                const card = document.createElement('div');
                card.className = 'crypto-card';
                card.onclick = () => openCrypto(crypto.symbol);

                card.innerHTML = `
                    <div class="crypto-emoji">${crypto.emoji || '💰'}</div>
                    <div class="crypto-symbol">${crypto.display_name || crypto.symbol}</div>
                `;

                grid.appendChild(card);
            });
        } else {
            console.error('Failed to load cryptos:', data.error);
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #999;">Ошибка загрузки</div>';
        }
    } catch (error) {
        console.error('Error rendering cryptos:', error);
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #999;">Ошибка подключения</div>';
    }
}

function openCrypto(symbol) {
    console.log('Opening crypto:', symbol);
    window.location.href = `/crypto-detail.html?symbol=${symbol}`;
}

// ==================== ПОИСК ====================

function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();

        if (query.length < 1) {
            document.getElementById('searchResults').innerHTML = '';
            return;
        }

        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    // Закрываем результаты при клике вне поиска
    document.addEventListener('click', (e) => {
        const searchBox = document.querySelector('.search-box');
        if (searchBox && !searchBox.contains(e.target)) {
            document.getElementById('searchResults').innerHTML = '';
        }
    });
}

async function performSearch(query) {
    if (query.length < 1) return;

    const searchResults = document.getElementById('searchResults');

    try {
        const response = await fetch(`${API_URL}/cryptos/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success && data.data && data.data.length > 0) {
            displaySearchResults(data.data);
        } else {
            searchResults.innerHTML = '<div style="padding: 12px 16px;">Не найдено</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        searchResults.innerHTML = '<div style="padding: 12px 16px;">Ошибка поиска</div>';
    }
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');

    searchResults.innerHTML = results.map(crypto => `
        <div class="search-result-item" onclick="openCrypto('${crypto.symbol}')" style="padding: 12px 16px; cursor: pointer; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
            ${crypto.emoji || '💰'} ${crypto.symbol} - ${crypto.name || ''}
        </div>
    `).join('');
}

// Закрываем меню при клике вне его
document.addEventListener('click', (e) => {
    const profileBtn = document.querySelector('.profile-btn');
    const profileMenu = document.getElementById('profileMenu');

    if (profileBtn && profileMenu && !profileBtn.contains(e.target) && !profileMenu.contains(e.target)) {
        profileMenu.classList.remove('show');
    }
});