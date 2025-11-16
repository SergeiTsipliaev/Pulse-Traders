"""
Authentication API routes для email/пароль, Google OAuth и Telegram
"""
import requests
import logging
import os
import secrets
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel, EmailStr
import bcrypt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# ==================== ENV ПЕРЕМЕННЫЕ ====================




WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://pulse-traders.com')

ADMIN_IDS = os.getenv('ADMIN_IDS', '').split(',') if os.getenv('ADMIN_IDS') else []

# ==================== МОДЕЛИ ====================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

class GoogleTokenRequest(BaseModel):
    token: str

class TelegramAuthRequest(BaseModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    is_bot: bool = False
    language_code: str = ""
    init_data: str = ""

# ==================== EMAIL СЕРВИС ====================

async def send_email(to_email: str, subject: str, html_content: str):
    """Отправить письмо"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = to_email

        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"✅ Письмо отправлено: {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки письма: {e}")
        return False

# ==================== ХЕШИРОВАНИЕ ПАРОЛЕЙ ====================

def hash_password(password: str) -> str:
    """Хешировать пароль"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Проверить пароль"""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception as e:
        logger.error(f"Ошибка проверки пароля: {e}")
        return False

# ==================== JWT ТОКЕНЫ ====================

def create_jwt_token(user_id: int, email: str, expires_hours: int = None) -> str:
    """Создать JWT токен"""
    if expires_hours is None:
        expires_hours = JWT_EXPIRATION_HOURS

    payload = {
        'sub': str(user_id),
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=expires_hours)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    """Проверить JWT токен"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ==================== EMAIL ВЕРИФИКАЦИЯ ====================

def generate_verification_code() -> str:
    """Генерировать 6-значный код"""
    return ''.join(str(secrets.randbelow(10)) for _ in range(6))

async def save_verification_code(db, email: str, code: str):
    """Сохранить код верификации"""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM email_verifications
                WHERE email = $1
            """, email)

            await conn.execute("""
                INSERT INTO email_verifications (email, code, expires_at)
                VALUES ($1, $2, $3)
            """, email, code, datetime.utcnow() + timedelta(minutes=15))

        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения кода: {e}")
        return False

async def verify_email_code(db, email: str, code: str) -> bool:
    """Проверить код верификации"""
    try:
        async with db.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT * FROM email_verifications
                WHERE email = $1 AND code = $2 AND expires_at > $3
            """, email, code, datetime.utcnow())

            if result:
                await conn.execute("DELETE FROM email_verifications WHERE email = $1", email)
                return True
            return False
    except Exception as e:
        logger.error(f"Ошибка проверки кода: {e}")
        return False

# ==================== ENDPOINTS ====================

@router.post("/register")
async def register(request: Request, body: RegisterRequest):
    """Регистрация с email и паролем"""
    db = request.state.db
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        async with db.pool.acquire() as conn:
            existing_user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                body.email
            )

            if existing_user:
                return JSONResponse(
                    status_code=400,
                    content={'success': False, 'error': 'Этот email уже зарегистрирован'}
                )

            hashed_password = hash_password(body.password)

            # Создаем пользователя с уникальным telegram_id (используем email hash)
            import hashlib
            telegram_id = int(hashlib.sha256(body.email.encode()).hexdigest()[:15], 16)

            user = await conn.fetchrow("""
                INSERT INTO users (telegram_id, email, password_hash, first_name, is_active)
                VALUES ($1, $2, $3, $4, FALSE)
                RETURNING id, email
            """, telegram_id, body.email, hashed_password, body.name)

            if not user:
                raise HTTPException(status_code=400, detail="Failed to create user")

            user_id = user['id']

            # Создаем лимиты для нового пользователя
            await conn.execute("""
                INSERT INTO prediction_limits (user_id, predictions_limit_daily, predictions_limit_monthly)
                VALUES ($1, 5, 5)
            """, user_id)

            code = generate_verification_code()
            await save_verification_code(db, body.email, code)

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px;">
                    <h2>Подтверждение email</h2>
                    <p>Ваш код подтверждения:</p>
                    <h1 style="color: #667eea; letter-spacing: 3px;">{code}</h1>
                    <p>Код действителен 15 минут</p>
                </div>
            </body>
        </html>
        """

        await send_email(body.email, "Подтверждение email", html_content)

        logger.info(f"✅ Регистрация: {body.email}")

        return JSONResponse({
            'success': True,
            'user_id': user_id,
            'message': 'Проверьте вашу почту'
        })

    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-email")
