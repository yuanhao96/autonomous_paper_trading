# Excluded Multi-Asset Alpha Factors (Future Reference)

## Overview

These **85 alpha factors** from the WorldQuant "101 Formulaic Alphas" (Kakushadze, 2015) and extended alpha sets were excluded from the current pipeline because they require data or operations beyond single-ticker daily OHLCV. They are documented here for future reference when the pipeline supports multi-asset strategies.

**Status**: NOT COMPATIBLE with current pipeline. Requires multi-asset universe, intraday data, or external classification data.

## Academic Reference

- **Paper**: Kakushadze, Z. (2015). "101 Formulaic Alphas."
- **Journal**: *Wilmott Magazine*, 2016(84), 72–80
- **Link**: https://arxiv.org/abs/1601.00991

## Prerequisites for Implementation

To implement these alphas, the pipeline would need:

| Requirement | Current Support | Needed For |
|-------------|----------------|------------|
| Multi-asset universe (100+ stocks) | No (single ticker) | `rank()` — cross-sectional percentile ranking |
| Intraday tick/bar data | No (daily OHLCV only) | `vwap` — volume-weighted average price |
| Dollar volume / turnover data | No | `amount` — trade value per bar |
| Industry/sector classification | No | `IndNeutralize()` — industry-neutral residuals |
| Market-cap data | No | `cap` — capitalization weighting |
| Benchmark index returns | No | `benchmark_returns` — relative performance |

## Operator Reference (Multi-Asset)

| Operator | Meaning | Implementation |
|----------|---------|----------------|
| `rank(x)` | Cross-sectional percentile rank across all stocks at time t | `x.rank(axis=1, pct=True)` on a stocks×time DataFrame |
| `vwap` | Volume-weighted average price (intraday) | `sum(price * volume) / sum(volume)` per bar |
| `amount` | Dollar trading volume | `price * volume` (requires tick-level accuracy) |
| `IndNeutralize(x, ind)` | Subtract industry-group mean from x | `x - x.groupby(ind).transform('mean')` |
| `cap` | Market capitalization | External data source required |

---

## Group 1: RANK-Dependent Alphas (~50 alphas)

These alphas use `rank()` — cross-sectional percentile ranking across a universe of stocks. This is the most common incompatibility. To adapt, you would need a DataFrame of shape `(dates, stocks)` and rank across the stock axis at each date.

### Alpha#001
**Formula**: `rank(ts_argmax(SignedPower(where(returns < 0, stddev(returns, 20), close), 2), 5)) - 0.5`
**Incompatible op**: `rank()`
**Notes**: Ranks the day-of-max of a conditional volatility/price measure.

### Alpha#006
**Formula**: `-1 * correlation(rank(open), rank(volume), 10)`
**Incompatible op**: `rank()` (×2)
**Notes**: Correlation of cross-sectional ranks of open and volume. Measures how relative open price tracks relative volume across the universe.

### Alpha#007
**Formula**: `where(adv20 < volume, -1 * ts_rank(abs(delta(close, 7)), 60) * sign(delta(close, 7)), -1)`
**Incompatible op**: `adv20` (20-day average dollar volume, requires `amount`)
**Notes**: Conditional on volume exceeding average dollar volume.

### Alpha#008
**Formula**: `-1 * rank(delta(close * 0.5 + open * 0.5, 4) - delta(close * 0.5 + open * 0.5, 8))`
**Incompatible op**: `rank()`
**Notes**: Ranks acceleration of midpoint price.

### Alpha#010
**Formula**: `rank(where(ts_min(delta(close, 1), 4) > 0, delta(close, 1), where(ts_max(delta(close, 1), 4) < 0, delta(close, 1), -1 * delta(close, 1))))`
**Incompatible op**: `rank()`
**Notes**: Ranks conditional momentum/reversal signal.

### Alpha#012
**Formula**: `sign(delta(volume, 1)) * (-1 * delta(close, 1))`
**Incompatible op**: Requires `rank()` in full form from paper (simplified version shown)
**Notes**: Volume direction times negative price change.

### Alpha#013
**Formula**: `-1 * rank(covariance(rank(close), rank(volume), 5))`
**Incompatible op**: `rank()` (×3)
**Notes**: Ranks the covariance of cross-sectional ranks.

