<div align="center">

# 🧮 MathEngineForAgents

**确定性数学运算 Skill · A Deterministic Math Skill for OpenClaw**

模型负责判断"要算什么"，真正的计算交给 `calc.py`（基于 SymPy）精确完成并返回 JSON。
告别"用语言模拟计算"带来的进位错误、符号遗漏。

The model decides *what* to compute; `calc.py` (SymPy) does the actual math
deterministically and returns exact JSON — no more language-simulated arithmetic.

[![Download ZIP](https://img.shields.io/badge/⬇_一键下载-Download_ZIP-2ea44f?style=for-the-badge)](https://github.com/Arctic-Antarctic/MathEngineForAgents/archive/refs/heads/main.zip)
&nbsp;
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

</div>

---

## ⬇️ 一键下载 / One-click download

| 方式 / Method | 命令 / Command |
|---|---|
| **下载 ZIP** | 👉 [**点此下载 main.zip**](https://github.com/Arctic-Antarctic/MathEngineForAgents/archive/refs/heads/main.zip) |
| **git clone（直接装进 skills 目录）** | `git clone https://github.com/Arctic-Antarctic/MathEngineForAgents.git ~/.openclaw/workspace/skills/math-engine` |
| **curl 一行下载并解压** | `curl -L https://github.com/Arctic-Antarctic/MathEngineForAgents/archive/refs/heads/main.zip -o math-engine.zip && unzip math-engine.zip` |

> 推荐用 `git clone` 那一行——它会直接把仓库克隆成 `~/.openclaw/workspace/skills/math-engine/`，目录名正好匹配 skill 名，省去手动改名。
> The `git clone` line is recommended: it clones straight into a folder named `math-engine`, matching the skill name so no renaming is needed.

---

## ✨ 功能 / Features

- **精确计算 Exact arithmetic** — 大数、分数、无理数，零浮点误差
- **代数 Algebra** — 化简 / 展开 / 因式分解
- **微积分 Calculus** — 求导、**偏导（高阶 + 混合）**、不定积分
- **方程 Equations** — 一元方程求解
- **线性代数 Linear algebra** — 行列式、矩阵乘法、逆矩阵、伴随矩阵、转置、秩、行变换 (RREF)、特征值
- **安全 Safe by design** — 不用 `eval()`、输入黑名单、超时与 CPU/内存上限
- **结构化输出 Structured output** — 统一返回 JSON（含 LaTeX），便于 agent 解析

---

## 🚀 安装 / Install

1. 用上面任一方式获取文件，确保最终是这个结构：
   Get the files via any method above, ending with this layout:

   ```
   ~/.openclaw/workspace/skills/math-engine/
   ├── SKILL.md
   ├── calc.py
   └── README.md
   ```

   > 若用 ZIP 下载，解压后会得到 `MathEngineForAgents-main/`，把里面的文件放进（或把文件夹重命名为）`math-engine/` 即可。
   > If you downloaded the ZIP, it extracts to `MathEngineForAgents-main/` — move its files into (or rename the folder to) `math-engine/`.

2. 安装依赖 / Install the dependency:

   ```bash
   pip3 install --upgrade sympy
   ```

3. 让 OpenClaw 重新扫描 skills（重启 gateway，或运行 doctor/refresh，视你的版本而定）。
   Have OpenClaw rescan skills (restart the gateway, or run a doctor/refresh command, depending on your version).

> ⚠️ **关于 frontmatter 字段名 / About the frontmatter keys**：不同 OpenClaw 版本对 `metadata.openclaw` 下的键名（`bins` / `install` / `emoji` 等）可能略有差异。安装前对照你本机的配置参考文档确认；某个键不被识别时，改成你版本的写法即可，`calc.py` 本身不受影响。
> The keys under `metadata.openclaw` can vary between OpenClaw versions — check your local config reference and adjust if needed. `calc.py` is unaffected.

---

## ✅ 快速自测 / Quick self-test

```bash
python3 calc.py "12345 * 67890"            --mode eval         # -> 838102050
python3 calc.py "(a+b)^2"                  --mode simplify     # -> a**2 + 2*a*b + b**2
python3 calc.py "x^2"                      --mode integrate    # -> C + x**3/3
python3 calc.py "x^2 - 5x + 6 = 0"         --mode auto         # -> [2, 3]
python3 calc.py "[[1,2],[3,4]]"            --mode adjugate     # -> [[4, -2], [-3, 1]]
python3 calc.py "x^2*y^3"                  --mode diff --var x,y  # -> 6*x*y**2
```

---

## 📖 用法 / Usage

```
python3 calc.py "<expression>" --mode <MODE> [--var x] [--order n] [--timeout 5]
```

### 模式 / Modes

| mode | 作用 / Does | 示例 / Example |
|------|------|------|
| `eval` | 精确值 / 30 位小数 | `12345 * 67890` |
| `simplify` | 化简（含展开） | `(a+b)^2` |
| `expand` | 仅展开 | `(x+1)^3` |
| `factor` | 因式分解 | `x^2 - 5x + 6` |
| `diff` | 求导 / 偏导（见下） | `sin(x)*x^2`、`x^2*y` |
| `integrate` | 不定积分（自动加 `+ C`） | `x^2` |
| `solve` | 解方程（可含 `=`） | `x^2 - 5x + 6 = 0` |
| `matrix` | 自由矩阵运算（`* + - **`、`**-1` 求逆、`det()/trace()/transpose()`） | `[[1,2],[3,4]]*[[5,6],[7,8]]` |
| `det` | 行列式 | `[[1,2],[3,4]]` |
| `inv` | 逆矩阵 | `[[1,2],[3,4]]` |
| `adjugate` | 伴随矩阵 | `[[1,2],[3,4]]` |
| `rref` | 行变换 / 简化行阶梯形 | `[[1,2,3],[4,5,6],[7,8,10]]` |
| `transpose` | 转置 | `[[1,2,3],[4,5,6]]` |
| `rank` | 秩 | `[[1,2],[2,4]]` |
| `eigenvals` | 特征值（值→重数） | `[[2,0],[0,3]]` |
| `auto` | 有 `[[`→`matrix`；有 `=`→`solve`；否则 `simplify` | （默认） |

### 偏导 / Partial derivatives

用 `diff` 配合 `--var`：

| 需求 / Need | 命令 / Command | 结果 |
|---|---|---|
| ∂/∂y（其余变量视为常量） | `--mode diff --var y` | — |
| 混合偏导 ∂²/∂x∂y | `--mode diff --var x,y` | — |
| 高阶 ∂²/∂x² | `--mode diff --var x --order 2` | — |

### 输入约定 / Input notes

- 幂用 `^` 或 `**`；支持 `5x` 这种隐式乘法。Powers via `^` or `**`; implicit multiplication like `5x` is understood.
- 矩阵写成 `[[1,2],[3,4]]`。单矩阵模式（`det`/`inv`/`adjugate`/`rref`/`transpose`/`rank`/`eigenvals`）只接受一个矩阵；`matrix` 模式可用运算符连接多个。

### 输出 / Output

始终是一个 JSON 对象 / Always one JSON object:

```json
{"ok": true, "mode": "solve", "input": "x^2 - 5x + 6 = 0", "result": "[2, 3]", "latex": "...", "variable": "x"}
```

失败时 / On failure:

```json
{"ok": false, "error": "...", "input": "..."}
```

Agent 解析 JSON 后用自然语言作答；`ok` 为 `false` 时如实告知错误（语法 / 超时 / 非法输入），**不要自己心算兜底**。

---

## 🔒 安全设计 / Security model

`calc.py` 接收任意用户字符串，因此做了多层防护 / defended in layers:

- **不使用 `eval()`** — 全程经 SymPy 的 `parse_expr` 词法解析，不执行任意 Python。No `eval()`; tokenizing parser only.
- **输入黑名单** — 拦截 `__`、`import`、`lambda`、`os.`、`subprocess` 等。Input blocklist.
- **长度上限** — 表达式超过 1000 字符直接拒绝。Length cap (1000 chars).
- **超时** — 默认 5 秒（`SIGALRM`），`--timeout` 可调。5s `SIGALRM` timeout.
- **资源上限** — `resource` 限制 CPU 时间与内存（Unix），防止 `9**9**9**9`、超大阶乘耗尽主机。CPU + memory caps (Unix).
- **输出截断** — 超长结果截断到 8000 字符。Output truncated at 8000 chars.

建议遵循 OpenClaw 最小权限原则：本 skill 只需 `python3`，不需网络或文件写入权限。
Follow least-privilege: this skill needs only `python3` — no network or file-write access.

---

## 🧩 扩展 / Extending

需要更强的符号能力时，把 `calc.py` 的后端从 SymPy 换成 Maxima、Wolfram Engine（有免费授权）等即可，`SKILL.md` 与调用约定不用动。
For stronger CAS power, swap the backend inside `calc.py` (Maxima, Wolfram Engine, …); `SKILL.md` and the calling convention stay the same.

潜在路线 / Possible additions: 梯度 gradient、Hessian、雅可比 Jacobian、定积分 definite integrals、分步初等行变换 step-by-step row operations。

---

## 📄 License

[MIT](LICENSE) © Arctic-Antarctic
