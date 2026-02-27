# Functions and Object-Oriented Programming

## Overview

Third article in the Introduction to Financial Python series by QuantConnect. Covers user-defined functions, built-in functions (range, len, map, sorted), lambda expressions, and object-oriented programming (classes, instances, attributes, methods, inheritance). Demonstrates how these concepts apply to QuantConnect algorithm development.

## Key Concepts

### User-Defined Functions

Functions are reusable blocks of code defined with the `def` keyword.

**Function with parameters and return value**:
```python
def product(x, y):
    return x * y

print(product(2, 3))    # 6
print(product(5, 10))   # 50
```

**Function without parameters**:
```python
def say_hi():
    print('Welcome to QuantConnect')

say_hi()
# Output: Welcome to QuantConnect
```

## Built-in Functions

### range()

Creates an arithmetic sequence. Arguments must be integers; step defaults to 1.

```python
print(range(10))        # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
print(range(1, 11))     # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
print(range(1, 11, 2))  # [1, 3, 5, 7, 9]
```

### len()

Returns the length of sequences or collections.

```python
tickers = ['AAPL', 'GOOGL', 'IBM', 'FB', 'F', 'V', 'G', 'GE']
print(f"The number of tickers is {len(tickers)}")
# Output: The number of tickers is 8

for k in range(len(tickers)):
    print(f"{k + 1} {tickers[k]}")
```

### map()

Applies a function to every item in a sequence.

```python
tickers = ['AAPL', 'GOOG', 'IBM', 'FB', 'F', 'V', 'G', 'GE']
print(list(map(len, tickers)))
# Output: [4, 5, 3, 2, 1, 1, 1, 2]
```

### sorted()

Returns a new sorted list from an iterable.

```python
sorted([5, 2, 3, 4, 1])
# Output: [1, 2, 3, 4, 5]
```

**With key parameter** (sort by second tuple element):
```python
price_list = [('AAPL', 144.09), ('GOOGL', 911.71), ('MSFT', 69), ('FB', 150), ('WMT', 75.32)]
sorted(price_list, key=lambda x: x[1])
# Output: [('MSFT', 69), ('WMT', 75.32), ('AAPL', 144.09), ('FB', 150), ('GOOGL', 911.71)]
```

**With reverse parameter** (descending):
```python
sorted(price_list, key=lambda x: x[1], reverse=True)
# Output: [('GOOGL', 911.71), ('FB', 150), ('AAPL', 144.09), ('WMT', 75.32), ('MSFT', 69)]
```

### list.sort() vs sorted()

`list.sort()` modifies the list in-place and returns `None`. `sorted()` returns a new list.

```python
price_list.sort(key=lambda x: x[1])
print(price_list)  # sorted in-place
```

## Lambda Expressions

Anonymous, single-expression functions created with the `lambda` keyword.

```python
# Square numbers 0-9
print(list(map(lambda x: x**2, range(10))))
# Output: [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# Element-wise addition of two lists
print(list(map(lambda x, y: x + y, [1, 2, 3, 4, 5], [5, 4, 3, 2, 1])))
# Output: [6, 6, 6, 6, 6]
```

Commonly used with `map()`, `sorted()`, and `filter()` for concise data transformations.

## Object-Oriented Programming

### Core Concepts

In Python, everything is an object — an instance of some class. Objects contain:
- **Attributes**: Data stored inside the object
- **Methods**: Functions associated with the object

### Defining a Class

```python
class Stock:
    def __init__(self, ticker, open, close, volume):
        self.ticker = ticker
        self.open = open
        self.close = close
        self.volume = volume
        self.rate_return = float(close) / open - 1

    def update(self, open, close):
        self.open = open
        self.close = close
        self.rate_return = float(self.close) / self.open - 1

    def print_return(self):
        print(self.rate_return)
```

**Key components**:
- `__init__`: Constructor method, called when creating a new instance
- `self`: Reference to the instance itself (always the first parameter)
- Attributes: `ticker`, `open`, `close`, `volume`, `rate_return`
- Methods: `update()`, `print_return()`

### Creating and Using Instances

```python
apple  = Stock('AAPL', 143.69, 144.09, 20109375)
google = Stock('GOOGL', 898.7, 911.7, 1561616)

# Access attributes
apple.ticker          # 'AAPL'

# Call methods
google.print_return() # 0.0144653388227

# Update and recalculate
google.update(912.8, 913.4)
google.print_return() # 0.000657318141981
```

### Dynamic Attributes

Attributes can be added to instances at runtime:

```python
apple.ceo = 'Tim Cook'
apple.ceo  # 'Tim Cook'
```

### Inspecting Objects with dir()

```python
dir(apple)
# ['__doc__', '__init__', '__module__', 'ceo', 'close', 'open',
#  'print_return', 'rate_return', 'ticker', 'update', 'volume']
```

### Inheritance

Child classes inherit attributes and methods from parent classes.

```python
class Child(Stock):
    def __init__(self, name):
        self.name = name

aa = Child('AA')
print(aa.name)       # 'AA'

# Inherited methods from Stock work:
aa.update(100, 102)
print(aa.open)       # 100
print(aa.close)      # 102
aa.print_return()    # 0.02
```

## Financial Application Notes

- QuantConnect algorithms are defined as classes inheriting from `QCAlgorithm`
- The algorithm class inherits all QC API methods through inheritance
- Functions encapsulate reusable trading logic (signal generation, position sizing)
- Lambda expressions and `sorted()` are commonly used for ranking stocks by criteria
- The `Stock` class example demonstrates a pattern for tracking position data

## Summary

Covers user-defined functions with `def`, essential built-in functions (`range`, `len`, `map`, `sorted`), lambda expressions for anonymous functions, and object-oriented programming (class definition, `__init__`, `self`, attributes, methods, inheritance). These are the building blocks for writing QuantConnect algorithms, which are themselves classes inheriting from `QCAlgorithm`.

## Source

- [QuantConnect: Functions and Object-Oriented Programming](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/functions-and-objective-oriented-programming)