async def verify_email(request: Request, body: VerifyEmailRequest):
    """Проверить код подтверждения email"""
    db = request.state.db
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        is_valid = await verify_email_code(db, body.email, body.code)

        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={'success': False, 'error': 'Неверный или истекший код'}
            )

        async with db.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                body.email
            )

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user_id = user['id']

            await conn.execute(
                "UPDATE users SET is_active = TRUE, verified_at = $1 WHERE id = $2",
                datetime.utcnow(),
                user_id
            )

        token = create_jwt_token(user_id, body.email)

        logger.info(f"✅ Email подтвержден: {body.email}")

        return JSONResponse({
            'success': True,
            'user_id': user_id,
            'token': token,
            'message': 'Email успешно подтвержден'
        })

    except Exception as e:
        logger.error(f"Ошибка верификации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(request: Request, body: LoginRequest):
    """Вход по email и пароль"""
    db = request.state.db
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id, password_hash, is_active FROM users WHERE email = $1",
                body.email
            )

            if not user:
                return JSONResponse(
                    status_code=401,
                    content={'success': False, 'error': 'Email или пароль неверны'}
                )

            user_id = user['id']
            password_hash = user['password_hash']
            is_active = user['is_active']

            if not verify_password(body.password, password_hash):
                return JSONResponse(
                    status_code=401,
                    content={'success': False, 'error': 'Email или пароль неверны'}
                )

            if not is_active:
                return JSONResponse(
                    status_code=403,
                    content={'success': False, 'error': 'Email не подтвержден'}
                )

            token = create_jwt_token(user_id, body.email)

            await conn.execute(
                "UPDATE users SET last_active = $1 WHERE id = $2",
                datetime.utcnow(),
                user_id
            )

        logger.info(f"✅ Успешный вход: {body.email}")

        return JSONResponse({
            'success': True,
            'user_id': user_id,
            'token': token,
            'message': 'Добро пожаловать!'
        })

    except Exception as e:
        logger.error(f"Ошибка входа: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google")