### Alpha#016
**Formula**: `-1 * rank(covariance(rank(high), rank(volume), 5))`
**Incompatible op**: `rank()` (×3)
**Notes**: Same as Alpha#013 but using high instead of close.

### Alpha#017
**Formula**: `-1 * rank(ts_rank(close, 10)) * rank(delta(delta(close, 1), 1)) * rank(ts_rank(volume / adv20, 5))`
**Incompatible op**: `rank()` (×3), `adv20`
**Notes**: Triple-ranked product of price rank, price acceleration rank, and relative volume rank.

### Alpha#022
**Formula**: `-1 * delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20))`
**Incompatible op**: `rank()`
**Notes**: Change in high-volume correlation, weighted by ranked volatility.

### Alpha#025
**Formula**: `rank(-1 * returns * adv20 * vwap * (high - close))`
**Incompatible op**: `rank()`, `adv20`, `vwap`
**Notes**: Multi-factor product ranked cross-sectionally. Triple incompatibility.

### Alpha#026
**Formula**: `-1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)`
**Incompatible op**: Requires `rank()` in full paper form
**Notes**: Max correlation of volume and high ranks.

### Alpha#030
**Formula**: `rank(sign(close - delay(close, 1)) + sign(delay(close, 1) - delay(close, 2)) + sign(delay(close, 2) - delay(close, 3))) * sum(volume, 5) / sum(volume, 20)`
**Incompatible op**: `rank()`
**Notes**: Ranked directional persistence times volume ratio.

### Alpha#032
**Formula**: `scale(sma(close, 7) - close) + 20 * scale(correlation(vwap, delay(close, 5), 230))`
**Incompatible op**: `vwap`, `scale()` (cross-sectional)
**Notes**: Mean reversion plus long-term VWAP-close correlation.

### Alpha#033
**Formula**: `rank(-1 * (1 - open / close))`
**Incompatible op**: `rank()`
**Notes**: Ranks intraday return (open-to-close).

### Alpha#035
**Formula**: `ts_rank(volume, 32) * (1 - ts_rank(close + high - low, 16)) * (1 - ts_rank(returns, 32))`
**Incompatible op**: Requires `rank()` in full paper form
**Notes**: Volume rank times inverse price-range rank times inverse return rank.

### Alpha#036
**Formula**: `2.21 * rank(correlation(close - open, delay(volume, 1), 15)) + 0.7 * rank(open - close) + 0.73 * rank(ts_rank(delay(-1 * returns, 6), 5)) + rank(abs(correlation(vwap, adv20, 6))) + 0.6 * rank(sma(close, 200) - open)`
**Incompatible op**: `rank()` (×5), `vwap`, `adv20`
**Notes**: Heavily multi-factor with multiple cross-sectional ranks.

### Alpha#037
**Formula**: `rank(correlation(delay(open - close, 1), close, 200)) + rank(open - close)`
**Incompatible op**: `rank()` (×2)
**Notes**: Ranked long-term correlation plus ranked intraday return.

### Alpha#039
**Formula**: `-1 * rank(delta(close, 7)) * (1 - rank(decay_linear(volume / adv20, 9))) * (1 + rank(sum(returns, 250)))`
**Incompatible op**: `rank()` (×3), `adv20`
**Notes**: Momentum reversal scaled by relative volume and long-term returns.

### Alpha#041
**Formula**: `power(high * low, 0.5) - vwap`
**Incompatible op**: `vwap`
**Notes**: Geometric mean of high/low minus VWAP. Measures intraday price skew.

### Alpha#042
**Formula**: `rank(vwap - close) / rank(vwap + close)`
**Incompatible op**: `rank()` (×2), `vwap` (×2)
**Notes**: Ranked VWAP-close spread ratio.

### Alpha#044
**Formula**: `-1 * correlation(high, rank(volume), 5)`
**Incompatible op**: `rank()`
**Notes**: Correlation of high with cross-sectionally ranked volume.

### Alpha#045
**Formula**: `-1 * rank(sma(delay(close, 5), 20)) * correlation(close, volume, 2) * rank(correlation(sum(close, 5), sum(close, 20), 2))`
**Incompatible op**: `rank()` (×2)
**Notes**: Triple-factor product with two cross-sectional ranks.

### Alpha#048
**Formula**: `IndNeutralize(correlation(delta(close, 1), delta(delay(close, 1), 1), 250) * delta(close, 1) / close, IndClass.subindustry) / sum(power(delta(close, 1) / delay(close, 1), 2), 250)`
**Incompatible op**: `IndNeutralize`, `IndClass`
**Notes**: Industry-neutralized serial correlation of returns. Requires sector classification.

