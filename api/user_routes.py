"""
User API endpoints для личного кабинета
"""

from fastapi import APIRouter, HTTPException, Header, Query, Request, File, UploadFile
from fastapi.responses import JSONResponse
import logging
import jwt
from datetime import datetime
from pathlib import Path
import shutil
from config import SECRET_KEY, JWT_ALGORITHM

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


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


# ==================== JWT AUTHENTICATION ====================

def verify_token(authorization: str = Header(None)) -> int:
    """
    Проверить JWT токен и вернуть user_id
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


# ==================== ПРОФИЛЬ ====================

@router.get("/profile")
async def get_user_profile(request: Request, authorization: str = Header(None)):
    """Получить профиль пользователя"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        user = await db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        subscription = await db.get_user_subscription(user_id)
        limits = await db.check_prediction_limit(user_id)

        # Получаем общее количество прогнозов пользователя
        async with db.pool.acquire() as conn:
            total_predictions_result = await conn.fetchval(
                "SELECT COUNT(*) FROM prediction_history WHERE user_id = $1",
                user_id
            )
            total_predictions = total_predictions_result or 0

        # Добавляем total_predictions к данным пользователя
        user['total_predictions'] = total_predictions

        return JSONResponse({
            'success': True,
            'data': {
                'user': serialize_datetime(user),
                'subscription': serialize_datetime(subscription),
                'prediction_limits': serialize_datetime(limits)
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ЛИМИТЫ ====================

@router.get("/limits")
async def check_prediction_limits(request: Request, authorization: str = Header(None)):
    """Проверить лимиты прогнозов"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        limits = await db.check_prediction_limit(user_id)
        if not limits:
            raise HTTPException(status_code=404, detail="Limits not found")

        # Определяем статус лимита
        daily_remaining = limits['predictions_limit_daily'] - limits['predictions_used_today']
        monthly_remaining = limits['predictions_limit_monthly'] - limits['predictions_used_month']

        # Если месячный лимит исчерпан, дневной тоже становится 0
        if monthly_remaining <= 0:
            daily_remaining = 0

        can_predict = daily_remaining > 0 and monthly_remaining > 0

        return JSONResponse({
            'success': True,
            'data': {
                'daily': {
                    'used': limits['predictions_used_today'],
                    'limit': limits['predictions_limit_daily'],
                    'remaining': max(0, daily_remaining)
                },
                'monthly': {
                    'used': limits['predictions_used_month'],
                    'limit': limits['predictions_limit_monthly'],
                    'remaining': max(0, monthly_remaining)
                },
                'is_premium': limits['is_premium'],
                'can_predict': can_predict,
                'needs_premium': (daily_remaining <= 0 or monthly_remaining <= 0) and not limits['is_premium']
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ПОДПИСКА ====================

@router.get("/subscription")
async def get_subscription(request: Request, authorization: str = Header(None)):
    """Получить информацию о подписке"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        subscription = await db.get_user_subscription(user_id)

        # Если подписки нет, отправляем свободный тариф
        if not subscription:
            return JSONResponse({
                'success': True,
                'data': {
                    'status': 'free',
                    'tier': {
                        'display_name': 'Бесплатный',
                        'price': 0,
                        'monthly_predictions': 30,
                        'daily_predictions': 5
                    },
                    'message': 'У вас бесплатная подписка'
                }
            })

        # Проверяем, не истекла ли подписка
        from datetime import datetime
        if subscription['expires_at'] and subscription['expires_at'] < datetime.now():
            return JSONResponse({
                'success': True,
                'data': {
                    'status': 'expired',
                    'subscription': subscription,
                    'message': 'Ваша подписка истекла'
                }
            })

        return JSONResponse({
            'success': True,
            'data': {
                'status': 'active',
                'subscription': subscription
            }
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscription/available-tiers")
async def get_available_tiers(request: Request, authorization: str = Header(None)):
    """Получить доступные тарифы подписок"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        tiers = await db.get_all_subscription_tiers()
        return JSONResponse({
            'success': True,
            'data': tiers
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ИСТОРИЯ ПРОГНОЗОВ ====================

@router.get("/predictions/history")
async def get_prediction_history(
        request: Request,
        authorization: str = Header(None),
        limit: int = Query(50, ge=1, le=500)
):
    """Получить историю прогнозов пользователя"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        history = await db.get_user_prediction_history(user_id, limit)
        # Сериализуем данные для корректной JSON конвертации
        serialized_history = serialize_datetime(history)
        return JSONResponse({
            'success': True,
            'data': serialized_history
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== СОХРАНЕНИЕ ПРОГНОЗА ====================

@router.post("/predictions/save")
async def save_prediction(
        request: Request,
        request_data: dict,
        authorization: str = Header(None)
):
    """Сохранить прогноз"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Проверяем лимит
        limits = await db.check_prediction_limit(user_id)
        if not limits:
            raise HTTPException(status_code=404, detail="Limits not found")

        daily_remaining = limits['predictions_limit_daily'] - limits['predictions_used_today']

        if daily_remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={
                    'success': False,
                    'error': 'Daily limit reached',
                    'message': 'Вы исчерпали дневной лимит прогнозов. Попробуйте завтра или купите подписку.'
                }
            )

        # Сохраняем прогноз
        success = await db.save_prediction(
            user_id=user_id,
            symbol=request_data.get('symbol'),
            predicted_price=float(request_data.get('predicted_price', 0)),
            confidence=float(request_data.get('confidence', 0)),
            signal=request_data.get('signal', 'HOLD')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to save prediction")

        # Получаем обновленные лимиты
        updated_limits = await db.check_prediction_limit(user_id)

        return JSONResponse({
            'success': True,
            'message': 'Prediction saved successfully',
            'limits': {
                'daily': {
                    'used': updated_limits['predictions_used_today'],
                    'remaining': max(0, updated_limits['predictions_limit_daily'] - updated_limits[
                        'predictions_used_today'])
                },
                'monthly': {
                    'used': updated_limits['predictions_used_month'],
                    'remaining': max(0, updated_limits['predictions_limit_monthly'] - updated_limits[
                        'predictions_used_month'])
                }
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ЗАГРУЗКА АВАТАРА ====================

@router.post("/upload-avatar")
async def upload_avatar(
        request: Request,
        avatar: UploadFile = File(...),
        authorization: str = Header(None)
):
    """Загрузка фото профиля"""
    user_id = verify_token(authorization)
    db = request.state.db

    if not db or not db.is_connected:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Проверка размера файла (макс 20MB)
        max_size = 20 * 1024 * 1024  # 20MB
        content = await avatar.read()
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 20MB")

        # Проверка типа файла
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if avatar.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed")

        # Создаем директорию если не существует
        avatars_dir = Path("static/avatars")
        avatars_dir.mkdir(exist_ok=True)

        # Генерируем имя файла
        file_extension = avatar.filename.split('.')[-1] if '.' in avatar.filename else 'jpg'
        filename = f"user_{user_id}.{file_extension}"
        filepath = avatars_dir / filename

        # Сохраняем файл
        with open(filepath, 'wb') as f:
            f.write(content)

        # Обновляем в базе данных
        avatar_url = f"/static/avatars/{filename}"
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET avatar_url = $1 WHERE id = $2",
                avatar_url,
                user_id
            )

        logger.info(f"✅ Avatar uploaded for user {user_id}: {avatar_url}")

        return JSONResponse({
            'success': True,
            'avatar_url': avatar_url,
            'message': 'Avatar uploaded successfully'
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))
