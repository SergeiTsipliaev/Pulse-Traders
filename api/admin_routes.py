"""
Admin API endpoints для админ-панели
Все endpoints требуют JWT токен с правами администратора
"""

from fastapi import APIRouter, HTTPException, Query, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import jwt
from datetime import datetime, timedelta
from config import SECRET_KEY, JWT_ALGORITHM, ADMIN_USERNAME, ADMIN_PASSWORD

logger = logging.getLogger(__name__)


def serialize_datetime(obj):
    """Конвертировать datetime и Decimal объекты для JSON сериализации"""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: serialize_datetime(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Добавляем поддержку Decimal
    if isinstance(obj, (int, float)):
        return obj
    # Проверяем Decimal (избегаем импорта)
    if type(obj).__name__ == 'Decimal':
        return float(obj)
    return obj


class AdminLoginRequest(BaseModel):
    username: str
    password: str

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==================== ADMIN LOGIN ====================

@router.post("/login")
async def admin_login(body: AdminLoginRequest):
    """Вход в админ-панель через credentials из .env"""
    try:
        # Проверяем логин и пароль из .env
        if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
            logger.warning(f"❌ Failed admin login attempt: {body.username}")
            return JSONResponse(
                status_code=401,
                content={'success': False, 'error': 'Invalid credentials'}
            )

        # Создаем специальный токен для админа
        payload = {
            'sub': 'admin',
            'role': 'super_admin',
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

        logger.info(f"✅ Admin login successful: {body.username}")

        return JSONResponse({
            'success': True,
            'token': token,
            'username': body.username,
            'role': 'admin'
        })

    except Exception as e:
        logger.error(f"❌ Admin login error: {e}")
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': str(e)}
        )


def verify_token(authorization: str = Header(None)) -> int:
    """
    Проверить JWT токен и вернуть user_id
    Для super_admin возвращает -1
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        # Ожидаем формат: "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authorization header format")

        token = parts[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Проверяем, это super_admin или обычный пользователь
        if payload.get('role') == 'super_admin':
            return -1  # Специальный ID для super_admin

        user_id = int(payload.get('sub'))

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def verify_admin(db, user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    # Super admin (из .env) всегда имеет права
    if user_id == -1:
        return True

    if not db or not db.is_connected:
        return False

    user = await db.get_user_by_id(user_id)
    return user and user.get('is_admin', False)


# ==================== СТАТИСТИКА ====================

@router.get("/stats")
async def get_admin_stats(request: Request, authorization: str = Header(None)):
    """Получить статистику для админ-панели"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not await verify_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        stats = await db.get_admin_stats()
        return JSONResponse({
            'success': True,
            'data': serialize_datetime(stats)
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@router.get("/users")
async def get_all_users(
    request: Request,
    authorization: str = Header(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Получить список всех пользователей"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not await verify_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        users = await db.get_all_users(limit, offset)
        total = await db.get_users_count()

        return JSONResponse({
            'success': True,
            'data': serialize_datetime(users),
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    request: Request,
    authorization: str = Header(None)
):
    """Получить информацию о пользователе"""
    admin_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not await verify_admin(db, admin_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        user = await db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        subscription = await db.get_user_subscription(user_id)
        predictions = await db.get_user_prediction_history(user_id, limit=10)
        limits = await db.check_prediction_limit(user_id)

        return JSONResponse({
            'success': True,
            'data': serialize_datetime({
                'user': user,
                'subscription': subscription,
                'prediction_limits': limits,
                'recent_predictions': predictions
            })
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    request: Request,
    authorization: str = Header(None),
    is_admin: bool = None,
    is_banned: bool = None
):
    """Обновить статус пользователя"""
    admin_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not await verify_admin(db, admin_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        success = await db.update_user_status(user_id, is_admin, is_banned)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update user")

        return JSONResponse({
            'success': True,
            'message': 'User updated successfully'
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ТАРИФЫ ====================

@router.get("/tiers")
async def get_subscription_tiers(
    request: Request,
    authorization: str = Header(None)
):
    """Получить все тарифы подписок"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not await verify_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        tiers = await db.get_all_subscription_tiers()
        return JSONResponse({
            'success': True,
            'data': serialize_datetime(tiers)
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tiers")
async def create_subscription_tier(
    request: Request,
    request_data: dict,
    authorization: str = Header(None)
):
    """Создать новый тариф"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not await verify_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        tier = await db.create_subscription_tier(
            name=request_data.get('name'),
            display_name=request_data.get('display_name'),
            price=float(request_data.get('price', 0)),
            monthly_predictions=int(request_data.get('monthly_predictions', 30)),
            daily_predictions=int(request_data.get('daily_predictions', 5)),
            features=request_data.get('features', ''),
            description=request_data.get('description', ''),
            display_order=int(request_data.get('display_order', 0))
        )

        if not tier:
            raise HTTPException(status_code=400, detail="Failed to create tier")

        return JSONResponse({
            'success': True,
            'data': serialize_datetime(tier)
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tiers/{tier_id}")
async def update_subscription_tier(
    tier_id: int,
    request: Request,
    request_data: dict,
    authorization: str = Header(None)
):
    """Обновить тариф"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not await verify_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        success = await db.update_subscription_tier(tier_id, **request_data)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update tier")

        return JSONResponse({
            'success': True,
            'message': 'Tier updated successfully'
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ПОДПИСКИ ПОЛЬЗОВАТЕЛЕЙ ====================

@router.put("/users/{user_id}/subscription")
async def set_user_subscription(
    user_id: int,
    request: Request,
    authorization: str = Header(None),
    tier_id: int = None,
    months: int = 1
):
    """Установить/обновить подписку пользователя"""
    admin_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not await verify_admin(db, admin_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        success = await db.subscribe_user(user_id, tier_id, months)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to subscribe user")

        return JSONResponse({
            'success': True,
            'message': 'User subscription updated successfully'
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== УПРАВЛЕНИЕ ПРАВАМИ ====================

@router.post("/users/{user_id}/toggle-admin")
async def toggle_admin_role(
    user_id: int,
    request: Request,
    authorization: str = Header(None)
):
    """Переключить админские права пользователя (только для super_admin)"""
    # Проверяем что это super_admin (из .env)
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authorization header format")

        token = parts[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Проверяем что это super_admin
        if payload.get('role') != 'super_admin':
            raise HTTPException(status_code=403, detail="Only super admin can manage admin rights")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

    db = request.state.db
    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        async with db.pool.acquire() as conn:
            # Получаем текущий статус
            user = await conn.fetchrow("SELECT id, email, is_admin FROM users WHERE id = $1", user_id)

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Переключаем статус
            new_status = not user['is_admin']

            await conn.execute(
                "UPDATE users SET is_admin = $1 WHERE id = $2",
                new_status,
                user_id
            )

            action = 'granted' if new_status else 'revoked'
            logger.info(f"✅ Admin rights {action} for user {user_id} ({user['email']})")

            return JSONResponse({
                'success': True,
                'is_admin': new_status,
                'message': f"Admin rights {action} successfully"
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error toggling admin role: {e}")
        raise HTTPException(status_code=500, detail=str(e))
