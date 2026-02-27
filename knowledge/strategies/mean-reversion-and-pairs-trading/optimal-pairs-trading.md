# Optimal Pairs Trading

## Overview

Models the spread between two correlated assets (GLD/SLV) as an Ornstein-Uhlenbeck (OU) mean-reverting process. Uses Maximum Likelihood Estimation to fit OU parameters and solves optimal stopping equations to derive mathematically optimal entry and exit thresholds. Retrains quarterly.

## Academic Reference

- **Paper**: "Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit" — Leung & Li (April 2015), International Journal of Theoretical and Applied Finance, Vol. 18, No. 3
- **Source**: arxiv.org/pdf/1411.5062.pdf

## Strategy Logic

### Universe Selection

Two correlated assets. Primary backtest: GLD (gold) and SLV (silver).

### Signal Generation

**Step 1 — Hedge ratio optimization**:
Test allocation ratios β ∈ [0.01, 1.00] in 0.01 increments. For each β, compute normalized portfolio: $1 of Stock A − β × $1 of Stock B. Select β* that maximizes average log-likelihood.

**Step 2 — OU parameter estimation via MLE**:
Fit Ornstein-Uhlenbeck parameters: θ (long-term mean), μ (mean reversion speed), σ (volatility).

**Step 3 — Optimal thresholds**:
- **Optimal liquidation level (b*)**: Solve F(b) = (b−c)F'(b), where c = 0.05 (transaction cost).
- **Optimal entry level (d*)**: Solve equation 4.11 using functions F(x) and G(x) involving OU parameters.

### Entry / Exit Rules

- **Enter**: When portfolio spread value ≤ d* (optimal entry level).
- **Exit**: When portfolio spread value ≥ b* (optimal liquidation level).
- **Position**: Long 1 unit of Stock A, short β* units of Stock B.

### Portfolio Construction

Full capital allocation when entering. Hedge ratio β* determines relative position sizes.

### Rebalancing Schedule

Model retraining: quarterly (first day of each quarter). Signal generation: daily.

## Key Indicators / Metrics

- Ornstein-Uhlenbeck parameters: θ*, μ*, σ*
- Optimal hedge ratio: β*
- Optimal entry threshold: d*
- Optimal liquidation threshold: b*
- 252-day rolling lookback window
- Transaction cost: c = 0.05
- Discount rate: r = 0.05

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Aug 2015 – Aug 2020 |
| Sharpe Ratio | 0.815 |
| Benchmark (SPY) Sharpe | 0.612 |
| Total Trades | 12 |
| Initial Capital | $100,000 |

Note: Few trades because "the algorithm had to wait periods of time before optimal entry and liquidation levels were reached."

## Data Requirements

- **Asset Classes**: Correlated equity pairs (e.g., GLD/SLV)
- **Resolution**: Daily closing prices
- **Lookback Period**: 252 trading days (1 year)
- **Libraries**: scipy.optimize (MLE), scipy.brentq (root finding)

## Implementation Notes

- Three Python modules: `ou_mle.py` (MLE optimization), `Model.py` (portfolio tracking), `main.py` (orchestration).
- First derivatives approximated via difference quotient with h = 1×10⁻⁴.
- scipy.brentq() for solving optimal stopping equations.
- Exception handling for "weird OU coefficients that lead to unsolveable Optimal Stopping."
- Python on QuantConnect LEAN.

## Risk Considerations

- Only 12 trades over 5 years — difficult to assess statistical significance.
- Extended waiting periods between trades — capital sits idle.
- Model instability: OU coefficients may produce unsolvable stopping equations.
- Quarterly retraining may miss regime changes between recalibration periods.
- Fixed transaction cost assumption (5%) may not reflect actual costs.
- Single pair (GLD/SLV) concentration — authors recommend adding multiple pairs (e.g., GLD-GDX).
- Fixed 5% discount rate may not reflect actual opportunity cost.

## Related Strategies

- [Pairs Trading - Copula vs Cointegration](pairs-trading-copula-vs-cointegration.md)
- [Pairs Trading with Stocks](pairs-trading-with-stocks.md)
- [Mean-Reversion Statistical Arbitrage Strategy in Stocks](mean-reversion-statistical-arbitrage-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/optimal-pairs-trading)
