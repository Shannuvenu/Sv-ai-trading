from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime


@dataclass
class BrokerHolding:
    symbol: str
    quantity: int
    average_price: Decimal


@dataclass
class BrokerOrder:
    symbol: str
    side: str
    quantity: int
    price: Decimal
    status: str


class BrokerAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool:
        ...

    @abstractmethod
    def get_holdings(self) -> list[BrokerHolding]:
        ...

    @abstractmethod
    def get_ltp(self, symbol: str) -> Decimal | None:
        ...

    def place_order(
        self, symbol: str, side: str, quantity: int, price: Decimal
    ) -> BrokerOrder:
        raise NotImplementedError(
            "Live order execution is disabled in this version. "
            "This is a paper-trading platform only."
        )
