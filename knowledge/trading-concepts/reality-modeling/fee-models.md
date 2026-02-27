# Fee Models

## Overview

Fee models calculate the transaction costs associated with each order. These costs directly reduce strategy returns and can be the difference between a profitable and unprofitable strategy. Accurate fee modeling during backtesting is essential to avoid overstating performance.

## Types of Fee Structures

| Fee Type | Description | Common For |
|----------|-------------|------------|
| Per-share | Fixed cost per share traded | US equities (e.g., $0.005/share) |
| Per-trade | Flat fee per order | Discount brokers (e.g., $4.95/trade) |
| Percentage | Percentage of trade value | Crypto, some forex (e.g., 0.1%) |
| Tiered | Rate decreases with volume | High-volume traders |
| Maker/Taker | Different rates for providing/taking liquidity | Crypto exchanges, ECNs |

## Common Fee Schedules

- **US Equities (Interactive Brokers):** $0.005/share, min $1.00, max 0.5% of trade value
- **US Options:** $0.65-$1.00 per contract
- **Forex:** Typically spread-based (no explicit commission) or $2-5 per 100K lot
- **Crypto:** 0.1-0.25% maker, 0.15-0.50% taker
- **Futures:** $0.85-$2.25 per contract per side

## Regulatory Fees (US Markets)

Beyond brokerage commissions, US-listed securities are subject to regulatory fees that are often overlooked in backtests:

- **SEC fee:** ~$22.90 per million on sells (updated periodically)
- **FINRA TAF:** $0.000166 per share on sells (capped at $8.30 per trade)
- **Exchange fees:** Vary by exchange and order routing; some exchanges offer rebates for adding liquidity

These fees are small individually but compound over many trades, especially for high-frequency strategies.

## Impact on Strategy Performance

- **High-frequency strategies:** Fees dominate P&L. Strategies often depend on maker rebates to remain profitable. Even a fraction of a cent per share matters at scale.
- **Medium-frequency (daily/weekly):** Fees are significant but manageable. Strategy must generate enough alpha to cover round-trip costs.
- **Low-frequency (monthly+):** Fees are usually negligible relative to expected returns per trade.

### Break-Even Analysis

A useful exercise is calculating the minimum return per trade needed to cover fees:

```
Min Return = (Entry Fee + Exit Fee) / Trade Value
```

For example, a $10,000 equity trade at $0.005/share (500 shares at $20) costs roughly $5.00 round-trip, requiring a 0.05% return just to break even on fees alone.

## Custom Fee Modeling

When building a custom fee model, consider the following inputs:

- **Security price:** Some fee structures depend on the price of the security
- **Order quantity:** Per-share and tiered models depend on the number of shares/contracts
- **Order type:** Market vs. limit orders may incur different fees (maker/taker)
- **Order direction:** Sells often incur additional regulatory fees
- **Fee currency:** Fees can be in the account currency or the security's denominated currency

### Implementation Considerations

- Model minimum fees and fee caps (e.g., IB has a $1.00 minimum per order)
- Handle fractional share fees for crypto or fractional equity trading
- Track cumulative volume for tiered fee schedules that reset monthly
- Include currency conversion costs when trading foreign-listed securities

## Common Pitfalls

1. **Ignoring fees entirely:** Leads to unrealistically profitable backtests
2. **Using flat estimates:** A fixed $10/trade ignores variation across asset classes
3. **Forgetting regulatory fees:** Small but cumulative, especially on sell-heavy strategies
4. **Not accounting for fee changes:** Brokerage fee schedules change over time; historical accuracy matters
5. **Overlooking minimum fees:** Small orders can have disproportionately high costs when minimums apply

---

Source: Generalized from QuantConnect Reality Modeling documentation.
