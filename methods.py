import math
from dataclasses import replace
from typing import Any, Dict, List

from models import CompoundMode, Constants, Prices, State, Strategy, TradeMethod


Order = Dict[str, Any]


def create_order(
    method: str,
    order_type: str,
    amount: float | None = None,
    quantity: int | None = None,
    price: float | None = None,
    event: str | None = None,
) -> Order:
    if amount is None and quantity is None:
        raise ValueError("amount 또는 quantity 중 하나를 정해야 합니다.")
    if amount is not None and quantity is not None:
        raise ValueError("amount 또는 quantity 중 하나만 정해야 합니다.")

    order: Order = {
        "method": method,
        "type": order_type,
        "by": "amount" if quantity is None else "quantity",
        "value": amount if quantity is None else quantity,
    }
    if price is not None:
        if price <= 0:
            raise ValueError("price는 0보다 커야 합니다.")
        order["price"] = price
    if event is not None:
        order["event"] = event
    return order


def LOCbuy(
    price: float,
    amount: float | None = None,
    quantity: int | None = None,
    event: str | None = None,
) -> Order:
    return create_order("LOC", "buy", amount, quantity, price, event)


def LOCsell(
    price: float,
    amount: float | None = None,
    quantity: int | None = None,
    event: str | None = None,
) -> Order:
    return create_order("LOC", "sell", amount, quantity, price, event)


def LObuy(
    price: float,
    amount: float | None = None,
    quantity: int | None = None,
    event: str | None = None,
) -> Order:
    return create_order("LO", "buy", amount, quantity, price, event)


def LOsell(
    price: float,
    amount: float | None = None,
    quantity: int | None = None,
    event: str | None = None,
) -> Order:
    return create_order("LO", "sell", amount, quantity, price, event)


def MOObuy(
    amount: float | None = None,
    quantity: int | None = None,
    event: str | None = None,
) -> Order:
    return create_order("MOO", "buy", amount, quantity, event=event)


def MOCsell(
    amount: float | None = None,
    quantity: int | None = None,
    event: str | None = None,
) -> Order:
    return create_order("MOC", "sell", amount, quantity, event=event)


