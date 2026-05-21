---
name: math-engine
description: >-
  确定性数学运算引擎。当用户需要精确数值计算、表达式化简/展开/因式分解、
  符号微分与积分、或解方程时调用。把表达式交给本工具计算，**不要心算或用语言模拟计算**。
  Deterministic math engine. Invoke whenever the user needs exact arithmetic,
  expression simplify/expand/factor, symbolic differentiation or integration,
  or equation solving. Always route the expression to this tool instead of
  computing it in your head.
metadata:
  openclaw:
    emoji: "🧮"
    bins: [python3]
    install: "pip3 install --upgrade sympy"
    env: []
---

# 🧮 Math Engine

A deterministic calculation core. The model decides *that* something needs
computing and *which mode*; the actual math is done by `calc.py` (SymPy), which
returns exact results as JSON. This removes language-simulated arithmetic and
its carry/sign errors.

## When to use

Trigger this skill when the user's message contains a computable math task,
e.g.:

- Exact arithmetic — `12345 * 67890`, `2^64`, `factorial(20)`
- Simplify / expand / factor — `(a+b)^2`, `x^2 - 5x + 6`
- Symbolic calculus — `∫ x² dx`, `d/dx sin(x)·x²`
- Equation solving — `x² − 5x + 6 = 0`
- Matrices — 行列式 determinant, 矩阵乘法 multiplication, 逆矩阵 inverse,
  伴随矩阵 adjugate, 转置 transpose, 秩 rank, 行变换/简化阶梯形 RREF, eigenvalues

If the user writes an explicit force-call like `\calc{...}`, treat the contents
as the expression and call this skill unconditionally.

## How to call

```
python3 <skill_dir>/calc.py "<expression>" --mode <MODE> [--var x] [--timeout 5]
```

`MODE` is one of:

| mode        | does                                  | example expression      |
|-------------|---------------------------------------|-------------------------|
| `eval`      | exact value / 30-digit decimal        | `12345 * 67890`         |
| `simplify`  | simplify (and expand) an expression   | `(a+b)^2`               |
| `expand`    | expand only                           | `(x+1)^3`               |
| `factor`    | factor a polynomial                   | `x^2 - 5x + 6`          |
| `diff`      | differentiate / partial derivative    | `sin(x)*x^2`, `x^2*y` (with `--var`) |
| `integrate` | indefinite integral (adds `+ C`)      | `x^2`                   |
| `solve`     | solve an equation (`=` allowed)       | `x^2 - 5x + 6 = 0`      |
| `matrix`    | free-form matrix arithmetic (`* + - **`, inverse via `**-1`, `det()/trace()/transpose()`) | `[[1,2],[3,4]]*[[5,6],[7,8]]` |
| `det`       | determinant 行列式                     | `[[1,2],[3,4]]`         |
| `inv`       | inverse 逆矩阵                          | `[[1,2],[3,4]]`         |
| `adjugate`  | adjugate 伴随矩阵                       | `[[1,2],[3,4]]`         |
| `rref`      | reduced row echelon 行变换/简化阶梯形    | `[[1,2,3],[4,5,6],[7,8,10]]` |
| `transpose` | transpose 转置                          | `[[1,2,3],[4,5,6]]`     |
| `rank`      | rank 矩阵的秩                           | `[[1,2],[2,4]]`         |
| `eigenvals` | eigenvalues 特征值 (dict: value→multiplicity) | `[[2,0],[0,3]]`   |
| `auto`      | matrix literal → `matrix`; `=` → `solve`; else `simplify` | (default) |

Notes for the parser:
- Use `^` or `**` for powers; `5x` implicit multiplication is understood.
- Pass `--var` if the variable to operate on is ambiguous (defaults to x→y→z…).
- **Partial derivatives** use `diff` with `--var`:
  - `--var y` → ∂/∂y (partial w.r.t. y, others held constant)
  - `--var x,y` → mixed partial ∂²/∂x∂y (differentiate by x then y)
  - `--var x --order 2` → second derivative ∂²/∂x²
- Write matrices as `[[1,2],[3,4]]` (rows of comma-separated entries). The
  single-matrix modes (`det`, `inv`, `adjugate`, `rref`, `transpose`, `rank`,
  `eigenvals`) expect exactly one matrix; `matrix` mode accepts several joined
  by operators, e.g. `[[1,2],[3,4]] * [[5,6],[7,8]]`.

## Reading the result

`calc.py` always prints one JSON object to stdout:

```json
{"ok": true, "mode": "solve", "input": "x^2 - 5x + 6 = 0", "result": "[2, 3]", "latex": "...", "variable": "x"}
```

or, on failure:

```json
{"ok": false, "error": "...", "input": "..."}
```

Parse the JSON, then phrase the answer naturally for the user. Use `latex` when
rendering math is appropriate. If `ok` is `false`, tell the user what went wrong
(bad syntax, timeout, disallowed input) — do **not** fall back to computing it
yourself.

## Worked examples

| User asks            | Call                                              | result      |
|----------------------|---------------------------------------------------|-------------|
| 12345 × 67890        | `calc.py "12345 * 67890" --mode eval`             | `838102050` |
| expand (a+b)²        | `calc.py "(a+b)^2" --mode simplify`               | `a**2 + 2*a*b + b**2` |
| ∫ x² dx              | `calc.py "x^2" --mode integrate`                  | `C + x**3/3` |
| solve x²−5x+6=0       | `calc.py "x^2 - 5x + 6 = 0" --mode solve`         | `[2, 3]`    |
| 行列式 det A          | `calc.py "[[1,2],[3,4]]" --mode det`              | `-2`        |
| 伴随矩阵 adj A         | `calc.py "[[1,2],[3,4]]" --mode adjugate`         | `[[4, -2], [-3, 1]]` |
| 矩阵乘法 A·B          | `calc.py "[[1,2],[3,4]]*[[5,6],[7,8]]" --mode matrix` | `[[19, 22], [43, 50]]` |
| 行变换 rref           | `calc.py "[[1,2,3],[4,5,6],[7,8,10]]" --mode rref` | `[[1,0,0],[0,1,0],[0,0,1]]` |
| 偏导 ∂/∂y (x²y+sin y)  | `calc.py "x^2*y + sin(y)" --mode diff --var y`    | `x**2 + cos(y)` |
| 混合偏导 ∂²/∂x∂y       | `calc.py "x^2*y^3" --mode diff --var x,y`         | `6*x*y**2`  |
| 高阶 ∂²/∂x² (x⁴)       | `calc.py "x^4" --mode diff --var x --order 2`     | `12*x**2`   |