### Alpha#054
**Formula**: `-1 * (low - close) * power(open, 5) / ((low - high) * power(close, 5))`
**Incompatible op**: Requires `rank()` in full paper form
**Notes**: Intraday price positioning ratio with polynomial scaling.

### Alpha#056
**Formula**: `-1 * rank(sum(returns, 10) / sum(sum(returns, 2), 3)) * rank(returns * cap)`
**Incompatible op**: `rank()` (×2), `cap`
**Notes**: Ranked smoothed returns times cap-weighted return rank.

### Alpha#061
**Formula**: `rank(vwap - ts_min(vwap, 16)) < rank(correlation(vwap, adv180, 17))`
**Incompatible op**: `rank()` (×2), `vwap` (×3), `adv180`
**Notes**: Comparison of VWAP channel position rank vs VWAP-volume correlation rank.

### Alpha#062
**Formula**: `rank(correlation(vwap, sum(adv20, 22), 9)) < rank(rank(open) + rank(open) < rank(close + high - low / (close * open)))`
**Incompatible op**: `rank()` (×4), `vwap`, `adv20`
**Notes**: Complex multi-rank comparison involving VWAP.

### Alpha#064
**Formula**: `rank(correlation(sum(open * 0.178 + low * 0.822, 4), sum(adv120, 4), 16)) < rank(delta(high + low + open + close, 3))`
**Incompatible op**: `rank()` (×2), `adv120`
**Notes**: Rank comparison of weighted price-volume correlation vs price change.

### Alpha#070
**Formula**: `-1 * rank(delta(vwap, 1)) * ts_rank(correlation(IndNeutralize(close, IndClass.industry), adv50, 17), 17)`
**Incompatible op**: `rank()`, `vwap`, `IndNeutralize`, `adv50`
**Notes**: Quadruple incompatibility — VWAP change rank times industry-neutral correlation.

### Alpha#073
**Formula**: `max(rank(decay_linear(delta(vwap, 4), 2)), ts_rank(decay_linear(correlation(IndNeutralize(close, IndClass.industry), adv50, 17), 11), 6)) * -1`
**Incompatible op**: `rank()`, `vwap`, `IndNeutralize`, `adv50`
**Notes**: Max of VWAP momentum rank and industry-neutral correlation rank.

### Alpha#074
**Formula**: `rank(correlation(close, sum(adv30, 37), 15)) < rank(correlation(rank(high * 0.0261661 + vwap * 0.974834), rank(volume), 11)) * -1`
**Incompatible op**: `rank()` (×4), `vwap`, `adv30`
**Notes**: Rank comparison with VWAP-weighted high and dollar volume.

### Alpha#075
**Formula**: `rank(correlation(vwap, volume, 4)) < rank(correlation(rank(low), rank(adv50), 12))`
**Incompatible op**: `rank()` (×4), `vwap`, `adv50`
**Notes**: VWAP-volume correlation rank vs low-volume correlation rank.

### Alpha#077
**Formula**: `min(rank(decay_linear(high + high - close - close + open, 20)), rank(decay_linear(correlation(high + low / 2, adv40, 3), 5))) * -1`
**Incompatible op**: `rank()` (×2), `adv40`
**Notes**: Min of two ranked decayed signals.

### Alpha#083
**Formula**: `rank(delay((high - low) / sma(close, 5), 2)) * rank(rank(volume)) / ((high - low) / sma(close, 5) / (vwap - close))`
**Incompatible op**: `rank()` (×3), `vwap`
**Notes**: Lagged normalized range times double-ranked volume, scaled by VWAP deviation.

### Alpha#087
**Formula**: `max(rank(decay_linear(delta(vwap, 1), 11)), ts_rank(decay_linear(ts_rank(correlation(IndNeutralize(low, IndClass.sector), adv81, 8), 19), 7), 6)) * -1`
**Incompatible op**: `rank()`, `vwap`, `IndNeutralize`, `adv81`
**Notes**: VWAP + industry-neutral low correlation.

### Alpha#090
**Formula**: `-1 * rank(correlation(delay(close, 1), close, 5)) * rank(close - sma(close, 20) / sma(close, 60))`
**Incompatible op**: `rank()` (×2)
**Notes**: Ranked serial correlation times ranked multi-SMA deviation.

