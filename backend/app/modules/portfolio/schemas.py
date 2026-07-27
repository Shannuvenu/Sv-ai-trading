from pydantic import BaseModel, field_validator, field_serializer, ConfigDict
from datetime import datetime
from decimal import Decimal


class PortfolioCreate(BaseModel):
    name: str
    initial_cash: float

    @field_validator("initial_cash")
    @classmethod
    def positive_cash(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Initial cash must be positive")
        return v


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    initial_cash: float
    cash_balance: float
    is_paper: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("initial_cash", "cash_balance")
    def serialize_dec(self, v: Decimal) -> float:
        return round(float(v), 2)

    model_config = ConfigDict(from_attributes=True)


class HoldingResponse(BaseModel):
    id: int
    symbol: str
    quantity: int
    average_price: float
    current_price: float | None = None
    cost_basis: float | None = None
    market_value: float | None = None
    unrealised_pnl: float | None = None
    unrealised_pnl_pct: float | None = None

    @field_serializer("average_price", "current_price", "cost_basis", "market_value", "unrealised_pnl", "unrealised_pnl_pct")
    def serialize_dec(self, v: Decimal | None) -> float | None:
        return round(float(v), 2) if v is not None else None

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: int
    price: float
    total_value: float
    executed_at: datetime

    @field_serializer("price", "total_value")
    def serialize_dec(self, v: Decimal) -> float:
        return round(float(v), 2)

    model_config = ConfigDict(from_attributes=True)


class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    price: float

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("price")
    @classmethod
    def positive_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class PortfolioSummary(BaseModel):
    portfolio: PortfolioResponse
    cash_balance: float
    invested_cost: float
    market_value: float
    equity: float
    unrealised_pnl: float
    unrealised_pnl_pct: float
    holdings: list[HoldingResponse]
    recent_transactions: list[TransactionResponse]
