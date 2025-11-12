"""
Admin API endpoints для админ-панели
Все endpoints требуют admin_key в headers
"""

from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def verify_admin(db, user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    if not db or not db.is_connected:
        return False

    user = await db.get_user_by_id(user_id)
    return user and user.get('is_admin', False)


# ==================== СТАТИСТИКА ====================

@router.get("/stats")
async def get_admin_stats(x_user_id: int = Header(None), db=None):
    """Получить статистику для админ-панели"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not await verify_admin(db, x_user_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        stats = await db.get_admin_stats()
        return JSONResponse({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@router.get("/users")
async def get_all_users(
    x_user_id: int = Header(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db=None
):
    """Получить список всех пользователей"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not await verify_admin(db, x_user_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        users = await db.get_all_users(limit, offset)
        total = await db.get_users_count()

        return JSONResponse({
            'success': True,
            'data': users,
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
    x_user_id: int = Header(None),
    db=None
):
    """Получить информацию о пользователе"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not await verify_admin(db, x_user_id):
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
            'data': {
                'user': user,
                'subscription': subscription,
                'prediction_limits': limits,
                'recent_predictions': predictions
            }
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_admin: bool = None,
    is_banned: bool = None,
    x_user_id: int = Header(None),
    db=None
):
    """Обновить статус пользователя"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not await verify_admin(db, x_user_id):
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
    x_user_id: int = Header(None),
    db=None
):
    """Получить все тарифы подписок"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not await verify_admin(db, x_user_id):
        raise HTTPException(status_code=403, detail="Not admin")

    try:
        tiers = await db.get_all_subscription_tiers()
        return JSONResponse({
            'success': True,
            'data': tiers
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tiers")
async def create_subscription_tier(
    request_data: dict,
    x_user_id: int = Header(None),
    db=None
):
    """Создать новый тариф"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not await verify_admin(db, x_user_id):
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
            'data': tier
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tiers/{tier_id}")
async def update_subscription_tier(
    tier_id: int,
    request_data: dict,
    x_user_id: int = Header(None),
    db=None
):
    """Обновить тариф"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not await verify_admin(db, x_user_id):
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
    tier_id: int,
    months: int = 1,
    x_user_id: int = Header(None),
    db=None
):
    """Установить/обновить подписку пользователя"""
    if not x_user_id or not db:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not await verify_admin(db, x_user_id):
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