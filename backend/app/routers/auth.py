from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status

from app.schemas.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.auth.jwt_handler import hash_password, verify_password, create_access_token, get_current_user
from app.db.mongodb import get_database

router = APIRouter() 

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    db = get_database()

    # Check for existing user
    existing = await db.users.find_one({
        "$or": [{"email": user_data.email}, {"username": user_data.username}]
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )

    # Create user document
    user_doc = {
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hash_password(user_data.password),
        "created_at": datetime.now(timezone.utc),
        "settings": {
            "routing": {
                "factual_strategy": "HYBRID_RERANK",
                "analytical_strategy": "MULTI_QUERY",
                "summarization_strategy": "SECTION_BASED",
                "conversational_strategy": "CONVERSATIONAL",
                "routing_confidence_min": 0.70,
            },
            "thresholds": {
                "hallucination_threshold": 0.20,
                "max_retries": 3,
                "max_iterations": 3,
                "enable_web_search": True,
                "enable_llm_knowledge": True,
            },
        },
    }

    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    token = create_access_token(user_id, user_data.email)

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=user_doc["created_at"],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    db = get_database()
    user = await db.users.find_one({"email": credentials.email})

    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user_id = str(user["_id"])
    token = create_access_token(user_id, user["email"])

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            username=user["username"],
            email=user["email"],
            full_name=user.get("full_name"),
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        created_at=current_user["created_at"],
    )