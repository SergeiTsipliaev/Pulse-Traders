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
                <button class="profile-btn" id="profileBtn" onclick="toggleProfileMenu()">👤</button>
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

        // Загружаем данные пользователя
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

                    // Если есть фото профиля - показываем его, иначе оставляем emoji
                    const profileBtn = document.getElementById('profileBtn');
                    if (profileBtn) {
                        if (user.avatar_url && user.avatar_url.trim() !== '') {
                            // Есть фото - показываем картинку
                            const img = new Image();
                            img.onload = function() {
                                profileBtn.innerHTML = `<img src="${user.avatar_url}" alt="" style="width: 100%; height: 100%; object-fit: cover;">`;
                            };
                            img.onerror = function() {
                                // Если картинка не загрузилась - оставляем emoji
                                console.log('Avatar image failed to load, keeping emoji');
                            };
                            img.src = user.avatar_url;
                        }
                        // Если фото нет - оставляем emoji 👤 (уже установлен при создании)
                    }
                }
            }
        } catch (error) {
            console.error('Error loading user:', error);
        }
    } else {
        // Пользователь не авторизован - показываем кнопку входа
        authButtonsDiv.innerHTML = `
            <a href="/login" class="btn-header">🔐 Войти</a>
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
    // Удаляем токены без подтверждения
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_id');
    sessionStorage.removeItem('auth_token');
    window.location.href = '/';
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

                // Для популярных показываем логотип, для остальных - emoji
                if (crypto.logo && crypto.logo.trim() !== '') {
                    card.innerHTML = `
                        <img src="${crypto.logo}" alt="${crypto.display_name}" class="crypto-logo" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover;">
                        <div class="crypto-symbol">${crypto.display_name || crypto.symbol}</div>
                    `;
                } else {
                    card.innerHTML = `
                        <div class="crypto-emoji">${crypto.emoji || '💰'}</div>
                        <div class="crypto-symbol">${crypto.display_name || crypto.symbol}</div>
                    `;
                }

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
    window.location.href = `/crypto-detail?symbol=${symbol}`;
}

// ==================== ПОИСК ====================

function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();

        if (query.length < 1) {
            const searchResults = document.getElementById('searchResults');
            searchResults.innerHTML = '';
            searchResults.classList.remove('show');
            return;
        }

        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    // Закрываем результаты при клике вне поиска
    document.addEventListener('click', (e) => {
        const searchContainer = document.querySelector('.search-container');
        const searchResults = document.getElementById('searchResults');
        if (searchContainer && !searchContainer.contains(e.target)) {
            searchResults.innerHTML = '';
            searchResults.classList.remove('show');
        }
    });
}

async function performSearch(query) {
    const searchResults = document.getElementById('searchResults');

    if (!searchResults) {
        console.error('searchResults element not found in performSearch');
        return;
    }

    // Если поле пустое - скрываем результаты
    if (query.length < 1) {
        searchResults.classList.remove('show');
        searchResults.innerHTML = '';
        return;
    }

    console.log('Searching for:', query);

    try {
        const response = await fetch(`${API_URL}/cryptos/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        console.log('Search response:', data);

        if (data.success && data.data && data.data.length > 0) {
            displaySearchResults(data.data);
        } else {
            // Показываем контейнер даже для "не найдено"
            searchResults.classList.add('show');
            searchResults.innerHTML = '<div style="padding: 12px 16px; color: var(--text-secondary);">Не найдено</div>';
        }
    } catch (error) {
        console.error('Search error:', error);
        // Показываем контейнер для ошибки
        searchResults.classList.add('show');
        searchResults.innerHTML = '<div style="padding: 12px 16px; color: var(--danger);">Ошибка поиска</div>';
    }
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');

    if (!searchResults) {
        console.error('searchResults element not found');
        return;
    }

    console.log('Displaying search results:', results.length);

    // Показываем контейнер результатов
    searchResults.classList.add('show');

    searchResults.innerHTML = results.map(crypto => {
        const symbolClean = crypto.symbol.replace('USDT', '');
        const firstLetter = symbolClean.charAt(0);

        return `
            <div class="search-result-item" onclick="openCrypto('${crypto.symbol}')" style="
                padding: 12px 16px;
                cursor: pointer;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                transition: all 0.2s;
            "
            onmouseover="this.style.background='rgba(124, 58, 237, 0.1)'"
            onmouseout="this.style.background='transparent'">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <!-- Цветной кружок с буквой -->
                    <div style="
                        width: 36px;
                        height: 36px;
                        border-radius: 50%;
                        background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
                        box-shadow: 0 2px 4px rgba(91, 33, 182, 0.3);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 16px;
                        font-weight: 700;
                        color: white;
                        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
                        flex-shrink: 0;
                    ">${firstLetter}</div>
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-weight: 600; font-size: 14px;">${crypto.display_name || symbolClean}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${crypto.name || symbolClean}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Закрываем меню при клике вне его
document.addEventListener('click', (e) => {
    const profileBtn = document.querySelector('.profile-btn');
    const profileMenu = document.getElementById('profileMenu');

    if (profileBtn && profileMenu && !profileBtn.contains(e.target) && !profileMenu.contains(e.target)) {
        profileMenu.classList.remove('show');
    }
});