async def google_login(request: Request, body: GoogleTokenRequest):
    """Вход через Google OAuth"""
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        if not GOOGLE_CLIENT_ID:
            logger.error("❌ GOOGLE_CLIENT_ID не установлен в .env")
            return JSONResponse(
                status_code=500,
                content={'success': False, 'error': 'Google OAuth не настроен'}
            )

        import requests as req

        # Верифицируем токен через Google API
        response = req.get(
            'https://www.googleapis.com/oauth2/v1/tokeninfo',
            params={'id_token': body.token},
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"Google token validation failed: {response.text}")
            return JSONResponse(
                status_code=400,
                content={'success': False, 'error': 'Invalid token'}
            )

        idinfo = response.json()
        logger.info(f"Token info: {idinfo}")

        # Декодируем id_token для получения полной информации, включая фото
        import jwt
        import os
        from pathlib import Path

        try:
            # Декодируем id_token без верификации (уже верифицирован через tokeninfo)
            decoded_token = jwt.decode(body.token, options={"verify_signature": False})
            logger.info(f"Decoded token: {decoded_token}")
            google_avatar_url = decoded_token.get('picture', None)
        except Exception as e:
            logger.error(f"Error decoding id_token: {e}")
            google_avatar_url = None

        email = idinfo.get('email')
        name = decoded_token.get('name') if 'decoded_token' in locals() else idinfo.get('name', email.split('@')[0] if email else 'User')
        google_id = str(idinfo.get('user_id')) if idinfo.get('user_id') else None

        # Скачиваем и сохраняем аватар локально
        avatar_url = None
        if google_avatar_url:
            try:
                # Скачиваем изображение
                img_response = req.get(google_avatar_url, timeout=10)
                if img_response.status_code == 200:
                    # Создаем директорию если не существует
                    avatars_dir = Path("static/avatars")
                    avatars_dir.mkdir(exist_ok=True)

                    # Сохраняем с именем google_id
                    file_extension = 'jpg'  # Google обычно возвращает JPG
                    filename = f"{google_id}.{file_extension}"
                    filepath = avatars_dir / filename

                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)

                    # Сохраняем относительный путь
                    avatar_url = f"/static/avatars/{filename}"
                    logger.info(f"✅ Avatar saved: {avatar_url}")
                else:
                    logger.warning(f"Failed to download avatar: {img_response.status_code}")
            except Exception as e:
                logger.error(f"Error downloading avatar: {e}")
                avatar_url = None

        if not email:
            return JSONResponse(
                status_code=400,
                content={'success': False, 'error': 'No email in token'}
            )

        # Используем метод Database
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1 OR google_id = $2",
                email, google_id
            )

            if user:
                user_id = user['id']
            else:
                user = await conn.fetchrow("""
                    INSERT INTO users (email, first_name, google_id, avatar_url, is_active, verified_at)
                    VALUES ($1, $2, $3, $4, TRUE, CURRENT_TIMESTAMP)
                    RETURNING id
                """, email, name, google_id, avatar_url)

                user_id = user['id']

                # Создаем лимиты для нового пользователя
                await conn.execute("""
                    INSERT INTO prediction_limits (user_id, predictions_limit_daily, predictions_limit_monthly)
                    VALUES ($1, 5, 5)
                """, user_id)

            token = create_jwt_token(user_id, email)

            await conn.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP, google_id = $1, avatar_url = $2 WHERE id = $3",
                google_id,
                avatar_url,
                user_id
            )

        logger.info(f"✅ Вход через Google: {email}")

        return JSONResponse({
            'success': True,
            'user_id': user_id,
            'token': token,
            'email': email,
            'message': 'Добро пожаловать!'
        })

    except Exception as e:
        logger.error(f"❌ Google OAuth ошибка: {e}")
        return JSONResponse(
            status_code=400,
            content={'success': False, 'error': f'Authentication failed: {str(e)}'}
        )


@router.post("/telegram")
async def telegram_auth(request: Request, body: TelegramAuthRequest):
    """
    OAuth через Telegram Web App - РЕАЛЬНАЯ интеграция
    Получает данные пользователя прямо из Telegram Web App
    """
    try:
        db = request.state.db

        if not db or not db.is_connected:
            logger.error("❌ Database не подключена")
            return JSONResponse(
                status_code=503,
                content={'success': False, 'error': 'Database unavailable'}
            )

        telegram_id = body.id
        first_name = body.first_name
        last_name = body.last_name
        username = body.username

        logger.info(f"📱 Telegram Web App auth: id={telegram_id}, username={username}")

        if not telegram_id:
            logger.error("❌ No telegram_id provided")
            return JSONResponse(
                status_code=400,
                content={'success': False, 'error': 'Invalid Telegram data'}
            )

        # Используем asyncpg напрямую
        async with db.pool.acquire() as conn:
            # Проверяем, существует ли пользователь
            user = await conn.fetchrow(
                "SELECT id, is_active FROM users WHERE telegram_id = $1",
                telegram_id
            )

            if user:
                user_id = user['id']
                logger.info(f"✅ Existing Telegram user found: {user_id}")

                # Обновляем данные пользователя если нужно
                await conn.execute(
                    """UPDATE users 
                       SET first_name = $1, last_name = $2, username = $3, last_active = CURRENT_TIMESTAMP 
                       WHERE id = $4""",
                    first_name, last_name, username, user_id
                )
            else:
                # Создаем нового пользователя
                email = f"tg_{telegram_id}@pulsetraders.local"
                user = await conn.fetchrow("""
                    INSERT INTO users (telegram_id, first_name, last_name, username, email, is_active, verified_at)
                    VALUES ($1, $2, $3, $4, $5, TRUE, CURRENT_TIMESTAMP)
                    RETURNING id
                """, telegram_id, first_name, last_name, username, email)

                if not user:
                    logger.error("Failed to create user")
                    return JSONResponse(
                        status_code=500,
                        content={'success': False, 'error': 'Failed to create user'}
                    )

                user_id = user['id']
                logger.info(f"✅ New Telegram user created: {user_id} (@{username})")

        # Создаем JWT токен
        token = create_jwt_token(user_id, f"tg_{telegram_id}@pulsetraders.local")

        logger.info(f"✅ Telegram login success: {telegram_id} (ID: {user_id})")

        return JSONResponse({
            'success': True,
            'user_id': user_id,
            'token': token,
            'message': '✅ Добро пожаловать!'
        })

    except Exception as e:
        logger.error(f"❌ Telegram OAuth error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': f'Error: {str(e)}'}
        )


