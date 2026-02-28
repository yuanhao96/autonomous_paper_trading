"""v0: Prove the pipeline shape works.

One file, one strategy (SMA crossover), one ticker (SPY), print stats.
No abstractions, no config, no LLM.
"""

import pandas as pd
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover


def sma(values, period):
    """Simple moving average that works with backtesting.py's numpy arrays."""
    return pd.Series(values).rolling(period).mean()


class SmaCrossover(Strategy):
    """Buy when fast SMA crosses above slow SMA, sell on cross below."""

    fast_period = 20
    slow_period = 50

    def init(self):
        self.fast_sma = self.I(sma, self.data.Close, self.fast_period)
        self.slow_sma = self.I(sma, self.data.Close, self.slow_period)

    def next(self):
        if crossover(self.fast_sma, self.slow_sma):
            self.buy()
        elif crossover(self.slow_sma, self.fast_sma):
            self.position.close()


def main():
    # Download data
    print("Downloading SPY daily data...")
    df = yf.download("SPY", start="2020-01-01", end="2025-12-31", progress=False)

    # backtesting.py expects flat columns: Open, High, Low, Close, Volume
    if hasattr(df.columns, "levels") and df.columns.nlevels > 1:
        df = df.droplevel(level=1, axis=1)

    print(f"Data: {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}\n")

    # Run backtest
    bt = Backtest(
        df,
        SmaCrossover,
        cash=100_000,
        commission=0.001,  # 10 bps
        exclusive_orders=True,
    )
    stats = bt.run()

    # Print key metrics
    print("=" * 50)
    print("SMA Crossover (20/50) on SPY")
    print("=" * 50)
    print(f"Total Return:    {stats['Return [%]']:.2f}%")
    print(f"Buy & Hold:      {stats['Buy & Hold Return [%]']:.2f}%")
    print(f"Sharpe Ratio:    {stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown:    {stats['Max. Drawdown [%]']:.2f}%")
    print(f"# Trades:        {stats['# Trades']}")
    print(f"Win Rate:        {stats['Win Rate [%]']:.1f}%")
    print(f"Avg Trade:       {stats['Avg. Trade [%]']:.2f}%")
    print(f"Exposure Time:   {stats['Exposure Time [%]']:.1f}%")
    print("=" * 50)


if __name__ == "__main__":
    main()
