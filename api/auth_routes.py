"""
Authentication API routes для email/пароль, Google OAuth и Telegram
"""

import logging
import os
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

import jwt
from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, EmailStr
import bcrypt
from google.auth.transport import requests
from google.oauth2 import id_token

from config import ADMIN_IDS, SECRET_KEY, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SUPPORT_EMAIL

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

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

# ==================== EMAIL СЕРВИС ====================

async def send_email(to_email: str, subject: str, html_content: str):
    """Отправить письмо"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = to_email

        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # Отправляем в фоне
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
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
    """Хешировать пароль с солью"""
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

def create_jwt_token(user_id: int, email: str, expires_hours: int = 720) -> str:
    """Создать JWT токен"""
    payload = {
        'sub': str(user_id),
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=expires_hours)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_jwt_token(token: str) -> dict:
    """Проверить JWT токен"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
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
        # Удаляем старые коды
        await db.execute("""
            DELETE FROM email_verifications 
            WHERE email = %s
        """, email)

        # Сохраняем новый
        await db.execute("""
            INSERT INTO email_verifications (email, code, expires_at)
            VALUES (%s, %s, %s)
        """, email, code, datetime.utcnow() + timedelta(minutes=15))

        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения кода: {e}")
        return False

async def verify_email_code(db, email: str, code: str) -> bool:
    """Проверить код верификации"""
    try:
        result = await db.fetch_one("""
            SELECT * FROM email_verifications 
            WHERE email = %s AND code = %s AND expires_at > %s
        """, email, code, datetime.utcnow())

        if result:
            # Удаляем код
            await db.execute("DELETE FROM email_verifications WHERE email = %s", email)
            return True
        return False
    except Exception as e:
        logger.error(f"Ошибка проверки кода: {e}")
        return False

# ==================== ENDPOINTS ====================

