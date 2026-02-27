# Pandas: Resampling and DataFrame

## Overview

Fifth article in the Introduction to Financial Python series by QuantConnect. Covers fetching financial data via QuantBook, time series resampling (changing frequency), Series operations (diff, pct_change, fillna, dropna), DataFrame creation and manipulation, data validation, and DataFrame concatenation.

## Key Concepts

### Fetching Financial Data

Using QuantConnect's QuantBook API to retrieve historical stock data:

```python
from datetime import datetime
qb = QuantBook()
symbol = qb.AddEquity("AAPL").Symbol
aapl_table = qb.History(symbol, datetime(1998, 1, 1), qb.Time, Resolution.Daily).loc[symbol]
aapl = aapl_table['close']['2017']
```

Access by date slicing: `series['2017-01-03']` or range: `series['2017-01':'2017-06']`

### Resampling Time Series

`series.resample(freq)` groups time series data into regular intervals.

**Common frequency codes**:

| Code | Frequency | Example |
|------|-----------|---------|
| `'D'` | Daily | `resample('D')` |
| `'W'` | Weekly | `resample('W')` |
| `'M'` | Monthly | `resample('M')` |
| `'nD'` | Every n days | `resample('3D')` |
| `'nW'` | Every n weeks | `resample('2W')` |

**Aggregation methods**:
```python
by_month = aapl.resample('M').mean()       # monthly average
std      = aapl.resample('W').std()         # weekly standard deviation
max_val  = aapl.resample('W').max()         # weekly maximum
min_val  = aapl.resample('W').min()         # weekly minimum
```

**Custom aggregation with lambda**:
```python
# Last trading day price each month
last_day = aapl.resample('M').agg(lambda x: x[-1])

# Monthly return
monthly_return = aapl.resample('M').agg(lambda x: x[-1] / x[1] - 1)
```

### Series Operations

**Statistical methods on resampled data**:
```python
monthly_return.mean()
monthly_return.std()
monthly_return.max()
```

**Difference and percentage change**:
```python
last_day.diff()         # consecutive element differences
last_day.pct_change()   # percentage change between elements
```

**Handling missing values**:
```python
daily_return.fillna(0)                    # replace NaN with 0
daily_return.fillna(method='bfill')       # backward fill
daily_return.dropna()                     # remove rows with NaN
```

### DataFrame Fundamentals

A DataFrame is a two-dimensional labeled data structure — like a spreadsheet or SQL table.

**Creation from dictionary**:
```python
dict = {
    'AAPL': [143.5, 144.09, 142.73, 144.18, 143.77],
    'GOOG': [898.7, 911.71, 906.69, 918.59, 926.99],
    'IBM':  [155.58, 153.67, 152.36, 152.94, 153.49]
}
dates = pd.date_range('2017-07-03', periods=5, freq='D')
df = pd.DataFrame(dict, index=dates)
```

**Column access**:
```python
df.close              # dot notation
df['volume']          # bracket notation
df[['open', 'high', 'low', 'close']]  # multiple columns
```

**Row and column selection with loc**:
```python
df.loc['2016-03':'2016-06', ['open', 'high', 'low', 'close']]
```

**Conditional filtering**:
```python
above = df[df.close > np.mean(df.close)]
```

### Adding Columns

```python
df['rate_return'] = df.close.pct_change()
```

### Data Validation

**Detecting missing values**:
```python
missing = df.isnull()
missing.describe()
missing[missing.rate_return == True]
```

**Handling missing data**:
```python
drop = df.dropna()    # remove rows with any NaN
fill = df.fillna(0)   # replace NaN with 0
```

### DataFrame Concatenation

**Merging Series into a DataFrame (column-wise, axis=1)**:
```python
s1 = pd.Series([143.5, 144.09, 142.73, 144.18, 143.77], name='AAPL')
s2 = pd.Series([898.7, 911.71, 906.69, 918.59, 926.99], name='GOOG')
data_frame = pd.concat([s1, s2], axis=1)
```

**Combining DataFrames by columns**:
```python
concat = pd.concat([aapl_bar, log_price], axis=1)
```

**Inner join (intersection only)**:
```python
concat = pd.concat([aapl_bar, df_volume], axis=1, join='inner')
```

**Appending rows (axis=0)**:
```python
concat = pd.concat([aapl_bar, df_2017], axis=0)
```

**Note**: Matching column names merge data into the same column; different names create separate columns.

All methods that apply to a Series can also be applied to a DataFrame.

## Financial Application Notes

- Resampling converts tick/daily data to weekly/monthly for strategy analysis
- `pct_change()` is the standard way to compute returns from price series
- `fillna()` and `dropna()` are essential for handling gaps in financial data (weekends, holidays)
- DataFrames represent multi-asset portfolios (columns = tickers, rows = dates)
- `pd.concat()` combines data from multiple sources (e.g., price + volume + fundamentals)
- QuantBook API provides the data pipeline for QuantConnect research notebooks

## Summary

Covers the full Pandas workflow for financial data: fetching data via QuantBook, resampling time series to different frequencies, computing returns and differences, creating and manipulating DataFrames, validating and cleaning data, and concatenating multiple data sources. These operations form the foundation of all quantitative analysis in Python.

## Source

- [QuantConnect: Pandas Resampling and DataFrame](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/pandas-resampling-and-dataframe)
