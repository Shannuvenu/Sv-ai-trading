from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import math


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class BacktestResult:
    total_return: float
    total_return_pct: float
    num_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown_pct: float
    initial_capital: float
    final_equity: float
    equity_curve: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_return": round(self.total_return, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "num_trades": self.num_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4) if self.sharpe_ratio is not None else None,
            "sortino_ratio": round(self.sortino_ratio, 4) if self.sortino_ratio is not None else None,
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "initial_capital": self.initial_capital,
            "final_equity": round(self.final_equity, 2),
            "equity_curve": self.equity_curve,
            "trades": self.trades,
        }


def _compute_returns(equity: list[float]) -> list[float]:
    returns = []
    for i in range(1, len(equity)):
        if equity[i - 1] > 0:
            returns.append((equity[i] - equity[i - 1]) / equity[i - 1])
        else:
            returns.append(0.0)
    return returns


def _sharpe_ratio(returns: list[float], risk_free: float = 0.0) -> float | None:
    if len(returns) < 2:
        return None
    import numpy as np
    mean_ret = np.mean(returns) - risk_free
    std_ret = np.std(returns, ddof=1)
    if std_ret == 0:
        return 0.0
    return float((mean_ret / std_ret) * math.sqrt(252))


def _sortino_ratio(returns: list[float], risk_free: float = 0.0) -> float | None:
    if len(returns) < 2:
        return None
    import numpy as np
    mean_ret = np.mean(returns) - risk_free
    downside = [r - risk_free for r in returns if r < risk_free]
    if not downside:
        return 0.0
    downside_std = np.std(downside, ddof=1)
    if downside_std == 0:
        return 0.0
    return float((mean_ret / downside_std) * math.sqrt(252))
