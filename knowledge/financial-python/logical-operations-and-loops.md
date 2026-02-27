# Logical Operations and Loops

## Overview

Second article in the Introduction to Financial Python series by QuantConnect. Covers comparison operators, logical operators (AND, OR, NOT), conditional statements (if/elif/else), loop structures (while, for), and list comprehensions.

## Key Concepts

### Comparison Operators

```python
print(1 == 0)   # False — equality
print(1 == 1)   # True
print(1 != 0)   # True  — not equal
print(5 >= 5)   # True  — greater than or equal
print(5 >= 6)   # False
```

Standard comparison operators: `==`, `!=`, `>`, `<`, `>=`, `<=`

### Logical Operators

| Operator | Description | Rule |
|----------|-------------|------|
| `and` | Logical AND | True only if both conditions are True |
| `or` | Logical OR | False only if both conditions are False |
| `not` | Logical NOT | Reverses the boolean value |

```python
print(2 > 1 and 3 > 2)   # True — both true
print(2 > 1 and 3 < 2)   # False — second is false
print(2 > 1 or 3 < 2)    # True — first is true
print(2 < 1 and 3 < 2)   # False — both false
```

**Complex compound statements** — use parentheses to control evaluation order:
```python
print((3 > 2 or 1 < 3) and (1 != 3 and 4 > 3) and not (3 < 2 or 1 < 3 and (1 != 3 and 4 > 3)))
```

## Conditional Statements

### if / elif / else

```python
if condition1:
    # executes if condition1 is True
elif condition2:
    # executes if condition1 is False and condition2 is True
else:
    # executes if none of the above are True
```

**Simple example**:
```python
i = 0
if i == 0:
    print('i == 0 is True')
```

**Complex example with logical operators**:
```python
p = 1 > 0
q = 2 > 3
if p and q:
    print('p and q is true')
elif p and not q:
    print('q is false')
elif q and not p:
    print('p is false')
else:
    print('None of p and q is true')
# Output: q is false
```

## Loop Structures

### While Loop

Repeats until the condition becomes False. Must update a variable to avoid infinite loops.

```python
i = 0
while i < 5:
    print(i)
    i += 1
# Output: 0, 1, 2, 3, 4
```

### For Loop

Iterates over a sequence and terminates when complete.

```python
for x in [1, 2, 3, 4, 5]:
    print(x)
```

**For loop with conditional filtering**:
```python
stocks = ['AAPL', 'GOOG', 'IBM', 'FB', 'F', 'V', 'G', 'GE']
selected = ['AAPL', 'IBM']
new_list = []
for stock in stocks:
    if stock not in selected:
        new_list.append(stock)
print(new_list)
# Output: ['GOOG', 'FB', 'F', 'V', 'G', 'GE']
```

### break Statement

Terminates the loop immediately.

```python
stocks = ['AAPL', 'GOOG', 'IBM', 'FB', 'F', 'V', 'G', 'GE']
for stock in stocks:
    print(stock)
    if stock == 'FB':
        break
# Output: AAPL, GOOG, IBM, FB
```

### continue Statement

Skips the current iteration and moves to the next.

```python
stocks = ['AAPL', 'GOOG', 'IBM', 'FB', 'F', 'V', 'G', 'GE']
for stock in stocks:
    if stock == 'FB':
        continue
    print(stock)
# Output: AAPL, GOOG, IBM, F, V, G, GE (FB skipped)
```

## List Comprehension

Concise syntax for creating lists using inline for loops.

**Basic**:
```python
foo = [1, 2, 3, 4, 5]
squares = [x**2 for x in foo]
print(squares)
# Output: [1, 4, 9, 16, 25]
```

**With conditional**:
```python
stocks = ['AAPL', 'GOOG', 'IBM', 'FB', 'F', 'V', 'G', 'GE']
selected = ['AAPL', 'IBM']
new_list = [x for x in stocks if x not in selected]
print(new_list)
# Output: ['GOOG', 'FB', 'F', 'V', 'G', 'GE']
```

**Multiple iterations (nested loops)**:
```python
print([(x, y) for x in [1, 2, 3] for y in [3, 1, 4] if x != y])

print([f'{x} vs {y}' for x in ['AAPL', 'GOOG', 'IBM', 'FB']
                      for y in ['F', 'V', 'G', 'GE'] if x != y])
```

## Financial Application Notes

- Conditional logic is essential for trading signals (if price > threshold, buy)
- For loops iterate over stock universes for screening
- List comprehensions are idiomatic Python for filtering stock lists
- Break/continue control flow in search operations (e.g., stop searching when a condition is met)

## Summary

Covers logical operations (comparison and boolean operators), conditional statements (if/elif/else), loop structures (while and for loops with break/continue), and list comprehensions as a concise alternative to loops. These control flow tools are fundamental to implementing trading algorithms.

## Source

- [QuantConnect: Logical Operations and Loops](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/logical-operations-and-loops)
