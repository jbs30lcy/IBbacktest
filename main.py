from copy import copy

from backtest import calculate_buy_unit, run_backtests
from methods import IB4, IB4_SOXL_DEFAULT, create_orders_IB4quartersell
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

    ib4_40_defaults = copy(IB4.defaults)
    ib4_40_defaults.division_count = 40
    soxl_40_constants = copy(IB4_SOXL_DEFAULT)
    soxl_40_constants.division_count = 40

    IB4_40 = Strategy(
        name="IB4_40",
        defaults=ib4_40_defaults,
        prepare=IB4.prepare,
        create_orders=IB4.create_orders,
        settle=IB4.settle,
    )

    IB4_40_quartersell = Strategy(
        name="IB4_40_quartersell",
        defaults=ib4_40_defaults,
        prepare=IB4.prepare,
        create_orders=create_orders_IB4quartersell,
        settle=IB4.settle,
    )

    tqqq_results = run_backtests(
        csv_path=tqqq_path,
        initial_state=tqqq_initial_state,
        methods=[IB4_40, IB4_40_quartersell],
        graph_path="output/tqqq_2022.png",
        start_date=start_date,
        end_date=end_date,
    )
    soxl_results = run_backtests(
        csv_path=soxl_path,
        initial_state=soxl_initial_state,
        methods=[IB4_40, IB4_40_quartersell],
        graph_path="output/soxl_2022.png",
        constants=soxl_40_constants,
        start_date=start_date,
        end_date=end_date,
    )



if __name__ == "__main__":
    main()
