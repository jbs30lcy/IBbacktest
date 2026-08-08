from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeAlias


class CompoundMode(Enum):
    NO = (0.0, True)
    HALF_REALTIME = (0.5, True)
    HALF_ROUND = (0.5, False)
    FULL_REALTIME = (1.0, True)
    FULL_ROUND = (1.0, False)

    def __init__(self, ratio: float, is_realtime: bool):
        self.ratio = ratio
        self.is_realtime = is_realtime


@dataclass
class State:
    profit: float
    initial_capital: float
    capital: float
    cash: float
    quantity: int
    average_price: float
    t: float
    buy_unit: int
    mode: str
    alter_t: float = 0
    buy_amount: float = 0
    realized_profit: float = 0
    peak_profit: float = 0
    pending_profit: float = 0


@dataclass
class Constants:
    star_reference: float
    sell_threshold: float
    division_count: int
    interval: int
    compound: CompoundMode


@dataclass
class Prices:
    open: float
    high: float
    low: float
    close: float
    adj_close: float


PrepareMethod: TypeAlias = Callable[[State, Constants], None]
OrderMethod: TypeAlias = Callable[..., list[dict[str, Any]]]
SettleMethod: TypeAlias = Callable[[State, list[dict[str, Any]], Constants], None]


@dataclass(frozen=True)
class Strategy:
    name: str
    defaults: Constants
    prepare: PrepareMethod
    create_orders: OrderMethod
    settle: SettleMethod


TradeMethod: TypeAlias = Strategy
