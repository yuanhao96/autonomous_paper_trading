# Glossary

## Overview

Key terms and definitions used in algorithmic trading, quantitative finance, and strategy development. Organized alphabetically for quick reference.

## Terms

### A

**Alpha**: The excess return of a strategy beyond what is explained by exposure to systematic risk factors (beta). Positive alpha indicates skill or market inefficiency.

**Ask Price**: The lowest price at which a seller is willing to sell an instrument. Also called the "offer."

**Asset Class**: A category of financial instruments with similar characteristics. Major classes: equities, fixed income, commodities, forex, crypto.

### B

**Backtest**: A simulation of a trading strategy using historical data to evaluate its hypothetical performance.

**Bar**: A data point representing market activity over a fixed time period (e.g., 1-minute bar, daily bar). Contains Open, High, Low, Close, and Volume (OHLCV).

**Benchmark**: A reference index (e.g., S&P 500) used to evaluate strategy performance.

**Beta**: A measure of an asset's sensitivity to market movements. Beta = Cov(R_asset, R_market) / Var(R_market).

**Bid Price**: The highest price a buyer is willing to pay for an instrument.

**Bid-Ask Spread**: The difference between the ask price and the bid price. A measure of liquidity — tighter spreads indicate more liquid markets.

### C

**Carry**: The return from holding an asset, excluding price changes. Examples: interest income from bonds, dividend yield from stocks, interest rate differential in forex.

**Consolidation**: Aggregating smaller data bars into larger ones (e.g., combining 1-minute bars into 5-minute bars).

**Correlation**: A measure of the linear relationship between two variables, ranging from -1 (perfectly inverse) to +1 (perfectly aligned).

**Covariance**: A measure of how two variables move together. Positive covariance means they tend to move in the same direction.

**Cross-Sectional**: Comparing multiple instruments at the same point in time (e.g., ranking all stocks by momentum).

### D

**Drawdown**: The peak-to-trough decline in portfolio value. Maximum drawdown is the largest such decline over a backtest period.

**Diversification**: Reducing portfolio risk by combining assets with low or negative correlations.

### E

**Efficient Frontier**: The set of portfolios offering the highest expected return for each level of risk (Markowitz mean-variance optimization).

**Event-Driven**: A programming model where the algorithm reacts to events (data arrival, order fills) rather than running in a continuous loop.

### F

**Factor**: A systematic source of return (e.g., market, size, value, momentum, quality). Factor models decompose returns into factor exposures.

**Fill**: The execution of an order. A "fill price" is the price at which an order was executed.

**Fill-Forward**: Repeating the last known price when no new data is available for a bar period.

### G

**Gross Exposure**: The sum of absolute position values (|long| + |short|), measuring total market exposure regardless of direction.

### H

**Hedging**: Taking an offsetting position to reduce risk. Example: shorting a market ETF to hedge equity-long portfolio.

**High-Water Mark**: The highest portfolio value achieved. Used to calculate drawdown and performance fees.

### I

**In-Sample**: The portion of data used to develop and optimize a strategy. Contrast with out-of-sample.

### K

**Kelly Criterion**: A formula for optimal position sizing: f* = (bp - q) / b, where b is odds, p is win probability, q = 1-p.

### L

**Leverage**: Using borrowed capital to increase position size beyond the portfolio's equity. 2x leverage = $2 of exposure per $1 of equity.

**Limit Order**: An order to buy/sell at a specific price or better. Not guaranteed to fill.

**Liquidity**: The ease of trading an instrument without significantly affecting its price. High volume = high liquidity.

**Long**: Buying an instrument with the expectation that its price will rise.

**Look-Ahead Bias**: Using information in a backtest that wasn't available at the simulated time. The most dangerous backtesting error.

### M

**Market Impact**: The price movement caused by a large order. Large buy orders push prices up; large sell orders push prices down.

**Market Order**: An order to buy/sell immediately at the best available price. Guaranteed to fill (for liquid instruments).

**Market-Neutral**: A strategy with zero (or near-zero) exposure to overall market movements (beta ≈ 0).

**Maximum Drawdown**: The largest peak-to-trough decline in portfolio value during a backtest or live period.

**Mean Reversion**: The tendency of prices to return to their historical average. Contrarian strategies exploit mean reversion.

**Momentum**: The tendency of assets that have performed well to continue performing well (and vice versa).

### N

**Net Exposure**: Long value minus short value. Measures directional market bias.

### O

**OHLCV**: Open, High, Low, Close, Volume — the standard fields in a price bar.

**Out-of-Sample**: Data not used during strategy development, reserved for validation.

**Overfitting**: Tuning a strategy to fit historical noise rather than genuine patterns. Results in poor live performance.

### P

**P&L (Profit and Loss)**: The gain or loss from trading. Realized P&L is from closed trades; unrealized P&L is from open positions.

**Paper Trading**: Running a strategy with real market data but simulated orders. An intermediate step between backtesting and live trading.

**Position Sizing**: Determining how many shares/contracts to trade per signal. Methods include equal-weight, risk parity, Kelly criterion.

### R

**Rebalancing**: Adjusting portfolio weights back to target allocations. Common frequencies: daily, weekly, monthly, quarterly.

**Resolution**: The time granularity of data (tick, second, minute, hourly, daily).

**Risk-Free Rate**: The theoretical return of a zero-risk investment, typically proxied by short-term government bonds (e.g., 3-month T-bills).

### S

**Sharpe Ratio**: Risk-adjusted return metric. Sharpe = (R_portfolio - R_risk-free) / σ_portfolio. Higher is better; >1.0 is generally considered good.

**Short**: Selling an instrument you don't own (borrowing to sell) with the expectation that its price will fall.

**Slippage**: The difference between the expected execution price and the actual fill price. Caused by market movement and order processing delays.

**Stop-Loss**: An order to sell a position when it reaches a specified loss level. Limits downside risk.

**Survivorship Bias**: The error of only analyzing instruments that survived to the present, ignoring delisted/bankrupt companies.

### T

**Tick**: The smallest possible price movement for an instrument, or a single trade/quote event.

**Time Series**: Sequential data points indexed in time order. The fundamental data structure in quantitative finance.

**Timeslice**: A synchronized snapshot of all available market data at a single point in time.

**Transaction Costs**: All costs associated with trading: commissions, bid-ask spread, market impact, taxes.

**Turnover**: The rate at which portfolio positions change. Higher turnover = higher transaction costs.

### U

**Universe**: The set of instruments eligible for trading at any point in time. Can be static (fixed list) or dynamic (filtered by criteria).

### V

**Value-at-Risk (VaR)**: The maximum expected loss over a given time period at a specified confidence level (e.g., 95% VaR = the loss not exceeded 95% of the time).

**Volatility**: The standard deviation of returns. A measure of risk. Annualized volatility = daily σ × √252.

### W

**Walk-Forward Analysis**: A validation technique that repeatedly trains on expanding/rolling windows and tests on subsequent out-of-sample periods.

**Warmup Period**: The initial period during which indicators accumulate data before generating valid signals. No trading should occur during warmup.

## Source

- Based on [QuantConnect: Key Concepts — Glossary](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary)
