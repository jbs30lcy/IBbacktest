import sys

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow

from backtest import run_backtest
from methods import IB1, IB2_2, IB3, IB4
from models import State


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IB Backtester")
        self.setMinimumSize(800, 600)
        self.setCentralWidget(QLabel("IB Backtester"))


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
