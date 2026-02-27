# Linear Algebra

## Overview

Eleventh article in the Introduction to Financial Python series by QuantConnect. Covers vectors, scalar products, matrices, matrix multiplication, inverse matrices, and solving linear equations with NumPy. Demonstrates applications to portfolio variance computation and arbitrage detection.

## Key Concepts

### Vectors

A vector represents a point via coordinates in n-dimensional space:

```
v = (x₁, x₂, ..., xₙ)
```

#### Scalar (Dot) Product

For two vectors x and y:

```
x^T · y = x₁y₁ + x₂y₂ + ... + xₙyₙ
```

### Matrices

Multiple vectors combined into a rectangular array. Element `x_{ij}` references row i, column j.

**Creating matrices with NumPy**:
```python
import numpy as np
a = np.array([1, 2, 3])
b = np.array([2, 2, 2])
c = np.array([3, 1, 1])
matrix = np.column_stack((a, b, c))
# Output: [[1 2 3]
#          [2 2 1]
#          [3 2 1]]
```

**Square matrices** have equal rows and columns.

### Matrix Multiplication

Each entry `x_{ij}` of the product X = AB equals the scalar product of row i from A with column j from B.

**Dimension rule**: (m × n) × (n × p) = (m × p) — inner dimensions must match.

```python
A = np.array([[2, 3], [4, 2], [2, 2]])
B = np.array([[4, 2], [4, 6]])
x = np.dot(A, B)
# Output: [[20 22]
#          [24 20]
#          [16 16]]
```

**Important**: Matrix multiplication is **not commutative** — AB ≠ BA in general.

### Identity Matrix

The identity matrix `I_n` has ones on the diagonal and zeros elsewhere. For any matrix A:

```
AI = IA = A
```

### Inverse Matrices

For an invertible matrix A, its inverse A⁻¹ satisfies:

```
AA⁻¹ = A⁻¹A = I
```

```python
inverse = np.linalg.inv(matrix)
print(np.dot(matrix, inverse))  # Returns identity matrix
```

**Limitations**:
- Rectangular matrices have no inverse
- Some square matrices are **singular** (non-invertible) — determinant = 0

### Solving Linear Equations

A system `Ax = b` can be solved directly:

```python
A = np.array([[2, 1, -1], [-3, -1, 2], [-2, 1, 2]])
b = np.array([[8], [-11], [-3]])
solution = np.linalg.solve(A, b)
# Output: [[2.] [3.] [-1.]]
```

**Best practice**: Use `np.linalg.solve()` (LU decomposition) rather than computing A⁻¹ and multiplying. It is more numerically stable and efficient.

## Financial Application Notes

- **Portfolio variance**: `Var(R_p) = w^T Σ w` where Σ is the covariance matrix — a direct matrix multiplication
- **Solving for portfolio weights**: Mean-variance optimization reduces to solving linear systems
- **Arbitrage detection**: Finding arbitrage opportunities by solving systems of linear equations
- **Factor models**: Fama-French regression uses matrix notation: `R = Xβ + ε`
- **Covariance matrices** are the central object in risk management and portfolio construction

## Summary

Covers the essential linear algebra toolkit for quantitative finance: vectors and scalar products, matrix creation and multiplication (non-commutative), inverse matrices, and solving linear systems with `np.linalg.solve()`. These operations underpin portfolio optimization, risk computation, and factor model estimation.

## Source

- [QuantConnect: Linear Algebra](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/linear-algebra)
