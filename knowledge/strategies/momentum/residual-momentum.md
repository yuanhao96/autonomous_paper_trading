# Residual Momentum

## Overview

Stocks with greater monthly residual returns (normalized by the volatility of residual returns) tend to outperform those with less. Unlike total return momentum, residual momentum has reduced exposure to dynamic Fama-French factors, produces higher Sharpe ratios, is more robust out-of-sample, more stable throughout business cycles, and less concentrated in small-cap stocks.

## Academic Reference

- **Paper**: "Residual Momentum" — Blitz, Huij, Martens (2009), SSRN #2319861
- **Paper**: "Residual Momentum and Reversal Strategies Revisited" — Huij, Lansdorp (2017), SSRN #2929306

## Strategy Logic

### Universe Selection

1. **Coarse filter**: 400 symbols with fundamental data, ranked by highest dollar volume.
2. **Fine filter**: Top 10% by market capitalization. Only stocks with ≥3 years of historical prices.

### Signal Generation

**Step 1 — Fama-French Regression** (trailing 36 months):

```
r_t = α + β₁(Mkt_t) + β₂(SMB_t) + β₃(HML_t) + ε_t
```

Where: `r_t` = monthly stock return, `Mkt_t` = market factor, `SMB_t` = small minus big, `HML_t` = high minus low, `ε_t` = residual.

**Step 2 — Residual Momentum Score**:

```
Score = Σε / σ_ε
```

Sum of residuals over previous 12 months (excluding most recent month), divided by standard deviation of residuals.

**Price filter**: Stocks below $1 excluded (score set to None).

### Entry / Exit Rules

- **Long**: Top 10% of stocks by residual momentum score.
- **Short**: Bottom 10% of stocks by residual momentum score.
- **Exit**: At next monthly rebalance.

### Portfolio Construction

Equal-weight within long and short legs.

### Rebalancing Schedule

Monthly, at beginning of each month. 30-day holding window.

## Key Indicators / Metrics

- Fama-French three factors (Mkt, SMB, HML)
- OLS regression residuals (36-month trailing)
- Residual momentum score (12-month sum / std dev)
- Monthly returns: `(Close - Open) / Open`

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2016 – Apr 2020 |
| Initial Capital | $100,000 |
| Universe Size | 100 (adjusted from 400) |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Lookback Period**: 36 months trailing Fama-French factors + 12-month scoring window
- **External Data**: Fama-French Research Data Factors CSV
- **Fundamental Data**: Market cap, dollar volume

## Implementation Notes

- `ResidualMomentum` class manages rolling window per security with custom monthly consolidator.
- `ResidualMomentumAlphaModel` houses Fama-French data and symbol indicators.
- `TopMarketCapUniverseSelection` handles universe filtering.
- Fama-French factors loaded from external CSV via custom data streamer (`fama_french.py`).
- Files: `residual_momentum.py`, `alpha.py`, `universe.py`, `main.py`, `fama_french.py`, `research.ipynb`.

## Risk Considerations

- Underperforms during trending market regimes; outperforms during reverting regimes.
- Requires 3+ years of historical data — limits universe to established stocks.
- Fama-French factor data dependency (external source).
- Monthly return calculation `(Close - Open) / Open` may differ from standard close-to-close returns.
- Reduced trading costs vs. total return momentum, but still significant turnover.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Fama French Five Factors](../factor-investing/fama-french-five-factors.md)
- [Momentum - Short Term Reversal Strategy](momentum-short-term-reversal-strategy.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/residual-momentum)