### Alpha#091
**Formula**: `-1 * rank(close - max(close, 5)) * rank(correlation(sma(volume, 40), low, 5))`
**Incompatible op**: `rank()` (×2)
**Notes**: Distance from 5-day max ranked times ranked volume-low correlation.

### Alpha#092
**Formula**: `min(ts_rank(decay_linear(correlation(rank(close), rank(adv30), 8), 13), 5), ts_rank(decay_linear(delta(close, 1), 4), 16))`
**Incompatible op**: `rank()` (×2), `adv30`
**Notes**: Min of ranked correlation decay and return momentum decay.

### Alpha#095
**Formula**: `rank(open - ts_min(open, 12)) < ts_rank(rank(correlation(sum(high + low / 2, 19), sum(adv40, 19), 12)), 11)`
**Incompatible op**: `rank()` (×3), `adv40`
**Notes**: Open channel position rank vs ranked dollar-volume correlation.

### Alpha#099
**Formula**: `-1 * rank(covariance(rank(close), rank(volume), 5))`
**Incompatible op**: `rank()` (×3)
**Notes**: Ranked covariance of close and volume ranks. Similar to Alpha#013.

### Alpha#101
**Formula**: `(close - open) / (high - low + 0.001)`
**Incompatible op**: Requires `rank()` in full paper form
**Notes**: Intraday return normalized by range. Full formula wraps in rank().

---

## Group 2: VWAP-Dependent Alphas (~25 alphas)

These alphas use `vwap` (volume-weighted average price), which requires intraday tick or bar data not available in standard daily OHLCV feeds. Many also use `rank()` and are listed in Group 1. The alphas below are VWAP-dependent but NOT already listed above.

### Alpha#104
**Formula**: `-1 * delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20))`
**Incompatible op**: `vwap` in full form
**Notes**: Some extended formulations reference VWAP for volume normalization.

### Alpha#105
**Formula**: `-1 * correlation(rank(vwap), rank(volume), 5)`
**Incompatible op**: `rank()` (×2), `vwap`
**Notes**: Ranked VWAP-volume correlation.

### Alpha#107
**Formula**: `rank(vwap - ts_max(vwap, 15)) + rank(delta(vwap, 5))`
**Incompatible op**: `rank()` (×2), `vwap` (×3)
**Notes**: VWAP channel position plus VWAP momentum, both ranked.

### Alpha#108
**Formula**: `rank(high - ts_min(high, 2)) * rank(correlation(vwap, adv120, 6)) * -1`
**Incompatible op**: `rank()` (×2), `vwap`, `adv120`
**Notes**: High-channel rank times VWAP-volume correlation rank.

### Alpha#113
**Formula**: `-1 * rank(sum(delay(close, 5) - delay(close, 10), 2)) * rank(sum(delay(returns, 5) * vwap, 2)) * rank(sum(delay(volume * vwap, 5), 2))`
**Incompatible op**: `rank()` (×3), `vwap` (×2)
**Notes**: Triple-ranked product with VWAP-weighted returns and volume.

### Alpha#114
**Formula**: `rank(delay(high - low, 2) / sma(volume, 5)) * rank(IndNeutralize(returns, IndClass.industry)) * (vwap - close) * -1`
**Incompatible op**: `rank()` (×2), `IndNeutralize`, `vwap`
**Notes**: Range/volume rank times industry-neutral returns times VWAP deviation.

### Alpha#115
**Formula**: `rank(correlation(high * 0.9 + close * 0.1, sma(volume, 30), 10)) * rank(correlation(ts_rank(high + low / 2, 3), ts_rank(volume, 10), 7))`
**Incompatible op**: `rank()` (×2)
**Notes**: Product of two ranked correlations.

### Alpha#119
**Formula**: `rank(vwap - ts_min(vwap, 11)) * rank(correlation(vwap, adv60, 4))`
**Incompatible op**: `rank()` (×2), `vwap` (×3), `adv60`
**Notes**: VWAP channel times VWAP-volume correlation, both ranked.

### Alpha#120
**Formula**: `rank(vwap - close) * rank(vwap + close)`
**Incompatible op**: `rank()` (×2), `vwap` (×2)
**Notes**: Product of ranked VWAP deviations.

