"""Credits management router.

Allows users to check balance, purchase credits, and view transactions.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_current_user
from src.api.models.credit_transaction import CreditTransaction
from src.api.models.user import User

log = structlog.get_logger()
router = APIRouter(prefix="/credits", tags=["credits"])


class BalanceResponse(BaseModel):
    balance: float
    currency: str = "credits"


class PurchaseRequest(BaseModel):
    amount: float


class PurchaseResponse(BaseModel):
    new_balance: float
    amount_purchased: float
    transaction_id: str


class TransactionResponse(BaseModel):
    id: str
    amount: float
    transaction_type: str
    description: str
    created_at: str


class TransactionsListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    user: User = Depends(get_current_user),
) -> BalanceResponse:
    """Get the current user's credit balance."""
    return BalanceResponse(balance=user.credits_balance)


@router.post("/purchase", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
async def purchase_credits(
    req: PurchaseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PurchaseResponse:
    """Purchase credits (mock payment for now, adds credits immediately)."""
    if req.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive",
        )

    if req.amount > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum single purchase is 10,000 credits",
        )

    # Add credits atomically to prevent concurrent purchase race condition
    from sqlalchemy import update

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(credits_balance=User.credits_balance + req.amount)
    )

    # Record transaction
    transaction = CreditTransaction(
        user_id=user.id,
        amount=req.amount,
        transaction_type="purchase",
        description=f"Credit purchase: {req.amount} credits",
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(user)
    await db.refresh(transaction)

    log.info(
        "credits_purchased",
        user_id=str(user.id),
        amount=req.amount,
        new_balance=user.credits_balance,
    )
    return PurchaseResponse(
        new_balance=user.credits_balance,
        amount_purchased=req.amount,
        transaction_id=str(transaction.id),
    )


@router.get("/transactions", response_model=TransactionsListResponse)
async def get_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> TransactionsListResponse:
    """Get the user's credit transaction history."""
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()

    # Get total count
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count())
        .select_from(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
    )
    total = count_result.scalar_one()

    return TransactionsListResponse(
        transactions=[
            TransactionResponse(
                id=str(t.id),
                amount=t.amount,
                transaction_type=t.transaction_type,
                description=t.description,
                created_at=t.created_at.isoformat(),
            )
            for t in transactions
        ],
        total=total,
    )
