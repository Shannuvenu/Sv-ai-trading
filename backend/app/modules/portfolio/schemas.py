from pydantic import BaseModel, field_validator
from datetime import datetime
from decimal import Decimal


class PortfolioCreate(BaseModel):
    name: str
    initial_cash: Decimal

    @field_validator("initial_cash")
    @classmethod
    def positive_cash(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Initial cash must be positive")
        return v


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    initial_cash: Decimal
    cash_balance: Decimal
    is_paper: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HoldingResponse(BaseModel):
    id: int
    symbol: str
    quantity: int
    average_price: Decimal
    current_price: Decimal | None = None
    cost_basis: Decimal | None = None
    market_value: Decimal | None = None
    unrealised_pnl: Decimal | None = None
    unrealised_pnl_pct: Decimal | None = None

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: int
    price: Decimal
    total_value: Decimal
    executed_at: datetime

    model_config = {"from_attributes": True}


class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    price: Decimal

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("price")
    @classmethod
    def positive_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class PortfolioSummary(BaseModel):
    portfolio: PortfolioResponse
    cash_balance: Decimal
    invested_cost: Decimal
    market_value: Decimal
    equity: Decimal
    unrealised_pnl: Decimal
    unrealised_pnl_pct: Decimal
    holdings: list[HoldingResponse]
    recent_transactions: list[TransactionResponse]
