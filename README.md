# MathEngineForAgents
确定性数学运算 skill，用于 OpenClaw。模型负责判断"要算"，真正的计算交给
`calc.py`（基于 SymPy），返回精确的 JSON 结果。
A deterministic math skill for OpenClaw: the model decides *what* to compute,
`calc.py` (SymPy) does the actual math and returns exact JSON.

## 安装 / Install

1. 把整个 `math-engine/` 文件夹放到你的 OpenClaw skills 目录：
   Drop the whole `math-engine/` folder into your OpenClaw skills directory:

   ```
   ~/.openclaw/workspace/skills/math-engine/
   ├── SKILL.md
   ├── calc.py
   └── README.md
   ```

2. 安装依赖（SKILL.md 的 `install` 字段也会声明，但手动装更稳妥）：
   Install the dependency (also declared in SKILL.md's `install` field):

   ```bash
   pip3 install --upgrade sympy
   ```

3. 让 OpenClaw 重新扫描 skills（重启 gateway 或运行 `claw doctor` 视你的版本而定）。
   Have OpenClaw rescan skills (restart the gateway, or run a doctor/refresh
   command depending on your version).

> ⚠️ **关于 frontmatter 字段名**：不同 OpenClaw 版本对 `metadata.openclaw`
> 下的键名（`bins` / `install` / `emoji` 等）可能略有差异。安装前请对照你本机
> 的配置参考文档确认；如果某个键不被识别，调整成你版本的写法即可，`calc.py`
> 本身不受影响。
> The exact keys under `metadata.openclaw` can vary between OpenClaw versions —
> check your local config reference and adjust if needed. `calc.py` is
> unaffected by the frontmatter format.

## 快速自测 / Quick self-test

```bash
python3 calc.py "12345 * 67890" --mode eval        # -> 838102050
python3 calc.py "(a+b)^2" --mode simplify          # -> a**2 + 2*a*b + b**2
python3 calc.py "x^2" --mode integrate             # -> C + x**3/3
python3 calc.py "x^2 - 5x + 6 = 0" --mode auto     # -> [2, 3]
```

## 安全设计 / Security model

`calc.py` 接收任意用户字符串，因此做了多层防护：
`calc.py` receives arbitrary user strings, so it is defended in layers:

- **不使用 `eval()`** — 全程经 SymPy 的 `parse_expr` 词法解析，不执行任意 Python。
  No `eval()`; parsing goes through SymPy's tokenizing `parse_expr`.
- **输入黑名单** — 拦截 `__`、`import`、`lambda`、`os.`、`subprocess` 等危险标记。
  Input blocklist for `__`, `import`, `lambda`, `os.`, `subprocess`, etc.
- **长度上限** — 表达式超过 1000 字符直接拒绝。
  Rejects expressions over 1000 chars.
- **超时** — 默认 5 秒（`SIGALRM`），可用 `--timeout` 调整。
  5-second `SIGALRM` timeout by default; tune with `--timeout`.
- **资源上限** — 通过 `resource` 限制 CPU 时间与内存（Unix），防止
  `9**9**9**9`、超大阶乘等耗尽主机。
  CPU + memory caps via `resource` (Unix) so pathological inputs can't exhaust
  the host.
- **输出截断** — 超长结果截断到 8000 字符。
  Output truncated at 8000 chars.

即便如此，仍建议遵循 OpenClaw 一贯的最小权限原则：本 skill 只需要 `python3`，
不需要网络或文件写入权限。
Still, follow OpenClaw's least-privilege practice: this skill needs only
`python3` — no network or file-write permissions.

## 扩展 / Extending

需要更强的符号能力时，把 `calc.py` 里的后端从 SymPy 换成 Maxima、
Wolfram Engine（有免费授权）等即可，SKILL.md 与调用约定不用动。
For stronger CAS power, swap the backend inside `calc.py` (Maxima, Wolfram
Engine, …); SKILL.md and the calling convention stay the same.
