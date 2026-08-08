from copy import copy

import pandas as pd

from methods import Order, divide_unit
from models import Constants, Prices, State, TradeMethod


def _buy(state: State, order: Order, trade_price: float) -> tuple[State, bool]:
    if trade_price <= 0:
        return state, False

    if order["by"] == "amount":
        quantity = divide_unit(order["value"], trade_price, state.buy_unit)
    else:
        quantity = order["value"]

    trade_amount = trade_price * quantity
    if quantity <= 0 or state.cash < trade_amount:
        return state, False

    state.average_price = (state.average_price * state.quantity + trade_amount) / (state.quantity + quantity)
    state.quantity += quantity
    state.cash -= trade_amount
    order["actual_quantity"] = quantity
    return state, True


def _sell(state: State, order: Order, trade_price: float) -> tuple[State, bool]:
    if trade_price <= 0:
        return state, False

    if order["by"] == "amount":
        quantity = divide_unit(order["value"], trade_price, state.buy_unit)
    else:
        quantity = order["value"]

    if quantity <= 0 or state.quantity < quantity:
        return state, False

    order["actual_quantity"] = quantity
    order["realized_profit"] = (trade_price - state.average_price) * quantity
    state.quantity -= quantity
    state.cash += trade_price * quantity
    if state.quantity == 0:
        state.average_price = 0
    return state, True


def execute(
    order_list: list[Order],
    state: State,
    prices: Prices,
) -> list[Order]:
    executed_list = []

    for order in order_list:
        success = False
        if order["method"] == "MOO":
            if order["type"] == "buy":
                state, success = _buy(state, order, prices.open)
            else:
                state, success = _sell(state, order, prices.open)
        if success:
            order["actual_price"] = prices.open
            executed_list.append(order)

    for order in order_list:
        success = False
        if order["method"] == "LO":
            if order["type"] == "buy" and prices.low <= order["price"]:
                actual_price = min(order["price"], prices.open)
                state, success = _buy(state, order, actual_price)
            elif order["type"] == "sell" and prices.high >= order["price"]:
                actual_price = max(order["price"], prices.open)
                state, success = _sell(state, order, actual_price)
        if success:
            order["actual_price"] = actual_price
            executed_list.append(order)

    for order in order_list:
        success = False
        if order["method"] == "MOC":
            if order["type"] == "buy":
                state, success = _buy(state, order, prices.close)
            else:
                state, success = _sell(state, order, prices.close)
        elif order["method"] == "LOC":
            if order["type"] == "buy" and prices.close <= order["price"]:
                state, success = _buy(state, order, prices.close)
            elif order["type"] == "sell" and prices.close >= order["price"]:
                state, success = _sell(state, order, prices.close)
        if success:
            order["actual_price"] = prices.close
            executed_list.append(order)

    return executed_list


def trade(
    state: State,
    constants: Constants,
    data: pd.DataFrame,
    row: int,
    method: TradeMethod,
) -> State:
    csv_row = data.iloc[row]
    new_state = copy(state)

    split_ratio = csv_row["Stock Splits"]
    if split_ratio > 0:
        new_state.buy_unit = int(new_state.buy_unit / split_ratio)

    prices = Prices(
        open=csv_row["Open"],
        high=csv_row["High"],
        low=csv_row["Low"],
        close=csv_row["Close"],
        adj_close=csv_row["Adj Close"],
    )
    method.prepare(new_state, constants)
    order_list = method.create_orders(new_state, constants, prices)
    executed_list = execute(order_list, new_state, prices)
    method.settle(new_state, executed_list, constants)
    return new_state