@router.get("/me")
async def get_me(request: Request):
    """Получить текущего пользователя"""
    authorization = request.headers.get('Authorization')

    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        scheme, token = authorization.split()
        payload = verify_jwt_token(token)

        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = int(payload.get('sub'))
        db = request.state.db

        if not db or not db.is_connected:
            raise HTTPException(status_code=503, detail="Database unavailable")

        async with db.pool.acquire() as conn:
            user = await conn.fetchrow("SELECT id, email, first_name, avatar_url FROM users WHERE id = $1", user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return JSONResponse({
            'success': True,
            'data': {
                'id': user['id'],
                'email': user['email'],
                'username': user['first_name'],
                'avatar_url': user['avatar_url']
            }
        })

    except Exception as e:
        logger.error(f"Error in /me: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth")
async def auth_page():
    """Страница аутентификации - для обработки редиректов"""
    html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Авторизация - Pulse Traders</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            h1 { color: #333; margin-top: 0; }
            p { color: #666; }
            .error { color: #c33; background: #fee; padding: 12px; border-radius: 8px; margin-top: 20px; }
            .success { color: #3c3; background: #efe; padding: 12px; border-radius: 8px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="spinner"></div>
            <h1>Авторизация...</h1>
            <p id="message">Пожалуйста, подождите</p>
            <div id="status"></div>
        </div>

        <script>
            function handleAuthRedirect() {
                const params = new URLSearchParams(window.location.search);
                const token = params.get('token');
                const userId = params.get('user_id');
                const error = params.get('error');

                const messageEl = document.getElementById('message');
                const statusEl = document.getElementById('status');

                if (error) {
                    console.error('❌ Ошибка аутентификации:', decodeURIComponent(error));
                    messageEl.textContent = 'Ошибка авторизации';
                    statusEl.innerHTML = `<div class="error"><strong>Ошибка:</strong> ${decodeURIComponent(error)}</div>`;
                    setTimeout(() => { window.location.href = '/auth.html'; }, 3000);
                    return;
                }

                if (token && userId) {
                    console.log('✅ Успешная аутентификация');
                    localStorage.setItem('auth_token', token);
                    localStorage.setItem('user_id', userId);
                    sessionStorage.setItem('auth_token', token);
                    
                    messageEl.textContent = 'Авторизация успешна!';
                    statusEl.innerHTML = '<div class="success">✅ Вы успешно вошли. Переводим на панель управления...</div>';
                    setTimeout(() => { window.location.href = '/dashboard'; }, 1500);
                    return;
                }

                messageEl.textContent = 'Нет данных авторизации';
                statusEl.innerHTML = '<div class="error">Параметры авторизации не найдены</div>';
                setTimeout(() => { window.location.href = '/auth.html'; }, 2000);
            }

            window.addEventListener('DOMContentLoaded', handleAuthRedirect);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/terms")
async def get_terms():
    """Получить условия обслуживания"""
    return FileResponse("static/auth-terms.html", media_type="text/html")


@router.get("/privacy")
async def get_privacy():
    """Получить политику конфиденциальности"""
    return FileResponse("static/auth-privacy.html", media_type="text/html")