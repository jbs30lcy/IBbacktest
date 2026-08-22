from copy import copy

from backtest import calculate_buy_unit, run_backtests
from methods import IB4, create_orders_IB4quartersell, get_default_constants
from models import State, Strategy
from report import print_state


def main():
    tqqq_path = "market_data/TQQQ_daily.csv"
    soxl_path = "market_data/SOXL_daily.csv"
    start_date = 20220101
    end_date = 20230601

    tqqq_initial_state = State(
        profit=0,
        initial_capital=20000,
        capital=20000,
        cash=20000,
        quantity=0,
        average_price=0,
        t=0,
        buy_unit=calculate_buy_unit(tqqq_path, start_date),
        mode="normal",
    )
    soxl_initial_state = copy(tqqq_initial_state)
    soxl_initial_state.buy_unit = calculate_buy_unit(soxl_path, start_date)

    tqqq_40_constants = get_default_constants("TQQQ", IB4)
    tqqq_40_constants.division_count = 40
    soxl_40_constants = get_default_constants("SOXL", IB4)
    soxl_40_constants.division_count = 40

    IB4_40 = Strategy(
        key="IB4_40",
        name="IB4_40",
        prepare=IB4.prepare,
        create_orders=IB4.create_orders,
        settle=IB4.settle,
    )

    IB4_40_quartersell = Strategy(
        key="IB4_40_QUARTERSELL",
        name="IB4_40_quartersell",
        prepare=IB4.prepare,
        create_orders=create_orders_IB4quartersell,
        settle=IB4.settle,
    )

    tqqq_results = run_backtests(
        csv_path=tqqq_path,
        initial_state=tqqq_initial_state,
        methods=[IB4_40, IB4_40_quartersell],
        graph_path="output/tqqq_2022.png",
        product="TQQQ",
        constants=tqqq_40_constants,
        start_date=start_date,
        end_date=end_date,
    )
    soxl_results = run_backtests(
        csv_path=soxl_path,
        initial_state=soxl_initial_state,
        methods=[IB4_40, IB4_40_quartersell],
        graph_path="output/soxl_2022.png",
        product="SOXL",
        constants=soxl_40_constants,
        start_date=start_date,
        end_date=end_date,
    )



if __name__ == "__main__":
    main()
