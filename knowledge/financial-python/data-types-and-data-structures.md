# Data Types and Data Structures

## Overview
First article in the Introduction to Financial Python series by QuantConnect. Covers fundamental Python data types (strings, integers, floats, booleans) and data structures (lists, tuples, sets, dictionaries), along with basic mathematical operations and string manipulation methods.

## Key Concepts

### Data Types

**Strings**: Text values enclosed in single or double quotes.
```python
my_string1 = 'Welcome to'
my_string2 = "QuantConnect"
```
- Can be converted to numeric types via `int()` and `float()`

**Integers**: Whole numbers without decimal values.
```python
my_int = 10
type(my_int)  # <type 'int'>
```

**Floats**: Real numbers with decimal points.
```python
my_float = 1.0
type(my_float)  # <type 'float'>
```
- Note: `1` is an int, `1.0` is a float
- Convert with `float()`, `int()`, `str()`

**Booleans**: Binary values `True` or `False`.
```python
my_bool = False
type(my_bool)  # <type 'bool'>
```

### Mathematical Operations

```python
print(f"Addition {1+1}")      # 2
print(f"Subtraction {5-2}")   # 3
print(f"Multiplication {2*3}") # 6
print(f"Division {10/2}")     # 5
print(f"Exponent {2**3}")     # 8
```

## Data Structures

### Lists
Ordered, mutable collections using square brackets.

```python
my_list = ['Quant', 'Connect', 1, 2, 3]
```

- **Zero-based indexing**: `my_list[0]` returns `'Quant'`
- **Slicing**: `my_list[1:3]` returns elements at indices 1 and 2
- **Append**: `my_list.append('new')` adds element to end
- **Remove**: `my_list.remove('Quant')` removes first occurrence
- **Length**: `len(my_list)` returns number of elements

### Tuples
Ordered, immutable sequences using parentheses.

```python
my_tuple = ('Welcome', 'to', 'QuantConnect')
```

- Supports slicing like lists
- Cannot be modified after creation (no append, remove, etc.)

### Sets
Unordered collections with unique elements.

```python
stock_list = ['AAPL', 'GOOG', 'AAPL', 'IBM']
stock_set = set(stock_list)  # {'AAPL', 'GOOG', 'IBM'}
```

- Automatically removes duplicates
- No indexing (unordered)

### Dictionaries
Unordered key-value pairs using curly braces.

```python
my_dic = {'AAPL': 'Apple', 'FB': 'FaceBook'}
my_dic['GOOG'] = 'Alphabet Company'  # add new entry
my_dic.keys()  # returns all keys
```

- Keys must be unique
- Access values via keys: `my_dic['AAPL']`

## String Operations

### Slicing
```python
my_str = "Welcome to QuantConnect"
my_str[8:]  # extracts from index 8 onward
```

### Methods
- **`count()`**: Count character occurrences
- **`find()`**: Return index position of a character
- **`replace()`**: Substitute characters — `'string'.replace('a','e')`
- **`split()`**: Divide string by delimiter, returns list

### String Formatting
```python
# .format() method
'Hour: {}, Minute: {}'.format(9, 43)

# Percent notation
'pi is %f' % 3.14    # %s=string, %f=float, %d=integer

# F-strings (recommended)
import numpy as np
f'pi is {np.pi}'
```

## Financial Application Notes

- Data types are foundational for handling financial data (prices as floats, tickers as strings, etc.)
- Lists are commonly used for storing collections of ticker symbols
- Dictionaries map ticker symbols to company names, prices, or other attributes
- Sets are useful for deduplicating ticker lists

## Summary

Covers the building blocks of Python programming: four basic data types (string, int, float, bool), four data structures (list, tuple, set, dict), mathematical operations, and string manipulation. These are prerequisites for all subsequent financial Python topics.

## Source

- [QuantConnect: Data Types and Data Structures](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/data-types-and-data-structures)
