"""
User API endpoints для личного кабинета
"""

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


# ==================== ПРОФИЛЬ ====================

@router.get("/profile")
async def get_user_profile(x_user_id: int = Header(None), db=None):
    """Получить профиль пользователя"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user = await db.get_user_by_id(x_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        subscription = await db.get_user_subscription(x_user_id)
        limits = await db.check_prediction_limit(x_user_id)

        return JSONResponse({
            'success': True,
            'data': {
                'user': user,
                'subscription': subscription,
                'prediction_limits': limits
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ЛИМИТЫ ====================

@router.get("/limits")
async def check_prediction_limits(x_user_id: int = Header(None), db=None):
    """Проверить лимиты прогнозов"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        limits = await db.check_prediction_limit(x_user_id)
        if not limits:
            raise HTTPException(status_code=404, detail="Limits not found")

        # Определяем статус лимита
        daily_remaining = limits['predictions_limit_daily'] - limits['predictions_used_today']
        monthly_remaining = limits['predictions_limit_monthly'] - limits['predictions_used_month']

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
                'needs_premium': daily_remaining <= 0 and not limits['is_premium']
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ПОДПИСКА ====================

@router.get("/subscription")
async def get_subscription(x_user_id: int = Header(None), db=None):
    """Получить информацию о подписке"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        subscription = await db.get_user_subscription(x_user_id)

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
async def get_available_tiers(x_user_id: int = Header(None), db=None):
    """Получить доступные тарифы подписок"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

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
        x_user_id: int = Header(None),
        limit: int = Query(50, ge=1, le=500),
        db=None
):
    """Получить историю прогнозов пользователя"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        history = await db.get_user_prediction_history(x_user_id, limit)
        return JSONResponse({
            'success': True,
            'data': history
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== СОХРАНЕНИЕ ПРОГНОЗА ====================

@router.post("/predictions/save")
async def save_prediction(
        request_data: dict,
        x_user_id: int = Header(None),
        db=None
):
    """Сохранить прогноз"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Проверяем лимит
        limits = await db.check_prediction_limit(x_user_id)
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
            user_id=x_user_id,
            symbol=request_data.get('symbol'),
            predicted_price=float(request_data.get('predicted_price', 0)),
            confidence=float(request_data.get('confidence', 0)),
            signal=request_data.get('signal', 'HOLD')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to save prediction")

        # Получаем обновленные лимиты
        updated_limits = await db.check_prediction_limit(x_user_id)

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