### Alpha#121
**Formula**: `rank(vwap - ts_min(vwap, 20)) * rank(correlation(vwap, adv60, 9)) * -1`
**Incompatible op**: `rank()` (×2), `vwap` (×3), `adv60`
**Notes**: Similar to Alpha#119 with different windows.

---

## Group 3: AMOUNT / Dollar Volume Dependent (~15 alphas)

These alphas use `amount` (dollar trading volume) or `adv` (average dollar volume) as primary signals. Those also listed in Group 1 or 2 are not repeated here.

### Alpha#123
**Formula**: `rank(correlation(vwap, sum(adv20, 26), 4)) < rank(correlation(rank(high * 0.9 + low * 0.1), rank(adv30), 6))`
**Incompatible op**: `rank()` (×4), `vwap`, `adv20`, `adv30`
**Notes**: Multi-dollar-volume correlation comparison.

### Alpha#124
**Formula**: `(close - vwap) / decay_linear(rank(ts_max(close, 30)), 2)`
**Incompatible op**: `rank()`, `vwap`
**Notes**: VWAP deviation scaled by ranked channel position.

### Alpha#125
**Formula**: `rank(decay_linear(correlation(vwap, adv80, 17), 4)) * rank(decay_linear(correlation(rank(high * 0.5 + low * 0.5), rank(adv60), 3), 16))`
**Incompatible op**: `rank()` (×4), `vwap`, `adv60`, `adv80`
**Notes**: Product of two ranked decayed correlation signals, heavily dependent on dollar volume.

### Alpha#130
**Formula**: `rank(decay_linear(correlation(close, volume, 10), 7)) * rank(decay_linear(delta(vwap, 3), 3))`
**Incompatible op**: `rank()` (×2), `vwap`
**Notes**: Close-volume correlation decay times VWAP momentum decay.

### Alpha#131
**Formula**: `rank(delta(vwap, 1)) * ts_rank(correlation(close, sma(volume, 50), 15), 14)`
**Incompatible op**: `rank()`, `vwap`
**Notes**: VWAP change rank times time-series-ranked correlation.

### Alpha#132
**Formula**: `sma(amount, 20) / amount`
**Incompatible op**: `amount`
**Notes**: Relative dollar volume. Simple inverse volume surge using dollar volume.

### Alpha#136
**Formula**: `rank(delta(returns, 3)) * correlation(open, volume, 10) * -1`
**Incompatible op**: `rank()`
**Notes**: Ranked return acceleration times open-volume correlation.

### Alpha#138
**Formula**: `rank(decay_linear(delta(rank(close * 0.7 + vwap * 0.3), 3), 5)) + ts_rank(decay_linear(abs(correlation(IndNeutralize(close, IndClass.industry), adv81, 9)), 9), 14) * -1`
**Incompatible op**: `rank()` (×2), `vwap`, `IndNeutralize`, `adv81`
**Notes**: Heavily multi-factor with five incompatible operations.

### Alpha#140
**Formula**: `rank(adv40) * correlation(high, volume, 10) * rank(high - close) / (stddev(close, 8) + 0.001)`
**Incompatible op**: `rank()` (×2), `adv40`
**Notes**: Dollar volume rank times high-volume correlation times close position.

### Alpha#141
**Formula**: `rank(correlation(rank(high), rank(adv15), 9)) * -1`
**Incompatible op**: `rank()` (×3), `adv15`
**Notes**: Negative ranked correlation of high rank and dollar volume rank.

### Alpha#142
**Formula**: `-1 * rank(ts_rank(close, 10)) * rank(delta(delta(close, 1), 1)) * rank(ts_rank(volume / adv20, 5))`
**Incompatible op**: `rank()` (×3), `adv20`
**Notes**: Same structure as Alpha#017. Triple-ranked acceleration signal.

### Alpha#143
**Formula**: `rank(close - delay(close, 1)) * rank(sma(volume / adv20, 20)) * -1`
**Incompatible op**: `rank()` (×2), `adv20`
**Notes**: Price change rank times relative volume rank.

### Alpha#144
**Formula**: `sum(where(close < delay(close, 1), -1 * amount * abs(close - delay(close, 1)), 0), 20) / sum(amount, 20)`
**Incompatible op**: `amount` (×2)
**Notes**: Volume-weighted average down-move magnitude using dollar volume.

---

## Group 4: IndNeutralize-Dependent (~8 alphas)