def divide_unit(a: float, b: float, unit: int) -> int:
    return int(a // (b * unit)) * unit


def star_price_IB2_2(state: State, constants: Constants) -> float:
    star = (2 * constants.star_reference / constants.division_count) * (constants.division_count / 2 - state.t)
    return state.average_price * (1 + star * 0.01)


def prepare_fixed_amount(state: State, constants: Constants) -> None:
    state.buy_amount = state.capital / constants.division_count


def prepare_IB2_2(state: State, constants: Constants) -> None:
    if state.mode == "normal" or state.buy_amount <= 0:
        prepare_fixed_amount(state, constants)


def create_orders_IB1(
    state: State,
    constants: Constants,
    prices: Prices,
) -> List[Order]:
    amount = state.buy_amount
    if state.t == 0:
        return [MOObuy(amount=amount)]

    average_price = state.average_price
    return [
        LObuy(average_price, amount=amount / 2),
        LOCbuy(prices.open * 1.1, amount=amount / 2),
        LOsell(
            average_price * (1 + constants.sell_threshold * 0.01),
            quantity=state.quantity,
        ),
    ]


def create_orders_alternate_IB2_2(state: State, constants: Constants) -> List[Order]:
    ad_count = constants.division_count // 4
    quarter_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    rest_quantity = state.quantity - quarter_quantity

    if state.alter_t > ad_count - 1:
        return [MOCsell(quantity=quarter_quantity)]

    loc_price = state.average_price * (1 - constants.star_reference * 0.01)
    return [
        LOCbuy(loc_price - 0.01, amount=state.buy_amount),
        LOCsell(loc_price, quantity=quarter_quantity),
        LOsell(
            state.average_price * (1 + constants.sell_threshold * 0.01),
            quantity=rest_quantity,
        ),
    ]


def create_orders_IB2_2(
    state: State,
    constants: Constants,
    prices: Prices,
) -> List[Order]:
    if state.mode == "alternate":
        return create_orders_alternate_IB2_2(state, constants)

    amount = state.buy_amount
    if state.t == 0:
        return [MOObuy(amount=amount)]

    star_price = star_price_IB2_2(state, constants)
    if state.t < constants.division_count / 2:
        orders = [
            LOCbuy(state.average_price, amount=amount / 2),
            LOCbuy(star_price - 0.01, amount=amount / 2),
        ]
    else:
        orders = [LOCbuy(star_price - 0.01, amount=amount)]

    loc_sell_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    orders.extend([
        LOCsell(star_price, quantity=loc_sell_quantity),
        LOsell(
            state.average_price * (1 + constants.sell_threshold * 0.01),
            quantity=state.quantity - loc_sell_quantity,
        ),
    ])
    return orders


def calculate_compound_profit(
    state: State,
    realized_profit: float,
    mode: CompoundMode,
) -> tuple[float, float]:
    state.realized_profit += realized_profit
    new_peak = max(state.peak_profit, state.realized_profit)
    compound_profit = (new_peak - state.peak_profit) * mode.ratio
    saved_profit = realized_profit - compound_profit

    state.peak_profit = new_peak
    return compound_profit, saved_profit


def apply_profit_IB1_IB2_2(
    state: State,
    realized_profit: float,
    mode: CompoundMode,
) -> None:
    compound_profit, saved_profit = calculate_compound_profit(
        state,
        realized_profit,
        mode,
    )
    state.capital += compound_profit
    state.profit += saved_profit
    state.cash -= saved_profit


def restart_IB1_IB2_2(state: State, constants: Constants) -> None:
    if not constants.compound.is_realtime:
        apply_profit_IB1_IB2_2(
            state,
            state.pending_profit,
            constants.compound,
        )
        state.pending_profit = 0
    state.cash = state.capital
    state.average_price = 0
    state.t = 0
    state.mode = "normal"
    state.alter_t = 0
    state.buy_amount = 0


def settle_IB1_IB2_2(
    state: State,
    executed: list[Order],
    constants: Constants,
) -> None:
    for order in executed:
        if order["type"] != "sell":
            continue
        if constants.compound.is_realtime:
            apply_profit_IB1_IB2_2(
                state,
                order["realized_profit"],
                constants.compound,
            )
        else:
            state.pending_profit += order["realized_profit"]

    if state.quantity == 0:
        restart_IB1_IB2_2(state, constants)
        return

    if state.mode == "alternate":
        for order in executed:
            method_type = order["method"] + order["type"]
            if method_type == "MOCsell":
                state.alter_t = 0
                if order["actual_price"] >= state.average_price * 0.9:
                    state.mode = "normal"
                    state.buy_amount = 0
                else:
                    state.buy_amount = order["actual_price"] * order["actual_quantity"] / 10
            elif method_type == "LOCbuy":
                state.alter_t += 1
            elif method_type in ("LOCsell", "LOsell"):
                state.alter_t = 0
                state.mode = "normal"
                state.buy_amount = 0

    if state.mode == "normal":
        state.t = state.average_price * state.quantity / (state.capital / constants.division_count)
        if state.t > constants.division_count - 1:
            state.mode = "alternate"
            state.alter_t = constants.division_count // 4


def prepare_IB3(state: State, constants: Constants) -> None:
    if state.buy_amount <= 0:
        state.buy_amount = state.capital / constants.division_count

    if state.quantity == 0 or state.cash >= state.buy_amount:
        return

    transfer = min(state.buy_amount - state.cash, max(state.profit, 0))
    state.profit -= transfer
    state.cash += transfer
    if state.cash < state.buy_amount:
        state.mode = "alternate"
        state.alter_t = constants.division_count // 4


def create_orders_alternate_IB3(state: State, constants: Constants) -> List[Order]:
    max_extra_buys = constants.division_count // 4
    quarter_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    rest_quantity = state.quantity - quarter_quantity
    target_price = state.average_price * (1 + constants.sell_threshold * 0.01)

    if state.alter_t >= max_extra_buys or state.cash < state.buy_amount:
        return [
            MOCsell(quantity=quarter_quantity, event="quarter_moc"),
            LOsell(target_price, quantity=rest_quantity, event="alternate_exit"),
        ]

    star = constants.star_reference - (2 * constants.star_reference / constants.division_count) * state.t
    star_price = state.average_price * (1 + star * 0.01)
    buy_price = star_price - 0.01
    return [
        LOCbuy(buy_price, amount=state.buy_amount, event="alternate_buy"),
        LOCsell(
            star_price,
            quantity=quarter_quantity,
            event="alternate_exit",
        ),
        LOsell(
            target_price,
            quantity=rest_quantity,
            event="alternate_exit",
        ),
    ]


def create_orders_IB3(
    state: State,
    constants: Constants,
    prices: Prices,
) -> List[Order]:
    if state.mode == "alternate":
        return create_orders_alternate_IB3(state, constants)

    amount = state.buy_amount
    if state.t == 0:
        return [MOObuy(amount=amount)]

    star = constants.star_reference - (2 * constants.star_reference / constants.division_count) * state.t
    star_price = state.average_price * (1 + star * 0.01)
    if state.t < constants.division_count / 2:
        orders = [
            LOCbuy(state.average_price, amount=amount / 2),
            LOCbuy(star_price - 0.01, amount=amount / 2),
        ]
    else:
        orders = [LOCbuy(star_price - 0.01, amount=amount)]

    quarter_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    orders.extend([
        LOCsell(
            star_price,
            quantity=quarter_quantity,
            event="quarter_sell",
        ),
        LOsell(
            state.average_price * (1 + constants.sell_threshold * 0.01),
            quantity=state.quantity - quarter_quantity,
            event="target_sell",
        ),
    ])
    return orders


def apply_profit_IB3(
    state: State,
    realized_profit: float,
    constants: Constants,
) -> None:
    compound_profit, saved_profit = calculate_compound_profit(
        state,
        realized_profit,
        constants.compound,
    )
    state.capital += compound_profit
    state.buy_amount += compound_profit / constants.division_count
    state.profit += saved_profit
    state.cash -= saved_profit


def restart_IB3(state: State, constants: Constants) -> None:
    if not constants.compound.is_realtime:
        apply_profit_IB3(
            state,
            state.pending_profit,
            constants,
        )
        state.pending_profit = 0

    state.profit += state.cash - state.capital
    state.cash = state.capital
    state.average_price = 0
    state.t = 0
    state.mode = "normal"
    state.alter_t = 0


def settle_IB3(
    state: State,
    executed: list[Order],
    constants: Constants,
) -> None:
    for order in executed:
        if order["type"] != "sell":
            continue
        if constants.compound.is_realtime:
            apply_profit_IB3(
                state,
                order["realized_profit"],
                constants,
            )
        else:
            state.pending_profit += order["realized_profit"]

    if state.quantity == 0:
        restart_IB3(state, constants)
        return

    if state.mode == "alternate":
        events = {order.get("event") for order in executed}
        if "quarter_moc" in events:
            state.alter_t = 0
        if "alternate_buy" in events:
            state.alter_t += 1
        if "alternate_exit" in events:
            state.mode = "normal"
            state.alter_t = 0

    raw_t = state.average_price * state.quantity / state.buy_amount
    state.t = math.ceil(raw_t * 10 - 1e-12) / 10
    if state.mode == "normal" and state.t > constants.division_count - 1:
        state.mode = "alternate"
        state.alter_t = constants.division_count // 4


IB1 = Strategy(
    name="IB1",
    defaults=Constants(10, 10, 40, 1, CompoundMode.NO),
    prepare=prepare_fixed_amount,
    create_orders=create_orders_IB1,
    settle=settle_IB1_IB2_2,
)

IB2_2 = Strategy(
    name="IB2_2",
    defaults=Constants(10, 10, 40, 1, CompoundMode.NO),
    prepare=prepare_IB2_2,
    create_orders=create_orders_IB2_2,
    settle=settle_IB1_IB2_2,
)

IB3 = Strategy(
    name="IB3",
    defaults=Constants(15, 15, 20, 1, CompoundMode.HALF_REALTIME),
    prepare=prepare_IB3,
    create_orders=create_orders_IB3,
    settle=settle_IB3,
)

IB3_SOXL_DEFAULT = Constants(20, 20, 20, 1, CompoundMode.HALF_REALTIME)


def get_default_constants(method: TradeMethod) -> Constants:
    return replace(method.defaults)
