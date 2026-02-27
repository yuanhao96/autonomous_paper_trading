# Improved Momentum Strategy on Commodities Futures

## Overview

A correlation-adjusted time-series momentum strategy (TSMOM-CF) that addresses three weaknesses of traditional TSMOM: discrete trading signals, standard volatility estimation, and static leverage. Based on Baltas and Kosowski (2017), it introduces continuous trend signals, Yang-Zhang volatility estimation, and dynamic leverage via a correlation factor.

## Academic Reference

- **Paper**: "Demystifying Time-Series Momentum Strategies" — Baltas, N. & Kosowski, R. (2017), SSRN Electronic Journal
- **Paper**: "Drift-Independent Volatility Estimation Based on High, Low, Open, and Close Prices" — Yang, D. & Zhang, Q. (2000), The Journal of Business, 73(3)

## Strategy Logic

### Universe Selection

20 commodity futures across CME and ICE:
- **Grains**: Soybeans, wheat, soybean meal/oil, corn, oats
- **Meats**: Live cattle, feeder cattle, lean hogs
- **Metals**: Gold, silver, platinum
- **Energies**: Brent crude, heating oil, natural gas, low sulfur gasoil
- **Softs**: Cotton, orange juice, coffee, cocoa

Daily resolution, backward-ratio normalization, open-interest mapping.

### Signal Generation

**TREND trading rule** using t-statistic of daily log-returns over 12 months:

```
t_stat = mean(log_returns) / (std(log_returns) / sqrt(n))

If t_stat > +1:  signal = +1
If -1 <= t_stat <= +1:  signal = t_stat  (continuous)
If t_stat < -1:  signal = -1
```

This continuous signal (vs. discrete +1/-1) reduces portfolio turnover and transaction costs.

### Entry / Exit Rules

Monthly rebalancing at month-end. Orders at market prices. Handles futures contract rollovers via symbol mapping events.

### Portfolio Construction

**Baltas-Kosowski weight formula**:

```
weight_i = (signal_i × σ_target × CF) / (N × σ_i)
```

Where:
- `signal_i` = trading signal (-1 to +1)
- `σ_target` = 12% portfolio volatility target
- `CF = sqrt(N / (1 + (N-1) × ρ̄))` (correlation factor)
- `N` = number of constituents
- `σ_i` = Yang-Zhang volatility of asset i

Weights clipped to [-1, +1]. Target leverage: 3x per contract.

### Rebalancing Schedule

Monthly, end-of-month.

## Key Indicators / Metrics

### Three core modifications:

1. **Continuous trading signal**: t-statistic capped to [-1, +1] (vs. discrete sign)
2. **Yang-Zhang volatility estimator** (21-day window):
   ```
   σ²_YZ = σ²_OJ + k × σ²_SD + (1-k) × σ²_RS
   ```
   Components: overnight jump volatility, standard deviation, Rogers-Satchell range estimator.
3. **Correlation factor**: Dynamic leverage based on average pairwise asset correlations (3-month window). Addresses post-2008 co-movement.

## Backtest Performance

| Metric | TSMOM-CF | Basic TSMOM | SPY |
|--------|----------|-------------|-----|
| Period | Jan 2018 – Sep 2019 | Same | Same |
| Sharpe Ratio | **0.198** | -0.746 | 0.46 |

"Significant performance improvement over the basic TSMOM" in post-GFC period.

## Data Requirements

- **Asset Classes**: Commodity futures (CME, ICE)
- **Resolution**: Daily OHLC
- **Lookback Period**: 12 months (signal), 1 month (volatility), 3 months (correlation)
- **Data**: Open, high, low, close bars required for Yang-Zhang estimator

## Implementation Notes

- Key methods: `get_trading_signal()`, `get_y_z_volatility()`, `get_correlation_factor()`.
- Position sizing accounts for contract multiplier.
- Automatic position transfer to newly mapped contracts on rollover.
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- Limited backtest duration (2018–2019).
- Transaction costs acknowledged but not fully modeled.
- Correlation window (3 months) may be too short for regime changes.
- Sensitivity to parameter choices (target volatility, estimation windows).
- Post-GFC focus period — performance in other regimes unknown.
- Assumes sufficient liquidity across all 20 commodity futures.

## Related Strategies

- [Time Series Momentum Effect](time-series-momentum-effect.md) — basic TSMOM this strategy improves upon
- [Momentum Effect in Commodities Futures](momentum-effect-in-commodities-futures.md)
- [Commodities Futures Trend Following](commodities-futures-trend-following.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/improved-momentum-strategy-on-commodities-futures)
