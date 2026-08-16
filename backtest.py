from copy import copy
from pathlib import Path

import pandas as pd

from engine import trade
from methods import get_default_constants
from models import Constants, State, TradeMethod
from report import export_comparison_graph, export_csv


def calculate_buy_unit(
    csv_path: str | Path,
    start_date: str | int | None = None,
) -> int:
    data = pd.read_csv(csv_path, parse_dates=["Date"])
    start = data["Date"].min() if start_date is None else pd.to_datetime(str(start_date))
    splits = data.loc[data["Date"] >= start, "Stock Splits"].replace(0, 1)
    return int(round(splits.prod()))


def run_backtest(
    csv_path: str | Path,
    initial_state: State,
    method: TradeMethod,
    constants: Constants | None = None,
    start_date: str | int | None = None,
    end_date: str | int | None = None,
    output_csv_path: str | Path | None = None,
) -> tuple[State, pd.DataFrame]:
    if constants is None:
        constants = get_default_constants(method)

    data = pd.read_csv(csv_path, parse_dates=["Date"])
    data["_Previous Close"] = data["Close"].shift(1)
    data["_Previous 5 Close Average"] = data["Close"].shift(1).rolling(5).mean()

    first_date = data["Date"].min()
    last_date = data["Date"].max()
    start = first_date if start_date is None else pd.to_datetime(str(start_date))
    end = last_date if end_date is None else pd.to_datetime(str(end_date))

    if start > end:
        raise ValueError("시작 날짜는 끝 날짜보다 늦을 수 없습니다.")

    selected_data = data[(data["Date"] >= start) & (data["Date"] <= end)].reset_index(drop=True)
    if selected_data.empty:
        raise ValueError("지정한 기간에 거래 데이터가 없습니다.")

    state = copy(initial_state)
    state.buy_unit = calculate_buy_unit(csv_path, selected_data.iloc[0]["Date"])
    records = []

    for row in range(len(selected_data)):
        state = trade(
            state,
            constants,
            selected_data,
            row,
            method,
        )
        csv_row = selected_data.iloc[row]
        position_value = state.quantity * csv_row["Close"]
        records.append({
            "Date": csv_row["Date"],
            "Close": csv_row["Close"],
            "Profit": state.profit,
            "Capital": state.capital,
            "Cash": state.cash,
            "Quantity": state.quantity,
            "Average Price": state.average_price,
            "T": state.t,
            "Buy Unit": state.buy_unit,
            "Mode": state.mode,
            "Position Value": position_value,
            "Total Value": state.profit + state.cash + position_value,
        })

    result = pd.DataFrame(records)
    if output_csv_path is not None:
        export_csv(result, output_csv_path)
    return state, result


def run_backtests(
    csv_path: str | Path,
    initial_state: State,
    methods: list[TradeMethod],
    graph_path: str | Path,
    constants: Constants | None = None,
    start_date: str | int | None = None,
    end_date: str | int | None = None,
) -> dict[str, tuple[State, pd.DataFrame]]:
    if not methods:
        raise ValueError("methods에 하나 이상의 방법을 넣어야 합니다.")

    results: dict[str, tuple[State, pd.DataFrame]] = {}
    for method in methods:
        base_name = method.name
        name = base_name
        number = 2
        while name in results:
            name = f"{base_name}_{number}"
            number += 1

        results[name] = run_backtest(
            csv_path=csv_path,
            initial_state=initial_state,
            method=method,
            constants=constants,
            start_date=start_date,
            end_date=end_date,
        )

    export_comparison_graph(
        {name: result for name, (_, result) in results.items()},
        graph_path,
    )
    return results
