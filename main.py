from pathlib import Path

from backtest import calculate_buy_unit, run_backtest
from methods import IB1
from models import State
from report import export_graph, print_state


def main(
    start_date: str | int | None = None,
    end_date: str | int | None = None,
    data: str | Path = "TQQQ_daily.csv",
) -> None:
    csv_path = Path(data)
    if not csv_path.is_absolute():
        project_path = Path(__file__).parent / csv_path
        csv_path = (
            project_path
            if project_path.exists()
            else Path(__file__).parent / "market_data" / csv_path
        )

    initial_capital = 40_000
    initial_state = State(
        profit=0,
        initial_capital=initial_capital,
        capital=initial_capital,
        cash=initial_capital,
        quantity=0,
        average_price=0,
        t=0,
        buy_unit=calculate_buy_unit(csv_path, start_date),
        mode="normal",
    )
    final_state, result = run_backtest(
        csv_path=csv_path,
        initial_state=initial_state,
        method=IB1,
        start_date=start_date,
        end_date=end_date,
    )

    print_state(final_state, result)
    export_graph(result, Path(__file__).parent / "output" / "tqqq_ib1_ref10.png")


if __name__ == "__main__":
    main()
