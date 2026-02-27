# Settlement & Margin Models

## Overview
Settlement models determine when funds from trades become available for new trading. Margin models determine how much buying power (leverage) is available. Both significantly impact strategy execution and position sizing.

## Settlement Models

### Settlement Cycles
| Asset Class | Settlement | Standard |
|------------|-----------|----------|
| US Equities | T+1 | Since May 2024 (was T+2) |
| US Options | T+1 | Since May 2024 |
| US Government Bonds | T+1 | |
| Corporate Bonds | T+1 | |
| Forex | T+2 (spot) | Can be T+0 for some |
| Futures | Daily (mark-to-market) | Margin settled daily |
| Crypto | Immediate | T+0 |
| Mutual Funds | T+1 to T+2 | |

### Immediate Settlement
- Funds available for trading instantly after a trade
- Default for margin accounts, crypto exchanges
- Simplifies position management

### Delayed Settlement
- Funds locked until settlement date
- Cash accounts subject to "free-riding" violations
- Must track settled vs unsettled cash

### Mark-to-Market (Futures)
- Daily settlement of gains/losses
- Margin account credited/debited at end of each trading day
- Variation margin calls if account drops below maintenance

## Margin / Buying Power Models

### Margin Requirements
- **Initial margin**: Required to open a position
- **Maintenance margin**: Required to keep position open
- If equity drops below maintenance, a margin call is triggered

### Leverage by Asset Class
| Asset Class | Initial Margin | Maintenance | Leverage |
|------------|---------------|-------------|----------|
| US Equities (Reg T) | 50% | 25% | 2x |
| US Day Trading (PDT) | 25% | 25% | 4x intraday |
| Forex | 2-5% | 1-2% | 20-50x |
| Futures | 5-12% | 3-8% | 8-20x |
| Crypto (spot) | 100% | 100% | 1x |
| Crypto (margin) | 10-50% | 5-25% | 2-10x |

### Margin Call Process
1. Account equity drops below maintenance margin
2. Broker issues margin call
3. Trader must deposit funds or close positions
4. If not resolved, broker liquidates positions (worst first)

### Pattern Day Trader (PDT) Rule (US)
- 4+ day trades in 5 business days with a margin account
- Requires $25,000 minimum equity
- Gets 4x intraday buying power
- 2x overnight buying power

### Short Selling Margin
- Must borrow shares (locate requirement)
- 150% margin requirement (100% proceeds + 50% additional)
- Subject to short squeeze risk
- Hard-to-borrow fees for illiquid stocks

## Portfolio Margin (Advanced)
- Risk-based margin using scenario analysis
- Typically lower margin requirements for diversified portfolios
- Available for accounts >$100,000 at most brokers
- Uses stress testing across multiple scenarios

## Implications for Algorithmic Trading
- Settlement delays affect capital recycling speed in cash accounts
- Margin models determine maximum position sizes and total exposure
- Backtests should model margin and settlement accurately to avoid overstating returns
- Strategies with high turnover are especially sensitive to settlement timing
- Futures strategies must account for daily mark-to-market cash flows
- Multi-asset strategies need asset-specific settlement and margin logic

## Key Takeaways
- Know your account type (cash vs margin) and its settlement rules
- Always maintain a buffer above maintenance margin to avoid forced liquidation
- PDT rules can limit strategy flexibility for smaller accounts
- Portfolio margin can unlock capital efficiency for diversified strategies
- Crypto's instant settlement simplifies cash management but removes leverage in spot

---

Source: Generalized from QuantConnect Reality Modeling documentation.