These alphas use `IndNeutralize()` to remove industry effects. Those already listed above are not repeated.

### Alpha#148
**Formula**: `rank(correlation(IndNeutralize(close, IndClass.subindustry), volume, 12)) * rank(delta(IndNeutralize(close, IndClass.subindustry), 1))`
**Incompatible op**: `rank()` (×2), `IndNeutralize` (×2)
**Notes**: Industry-neutral close-volume correlation times industry-neutral return, both ranked.

### Alpha#149
**Formula**: `IndNeutralize(correlation(close, sma(close, 20), 5), IndClass.industry) + rank(delta(close, 5))`
**Incompatible op**: `IndNeutralize`, `rank()`
**Notes**: Industry-neutral serial correlation plus ranked momentum.

### Alpha#154
**Formula**: `IndNeutralize(close / sma(close, 60) - 1, IndClass.subindustry)`
**Incompatible op**: `IndNeutralize`
**Notes**: Industry-neutral mean deviation from 60-day SMA.

### Alpha#156
**Formula**: `-1 * rank(decay_linear(delta(IndNeutralize(vwap, IndClass.industry), 3), 11)) + rank(decay_linear(correlation(IndNeutralize(close, IndClass.sector), volume, 4), 7))`
**Incompatible op**: `rank()` (×2), `IndNeutralize` (×2), `vwap`
**Notes**: VWAP industry-neutral momentum vs sector-neutral close-volume correlation.

### Alpha#157
**Formula**: `min(product(rank(rank(log(sum(ts_min(rank(-1 * rank(delta(close - 1, 5))), 2), 1)))), 1), 5) + ts_rank(delay(-1 * returns, 6), 5)`
**Incompatible op**: `rank()` (×4)
**Notes**: Deeply nested ranks with log-sum-min composition.

### Alpha#159
**Formula**: `IndNeutralize(close / sma(close, 12) - 1, IndClass.sector) - IndNeutralize(delta(close, 1) / delay(close, 1), IndClass.industry)`
**Incompatible op**: `IndNeutralize` (×2)
**Notes**: Sector-neutral mean deviation minus industry-neutral returns.

### Alpha#163
**Formula**: `rank(decay_linear(delta(IndNeutralize(close, IndClass.industry), 2), 6)) - rank(delta(IndNeutralize(vwap, IndClass.industry), 3))`
**Incompatible op**: `rank()` (×2), `IndNeutralize` (×2), `vwap`
**Notes**: Industry-neutral price vs VWAP momentum, both ranked.

### Alpha#165
**Formula**: `-1 * rank(correlation(rank(IndNeutralize(close, IndClass.sector)), rank(volume), 5))`
**Incompatible op**: `rank()` (×3), `IndNeutralize`
**Notes**: Triple-ranked sector-neutral close-volume correlation.

---

## Group 5: Benchmark / Cap Dependent (~5 alphas)

These alphas use benchmark returns or market capitalization data.

### Alpha#166
**Formula**: `rank(returns * cap) - rank(returns) * rank(cap)`
**Incompatible op**: `rank()` (×3), `cap` (×2)
**Notes**: Cap-weighted return rank interaction. Measures if cap and returns are jointly ranked differently than their individual ranks suggest.

### Alpha#170
**Formula**: `rank(close / delay(close, 1)) * rank(volume / adv20) * rank(high / close) * rank(returns * cap) * -1`
**Incompatible op**: `rank()` (×4), `adv20`, `cap`
**Notes**: Quad-ranked product with dollar volume and cap weighting.

### Alpha#171
**Formula**: `-1 * (low - close) * power(open, 5) / ((close - high) * power(close, 5)) * rank(cap)`
**Incompatible op**: `rank()`, `cap`
**Notes**: Intraday positioning ratio scaled by market cap rank.

### Alpha#172
**Formula**: `rank(sma(delta(high, 1), 15)) * rank(sma(delta(close, 1), 15)) / (rank(sma(delta(volume, 1), 15)) * cap)`
**Incompatible op**: `rank()` (×3), `cap`
**Notes**: Smoothed momentum ratio normalized by cap.

### Alpha#176
**Formula**: `correlation(rank(close - ts_min(low, 12) / (ts_max(high, 12) - ts_min(low, 12))), rank(adv20), 6) * rank(cap)`
**Incompatible op**: `rank()` (×3), `adv20`, `cap`
**Notes**: Channel position-volume correlation weighted by cap rank.

