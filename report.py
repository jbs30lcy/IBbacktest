from pathlib import Path
from typing import Mapping

import pandas as pd

from models import State


def print_state(state: State, result: pd.DataFrame) -> None:
    last = result.iloc[-1]

    print("\n=== 백테스트 결과 ===")
    print(f"기간: {result.iloc[0]['Date']:%Y-%m-%d} ~ {last['Date']:%Y-%m-%d}")
    print(f"거래일: {len(result):,}일")
    print(f"누적 실현손익: {state.profit:,.2f}")
    print(f"운용 원금: {state.capital:,.2f}")
    print(f"현금: {state.cash:,.2f}")
    print(f"보유수량: {state.quantity:,.0f}")
    print(f"평단가: {state.average_price:,.4f}")
    print(f"진행 회차 T: {state.t:g}")
    print(f"보유자산 평가액: {last['Position Value']:,.2f}")
    print(f"총자산: {last['Total Value']:,.2f}")


def export_csv(result: pd.DataFrame, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"CSV 저장: {output_path}")


def export_graph(result: pd.DataFrame, output_path: str | Path) -> None:
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(12, 6))
    axis.plot(result["Date"], result["Total Value"], label="Total Value")
    axis.set_title("Backtest Result")
    axis.set_xlabel("Date")
    axis.set_ylabel("Value")
    axis.grid(alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    print(f"Graph 저장: {output_path}")


def export_comparison_graph(
    results: Mapping[str, pd.DataFrame],
    output_path: str | Path,
) -> None:
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(12, 6))
    for name, result in results.items():
        axis.plot(result["Date"], result["Total Value"], label=name)
    axis.set_title("Backtest Comparison")
    axis.set_xlabel("Date")
    axis.set_ylabel("Value")
    axis.grid(alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    print(f"Comparison graph 저장: {output_path}")
