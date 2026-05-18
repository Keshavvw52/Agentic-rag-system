"""Configuration and stats endpoints."""

from fastapi import APIRouter, Depends
from app.auth.jwt_handler import get_current_user
from app.schemas.schemas import RoutingConfig, ThresholdConfig, StatsResponse
from app.db.mongodb import get_database

# Config router
router = APIRouter()


@router.get("/routing")
async def get_routing_config(current_user: dict = Depends(get_current_user)):
    db = get_database()
    user = await db.users.find_one({"_id": __import__("bson").ObjectId(current_user["id"])})
    routing = user.get("settings", {}).get("routing", {})
    return routing


@router.put("/routing")
async def update_routing_config(
    config: RoutingConfig,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    await db.users.update_one(
        {"_id": __import__("bson").ObjectId(current_user["id"])},
        {"$set": {"settings.routing": config.model_dump()}},
    )
    return {"message": "Routing configuration updated", "config": config.model_dump()}


@router.put("/thresholds")
async def update_thresholds(
    config: ThresholdConfig,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    await db.users.update_one(
        {"_id": __import__("bson").ObjectId(current_user["id"])},
        {"$set": {"settings.thresholds": config.model_dump()}},
    )
    return {"message": "Threshold configuration updated", "config": config.model_dump()}