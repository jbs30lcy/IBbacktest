from dataclasses import dataclass
from typing import Any, Callable, TypeAlias


@dataclass(frozen=True)
class CompoundMode:
    ratio: float
    is_realtime: bool


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
    interval: int = 1
    wait_t: int = 0
    alter_t: float = 0
    buy_amount: float = 0
    realized_profit: float = 0
    peak_profit: float = 0
    pending_profit: float = 0


@dataclass
class Constants:
    star_reference: float
    sell_reference: float
    division_count: int
    compound: CompoundMode


@dataclass(frozen=True)
class TEffect:
    multiplier: float = 1
    increment: float = 0


@dataclass
class Prices:
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    previous_close: float | None = None
    previous_five_close_average: float | None = None


PrepareMethod: TypeAlias = Callable[[State, Constants], None]
OrderMethod: TypeAlias = Callable[
    [State, Constants, Prices],
    list[dict[str, Any]],
]
SettleMethod: TypeAlias = Callable[
    [State, list[dict[str, Any]], Constants, Prices],
    None,
]


@dataclass(frozen=True)
class Strategy:
    key: str
    name: str
    prepare: PrepareMethod
    create_orders: OrderMethod
    settle: SettleMethod


TradeMethod: TypeAlias = Strategy