### Alpha#179
**Formula**: `rank(correlation(vwap, volume, 4)) * rank(correlation(rank(low), rank(adv50), 12)) * rank(returns * cap * benchmark_returns)`
**Incompatible op**: `rank()` (×5), `vwap`, `adv50`, `cap`, `benchmark_returns`
**Notes**: Most incompatible alpha — requires all five excluded data types.

### Alpha#181
**Formula**: `-1 * rank(delta(returns * cap, 1) / delay(returns * cap, 1))`
**Incompatible op**: `rank()`, `cap`
**Notes**: Ranked acceleration of cap-weighted returns.

### Alpha#182
**Formula**: `rank(correlation(IndNeutralize(close, IndClass.sector), volume, 18)) * rank(cap / sma(cap, 40))`
**Incompatible op**: `rank()` (×2), `IndNeutralize`, `cap` (×2)
**Notes**: Sector-neutral close-volume correlation times relative cap trend.

### Alpha#183
**Formula**: `rank(sma(returns * cap, 15)) * rank(returns * benchmark_returns) * -1`
**Incompatible op**: `rank()` (×2), `cap`, `benchmark_returns`
**Notes**: Smoothed cap-weighted return rank times benchmark-relative return rank.

### Alpha#184
**Formula**: `rank(correlation(delay(open - close, 1), close, 200)) + rank(open - close) * rank(cap)`
**Incompatible op**: `rank()` (×3), `cap`
**Notes**: Long-term serial correlation rank plus cap-weighted intraday return rank.

### Alpha#185
**Formula**: `rank(-1 * (1 - open / close)) * rank(cap)`
**Incompatible op**: `rank()` (×2), `cap`
**Notes**: Ranked intraday return times cap rank.

### Alpha#186
**Formula**: `rank(delta(returns * cap * benchmark_returns, 1))`
**Incompatible op**: `rank()`, `cap`, `benchmark_returns`
**Notes**: Ranked acceleration of benchmark-relative, cap-weighted returns.

---

## Summary Table

| Group | Incompatible Operation | Alpha Count | Alpha Numbers |
|-------|----------------------|-------------|---------------|
| 1 | `rank()` (primary) | 50 | 1, 6, 7, 8, 10, 12, 13, 16, 17, 22, 25, 26, 30, 32, 33, 35, 36, 37, 39, 41, 42, 44, 45, 48, 54, 56, 61, 62, 64, 70, 73, 74, 75, 77, 83, 87, 90, 91, 92, 95, 99, 101, 104, 105, 136, 140, 141, 142, 143, 157 |
| 2 | `vwap` (primary) | 12 | 107, 108, 113, 114, 115, 119, 120, 121, 123, 124, 125, 130, 131 |
| 3 | `amount` / `adv` | 4 | 132, 138, 144 |
| 4 | `IndNeutralize` | 8 | 148, 149, 154, 156, 159, 163, 165 |
| 5 | `cap` / benchmark | 11 | 166, 170, 171, 172, 176, 179, 181, 182, 183, 184, 185, 186 |
| **Total** | | **85** | |

**Note**: Many alphas have multiple incompatibilities (e.g., Alpha#179 requires `rank`, `vwap`, `adv`, `cap`, AND `benchmark_returns`). They are listed under their primary incompatible group only.

## Migration Path

When the pipeline supports multi-asset strategies, these alphas can be enabled by:

1. **Adding a multi-asset data layer**: Download daily OHLCV for a universe (e.g., S&P 500 constituents) into a panel DataFrame `(dates × stocks × OHLCV)`.
2. **Implementing `rank()`**: `df.rank(axis=1, pct=True)` across the stock axis at each date.
3. **Computing `vwap`**: If intraday data is available, compute from tick/bar data. Otherwise, approximate as `(high + low + close) / 3` (typical price) or `(open + high + low + close) / 4`.
4. **Computing `amount` / `adv`**: `amount = close * volume`; `adv{N} = amount.rolling(N).mean()`.
5. **Adding `IndNeutralize`**: Requires industry classification (GICS, SIC). Compute as `x - x.groupby(industry).transform('mean')`.
6. **Adding `cap`**: Requires market cap data from a fundamental data provider.
7. **Adding benchmark returns**: Download SPY or market index returns as the benchmark.

## Source

- Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72–80. https://arxiv.org/abs/1601.00991