@router.post("/register")
async def register(request: RegisterRequest, db=None):
    """Регистрация с email и паролем"""
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Проверяем, что email не существует
        existing_user = await db.fetch_one(
            "SELECT id FROM users WHERE email = %s",
            request.email
        )

        if existing_user:
            return JSONResponse(
                status_code=400,
                content={'success': False, 'error': 'Этот email уже зарегистрирован'}
            )

        # Хешируем пароль
        hashed_password = hash_password(request.password)

        # Создаем пользователя
        user = await db.execute("""
            INSERT INTO users (email, password_hash, first_name, is_active)
            VALUES (%s, %s, %s, FALSE)
            RETURNING id, email
        """, request.email, hashed_password, request.name)

        if not user:
            raise HTTPException(status_code=400, detail="Failed to create user")

        user_id = user[0][0]

        # Генерируем и сохраняем код верификации
        code = generate_verification_code()
        await save_verification_code(db, request.email, code)

        # Отправляем письмо с кодом
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Подтверждение email</h2>
                <p>Ваш код подтверждения:</p>
                <h1 style="color: #667eea; letter-spacing: 5px;">{code}</h1>
                <p>Код действителен 15 минут.</p>
                <hr>
                <p style="color: #999; font-size: 12px;">Pulse Traders © 2025</p>
            </body>
        </html>
        """

        await send_email(
            request.email,
            "Подтверждение email - Pulse Traders",
            html_content
        )

        logger.info(f"✅ Пользователь создан: {request.email}")

        return JSONResponse({
            'success': True,
            'user_id': user_id,
            'email': request.email,
            'message': 'Проверьте вашу почту'
        })

    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db=None):
    """Подтвердить email кодом"""
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Проверяем код
        is_valid = await verify_email_code(db, request.email, request.code)

        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={'success': False, 'error': 'Неверный или истекший код'}
            )

        # Активируем пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE email = %s",
            request.email
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user[0]

        await db.execute(
            "UPDATE users SET is_active = TRUE, verified_at = %s WHERE id = %s",
            datetime.utcnow(),
            user_id
        )

        # Создаем JWT токен
        token = create_jwt_token(user_id, request.email)

        logger.info(f"✅ Email подтвержден: {request.email}")

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
async def login(request: LoginRequest, db=None):
    """Вход по email и пароль"""
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Ищем пользователя
        user = await db.fetch_one(
            "SELECT id, password_hash, is_active FROM users WHERE email = %s",
            request.email
        )

        if not user:
            return JSONResponse(
                status_code=401,
                content={'success': False, 'error': 'Email или пароль неверны'}
            )

        user_id, password_hash, is_active = user

        # Проверяем пароль
        if not verify_password(request.password, password_hash):
            return JSONResponse(
                status_code=401,
                content={'success': False, 'error': 'Email или пароль неверны'}
            )

        # Проверяем активность
        if not is_active:
            return JSONResponse(
                status_code=403,
                content={'success': False, 'error': 'Email не подтвержден'}
            )

        # Создаем токен
        token = create_jwt_token(user_id, request.email)

        # Обновляем last_active
        await db.execute(
            "UPDATE users SET last_active = %s WHERE id = %s",
            datetime.utcnow(),
            user_id
        )

        logger.info(f"✅ Успешный вход: {request.email}")

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
async def google_login(request: GoogleTokenRequest, db=None):
    """Вход через Google OAuth"""
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Проверяем Google токен
        idinfo = id_token.verify_oauth2_token(
            request.token,
            requests.Request(),
            os.getenv('GOOGLE_CLIENT_ID', '154411658303-lhc5cfoj9deb954ivbfd3g9k7ijlh5ob.apps.googleusercontent.com')
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(status_code=400, detail="Invalid token")

        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        google_id = idinfo['sub']

        # Ищем или создаем пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE email = %s OR google_id = %s",
            email, google_id
        )

        if user:
            user_id = user[0]
        else:
            # Создаем нового пользователя
            result = await db.execute("""
                INSERT INTO users (email, first_name, google_id, is_active, verified_at)
                VALUES (%s, %s, %s, TRUE, %s)
                RETURNING id
            """, email, name, google_id, datetime.utcnow())

            user_id = result[0][0]

        # Создаем токен
        token = create_jwt_token(user_id, email)

        # Обновляем last_active
        await db.execute(
            "UPDATE users SET last_active = %s, google_id = %s WHERE id = %s",
            datetime.utcnow(),
            google_id,
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
        logger.error(f"Ошибка Google OAuth: {e}")
        return JSONResponse(
            status_code=400,
            content={'success': False, 'error': 'Ошибка аутентификации Google'}
        )


@router.get("/telegram")
async def telegram_auth(request, redirect: str = "/", register: bool = False, db=None):
    """OAuth через Telegram"""
    try:
        # Получаем данные из Telegram
        telegram_id = request.query_params.get('id')
        first_name = request.query_params.get('first_name', '')
        last_name = request.query_params.get('last_name', '')
        username = request.query_params.get('username', '')

        if not telegram_id:
            raise HTTPException(status_code=400, detail="Invalid Telegram data")

        if not db or not db.is_connected:
            raise HTTPException(status_code=503, detail="Database unavailable")

        # Ищем или создаем пользователя
        user = await db.fetch_one(
            "SELECT id, is_active FROM users WHERE telegram_id = %s",
            int(telegram_id)
        )

        if user:
            user_id, is_active = user
        else:
            # Создаем нового пользователя
            email = f"tg_{telegram_id}@pulsetraders.local"
            result = await db.execute("""
                INSERT INTO users (telegram_id, first_name, last_name, username, email, is_active, verified_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                RETURNING id
            """, int(telegram_id), first_name, last_name, username, email, datetime.utcnow())

            user_id = result[0][0]

        # Создаем токен
        fake_email = f"tg_{telegram_id}@pulsetraders.local"
        token = create_jwt_token(user_id, fake_email)

        # Обновляем last_active
        await db.execute(
            "UPDATE users SET last_active = %s WHERE id = %s",
            datetime.utcnow(),
            user_id
        )

        logger.info(f"✅ Вход через Telegram: {username or telegram_id}")

        # Перенаправляем с токеном
        return JSONResponse({
            'success': True,
            'user_id': user_id,
            'token': token,
            'redirect': redirect
        })

    except Exception as e:
        logger.error(f"Ошибка Telegram OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout(authorization: str = Header(None)):
    """Выход пользователя"""
    # JWT не хранит сессии, поэтому просто удаляем с клиента
    return JSONResponse({
        'success': True,
        'message': 'Вы вышли из аккаунта'
    })


@router.post("/resend-code")
async def resend_verification_code(email: EmailStr, db=None):
    """Отправить код еще раз"""
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Проверяем, что пользователь существует и не активирован
        user = await db.fetch_one(
            "SELECT id FROM users WHERE email = %s AND is_active = FALSE",
            email
        )

        if not user:
            return JSONResponse(
                status_code=400,
                content={'success': False, 'error': 'Пользователь не найден или уже активирован'}
            )

        # Генерируем новый код
        code = generate_verification_code()
        await save_verification_code(db, email, code)

        # Отправляем письмо
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Новый код подтверждения</h2>
                <p>Ваш новый код верификации:</p>
                <h1 style="color: #667eea; letter-spacing: 5px;">{code}</h1>
                <p>Код действителен 15 минут.</p>
                <hr>
                <p style="color: #999; font-size: 12px;">Pulse Traders © 2025</p>
            </body>
        </html>
        """

        await send_email(
            email,
            "Новый код подтверждения - Pulse Traders",
            html_content
        )

        return JSONResponse({
            'success': True,
            'message': 'Код отправлен еще раз'
        })

    except Exception as e:
        logger.error(f"Ошибка повторной отправки: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/terms")
async def get_terms():
    """Получить условия обслуживания"""
    try:
        return FileResponse("static/auth-terms.html", media_type="text/html")
    except:
        return FileResponse("api/terms.html", media_type="text/html")


@router.get("/privacy")
async def get_privacy():
    """Получить политику конфиденциальности"""
    try:
        return FileResponse("static/auth-privacy.html", media_type="text/html")
    except:
        return FileResponse("api/privacy.html", media_type="text/html")