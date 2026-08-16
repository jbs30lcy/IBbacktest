from backtest import calculate_buy_unit, run_backtests
from methods import IB4, create_orders_IB4quartersell
from models import State, Strategy
from report import print_state


def main():
    csv_path = "market_data/TQQQ_daily.csv"
    start_date = 20220101
    end_date = 20221231

    initial_state = State(
        profit=0,
        initial_capital=40000,
        capital=40000,
        cash=40000,
        quantity=0,
        average_price=0,
        t=0,
        buy_unit=calculate_buy_unit(csv_path, start_date),
        mode="normal",
    )

    IB4quartersell = Strategy(
        name="IB4quartersell",
        defaults=IB4.defaults,
        prepare=IB4.prepare,
        create_orders=create_orders_IB4quartersell,
        settle=IB4.settle,
    )

    results = run_backtests(
        csv_path=csv_path,
        initial_state=initial_state,
        methods=[IB4, IB4quartersell],
        graph_path="output/tqqq_ib4_quartersell_2022.png",
        start_date=start_date,
        end_date=end_date,
    )

    for name, (final_state, result) in results.items():
        print(f"\n[{name}]")
        print_state(final_state, result)


if __name__ == "__main__":
    main()
