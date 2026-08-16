import warnings
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
    return order


def LOCbuy(
    price: float,
    amount: float | None = None,
    quantity: int | None = None,
) -> Order:
    return create_order("LOC", "buy", amount, quantity, price)


def LOCsell(
    price: float,
    amount: float | None = None,
    quantity: int | None = None,
) -> Order:
    return create_order("LOC", "sell", amount, quantity, price)


def LObuy(
    price: float,
    amount: float | None = None,
    quantity: int | None = None,
) -> Order:
    return create_order("LO", "buy", amount, quantity, price)


def LOsell(
    price: float,
    amount: float | None = None,
    quantity: int | None = None,
) -> Order:
    return create_order("LO", "sell", amount, quantity, price)


def MOObuy(
    amount: float | None = None,
    quantity: int | None = None,
) -> Order:
    return create_order("MOO", "buy", amount, quantity)


def MOCsell(
    amount: float | None = None,
    quantity: int | None = None,
) -> Order:
    return create_order("MOC", "sell", amount, quantity)


def divide_unit(a: float, b: float, unit: int) -> int:
    return int(a // (b * unit)) * unit


def star_price(state: State, constants: Constants) -> float:
    star = (2 * constants.star_reference / constants.division_count) * (constants.division_count / 2 - state.t)
    return state.average_price * (1 + star * 0.01)


def prepare_fixed_amount(state: State, constants: Constants) -> None:
    state.buy_amount = state.capital / constants.division_count


def prepare_IB2_2(state: State, constants: Constants) -> None:
    if state.mode == "normal" or state.buy_amount <= 0:
        prepare_fixed_amount(state, constants)


def prepare_IB4(state: State, constants: Constants) -> None:
    if state.mode == "alternate":
        state.buy_amount = state.cash / 4
    else:
        remaining_turns = constants.division_count - state.t
        if remaining_turns == 0:
            raise RuntimeError("이게 0이면 alternate여야 하는데 이상하당")
        state.buy_amount = state.cash / remaining_turns


def create_orders_IB1(
    state: State,
    constants: Constants,
    prices: Prices,
) -> List[Order]:
    amount = state.buy_amount
    if state.quantity > 0 and state.cash < amount:
        return [MOCsell(quantity=state.quantity)]

    if state.t == 0:
        return [MOObuy(amount=amount)]

    average_price = state.average_price
    return [
        LObuy(average_price, amount=amount / 2),
        LOCbuy(prices.open * 1.1, amount=amount / 2),
        LOsell(
            average_price * (1 + constants.sell_reference * 0.01),
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
            state.average_price * (1 + constants.sell_reference * 0.01),
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

    star = star_price(state, constants)
    if state.t < constants.division_count / 2:
        orders = [
            LOCbuy(state.average_price, amount=amount / 2),
            LOCbuy(star - 0.01, amount=amount / 2),
        ]
    else:
        orders = [LOCbuy(star - 0.01, amount=amount)]

    loc_sell_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    orders.extend([
        LOCsell(star, quantity=loc_sell_quantity),
        LOsell(
            state.average_price * (1 + constants.sell_reference * 0.01),
            quantity=state.quantity - loc_sell_quantity,
        ),
    ])
    return orders


def create_orders_alternate_IB3(state: State, constants: Constants) -> List[Order]:
    max_extra_buys = constants.division_count // 4
    quarter_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    rest_quantity = state.quantity - quarter_quantity
    target_price = state.average_price * (1 + constants.sell_reference * 0.01)

    if state.alter_t >= max_extra_buys or state.cash < state.buy_amount:
        return [
            MOCsell(quantity=quarter_quantity),
            LOsell(target_price, quantity=rest_quantity),
        ]

    star = star_price(state, constants)
    buy_price = star - 0.01
    return [
        LOCbuy(buy_price, amount=state.buy_amount),
        LOCsell(star, quantity=quarter_quantity),
        LOsell(target_price, quantity=rest_quantity),
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

    star = star_price(state, constants)
    if state.t < constants.division_count / 2:
        orders = [
            LOCbuy(state.average_price, amount=amount / 2),
            LOCbuy(star - 0.01, amount=amount / 2),
        ]
    else:
        orders = [LOCbuy(star - 0.01, amount=amount)]

    quarter_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    orders.extend([
        LOCsell(star, quantity=quarter_quantity),
        LOsell(
            state.average_price * (1 + constants.sell_reference * 0.01),
            quantity=state.quantity - quarter_quantity,
        ),
    ])
    return orders


def create_orders_alternate_IB4(
    state: State,
    constants: Constants,
    prices: Prices,
) -> List[Order]:
    sell_divisor = constants.division_count // 2
    sell_quantity = divide_unit(state.quantity, sell_divisor, state.buy_unit)

    if state.alter_t == 0:
        return [MOCsell(quantity=sell_quantity)] if sell_quantity > 0 else []

    star = prices.previous_five_close_average
    if star is None:
        raise ValueError("IB4 alternate mode requires five previous closing prices.")

    if star > state.buy_amount:
        return [MOCsell(quantity=sell_quantity)] if sell_quantity > 0 else []

    orders: List[Order] = []
    if state.buy_amount > 0:
        orders.append(LOCbuy(star - 0.01, amount=state.buy_amount))
    if sell_quantity > 0:
        orders.append(LOCsell(star, quantity=sell_quantity))
    return orders


def create_orders_IB4(
    state: State,
    constants: Constants,
    prices: Prices,
) -> List[Order]:
    if state.mode == "alternate":
        return create_orders_alternate_IB4(state, constants, prices)

    amount = state.buy_amount
    if state.t == 0:
        reference_price = prices.previous_close or prices.open
        return [LOCbuy(reference_price * 1.15, amount=amount)]

    star = star_price(state, constants)
    if state.t < constants.division_count / 2:
        orders = [
            LOCbuy(state.average_price, amount=amount / 2),
            LOCbuy(star - 0.01, amount=amount / 2),
        ]
    else:
        orders = [
            LOCbuy(star - 0.01, amount=amount),
        ]

    quarter_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    orders.extend([
        LOCsell(star, quantity=quarter_quantity),
        LOsell(
            state.average_price * (1 + constants.sell_reference * 0.01),
            quantity = state.quantity - quarter_quantity,
        ),
    ])
    return orders

def create_orders_IB4quartersell(
    state: State,
    constants: Constants,
    prices: Prices,
) -> List[Order]:
    if state.mode == "alternate":
        return [MOCsell(quantity=state.quantity)]

    amount = state.buy_amount
    if state.t == 0:
        reference_price = prices.previous_close or prices.open
        return [LOCbuy(reference_price * 1.15, amount=amount)]

    star = star_price(state, constants)
    if state.t < constants.division_count / 2:
        orders = [
            LOCbuy(state.average_price, amount=amount / 2),
            LOCbuy(star - 0.01, amount=amount / 2),
        ]
    else:
        orders = [
            LOCbuy(star - 0.01, amount=amount),
        ]

    quarter_quantity = divide_unit(state.quantity, 4, state.buy_unit)
    orders.extend([
        LOCsell(star, quantity=quarter_quantity),
        LOsell(
            state.average_price * (1 + constants.sell_reference * 0.01),
            quantity = state.quantity - quarter_quantity,
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

def apply_profit(
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
    state.buy_amount = state.capital / constants.division_count
    state.profit += saved_profit
    state.cash -= saved_profit


def restart(state: State, constants: Constants) -> None:
    if not constants.compound.is_realtime:
        apply_profit(
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


def settle_IB1(
    state: State,
    executed: list[Order],
    constants: Constants,
    prices: Prices | None = None,
) -> None:
    for order in executed:
        if order["type"] != "sell":
            continue
        if constants.compound.is_realtime:
            apply_profit(
                state,
                order["realized_profit"],
                constants,
            )
        else:
            state.pending_profit += order["realized_profit"]

    if state.quantity == 0:
        restart(state, constants)
        return

    for order in executed:
        if order["type"] != "buy":
            continue
        state.t += 1 if order["method"] == "MOO" else 0.5


def settle_IB1_IB2_2(
    state: State,
    executed: list[Order],
    constants: Constants,
    prices: Prices | None = None,
) -> None:
    for order in executed:
        if order["type"] != "sell":
            continue
        if constants.compound.is_realtime:
            apply_profit(
                state,
                order["realized_profit"],
                constants,
            )
        else:
            state.pending_profit += order["realized_profit"]

    if state.quantity == 0:
        restart(state, constants)
        return

    if state.mode == "alternate":
        for order in executed:
            method_type = order["method"] + order["type"]
            if method_type == "MOCsell":
                state.alter_t = 0
                if order["actual_price"] >= state.average_price * (1 - constants.star_reference * 0.01):
                    state.mode = "normal"
                    state.buy_amount = 0
                else:
                    state.buy_amount = order["actual_price"] * order["actual_quantity"] / (constants.division_count // 4)
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


def settle_IB3(
    state: State,
    executed: list[Order],
    constants: Constants,
    prices: Prices | None = None,
) -> None:
    for order in executed:
        if order["type"] != "sell":
            continue
        if constants.compound.is_realtime:
            apply_profit(
                state,
                order["realized_profit"],
                constants,
            )
        else:
            state.pending_profit += order["realized_profit"]

    if state.quantity == 0:
        restart(state, constants)
        return

    if state.mode == "alternate":
        for order in executed:
            method_type = order["method"] + order["type"]
            if method_type == "MOCsell":
                state.alter_t = 0
                if order["actual_price"] >= state.average_price * (1 - constants.star_reference * 0.01):
                    state.mode = "normal"
                else:
                    target_cash = (constants.division_count // 4) * state.buy_amount
                    state.profit += state.cash - target_cash
                    state.cash = target_cash
            elif method_type == "LOCbuy":
                state.alter_t += 1
            elif method_type in ("LOCsell", "LOsell"):
                state.mode = "normal"
                state.alter_t = 0

    state.t = state.average_price * state.quantity / state.buy_amount
    if state.mode == "normal" and state.t > constants.division_count - 1:
        state.mode = "alternate"
        state.alter_t = constants.division_count // 4


def quantity_based_add_t(state: State, order: Order) -> float:
    executed_amount = order["actual_price"] * order["value"]
    if 0 < executed_amount <= state.buy_amount / 2:
        return 0.5
    if state.buy_amount / 2 < executed_amount <= state.buy_amount:
        return 1
    raise ValueError(
        "IB4 quantity-based buy amount must be greater than 0 "
        "and less than or equal to buy_amount."
    )


def apply_sell_profits_IB4(
    state: State,
    executed: list[Order],
    constants: Constants,
) -> None:
    for order in executed:
        if order["type"] != "sell":
            continue
        if constants.compound.is_realtime:
            apply_profit(
                state,
                order["realized_profit"],
                constants,
            )
        else:
            state.pending_profit += order["realized_profit"]


def settle_normal_IB4(
    state: State,
    executed: list[Order],
    constants: Constants,
) -> None:
    for order in executed:
        if order["type"] != "sell":
            continue
        if order["method"] == "LOC":
            state.t *= 0.75
        elif order["method"] == "LO":
            state.t *= 0.25

    for order in executed:
        if order["type"] == "buy":
            if order["by"] == "amount":
                state.t += order["value"] / state.buy_amount
            else:
                warnings.warn(
                    "Quantity-based IB4 buy orders are not recommended.",
                    UserWarning,
                    stacklevel=3,
                )
                state.t += quantity_based_add_t(state, order)

    apply_sell_profits_IB4(state, executed, constants)

    if state.quantity == 0:
        restart(state, constants)
        return

    if state.t > constants.division_count - 1:
        state.mode = "alternate"
        state.alter_t = 0


def settle_alternate_IB4(
    state: State,
    executed: list[Order],
    constants: Constants,
    prices: Prices,
) -> None:
    for order in executed:
        if order["type"] == "sell":
            state.t *= 1 - 2 / constants.division_count
        elif order["type"] == "buy":
            state.t += (constants.division_count - state.t) * 0.25

    apply_sell_profits_IB4(state, executed, constants)

    if state.quantity == 0:
        restart(state, constants)
        return

    state.alter_t += 1
    recovery_price = state.average_price * (
        1 - constants.sell_reference * 0.01
    )
    if prices.close > recovery_price:
        state.mode = "normal"
        state.alter_t = 0


def settle_IB4(
    state: State,
    executed: list[Order],
    constants: Constants,
    prices: Prices | None = None,
) -> None:
    if state.mode == "normal":
        settle_normal_IB4(state, executed, constants)
        return

    if state.mode == "alternate":
        if prices is None:
            raise ValueError("IB4 alternate settlement requires current prices.")
        settle_alternate_IB4(state, executed, constants, prices)
        return

    raise ValueError(f"Unsupported IB4 mode: {state.mode}")


IB1 = Strategy(
    name="IB1",
    defaults=Constants(10, 10, 40, 1, CompoundMode.NO),
    prepare=prepare_fixed_amount,
    create_orders=create_orders_IB1,
    settle=settle_IB1,
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
    prepare=prepare_fixed_amount,
    create_orders=create_orders_IB3,
    settle=settle_IB3,
)

IB3_SOXL_DEFAULT = Constants(20, 20, 20, 1, CompoundMode.HALF_REALTIME)

IB4 = Strategy(
    name="IB4",
    defaults=Constants(15, 15, 20, 1, CompoundMode.HALF_REALTIME),
    prepare=prepare_IB4,
    create_orders=create_orders_IB4,
    settle=settle_IB4,
)

IB4_SOXL_DEFAULT = Constants(20, 20, 20, 1, CompoundMode.HALF_REALTIME)


def get_default_constants(method: TradeMethod) -> Constants:
    return replace(method.defaults)
