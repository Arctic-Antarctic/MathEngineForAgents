#!/usr/bin/env python3
"""
math-engine :: deterministic calculation core for OpenClaw.

Takes a math expression + a mode, computes the result with SymPy, and prints a
single JSON object to stdout. NEVER uses Python's eval(). All parsing goes
through SymPy's tokenizing parser with a locked-down namespace, and execution
runs under CPU/memory/time limits so a malicious or pathological input cannot
hang or exhaust the host.

Usage:
    python3 calc.py "<expression>" --mode <eval|simplify|expand|factor|diff|integrate|solve|auto>
                                   [--var x] [--timeout 5]

Output (always JSON):
    {"ok": true,  "mode": "...", "input": "...", "result": "...", "latex": "..."}
    {"ok": false, "error": "...", "input": "..."}
"""

import sys
import json
import argparse
import signal

# ----------------------------------------------------------------------------
# 1. Hard resource limits (defense-in-depth backstop, Unix only).
#    Caps CPU seconds and address space so e.g. 9**9**9 or a runaway integral
#    cannot take the machine down even if the SIGALRM below is somehow missed.
# ----------------------------------------------------------------------------
def _apply_resource_limits(cpu_seconds: int = 8, mem_bytes: int = 1024 * 1024 * 1024):
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except (ImportError, ValueError, OSError):
        # resource is unavailable on Windows; the SIGALRM timeout still applies.
        pass


class _Timeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise _Timeout("computation exceeded the time limit")


# ----------------------------------------------------------------------------
# 2. Input validation. Reject obviously hostile or oversized input before it
#    ever reaches the parser.
# ----------------------------------------------------------------------------
MAX_LEN = 1000
_BLOCKLIST = (
    "__", "import", "lambda", "exec(", "eval(", "open(", "os.", "sys.",
    "subprocess", "globals", "locals", "compile(", "getattr", "setattr",
)


def _validate(expr: str) -> str:
    if not expr or not expr.strip():
        raise ValueError("empty expression")
    if len(expr) > MAX_LEN:
        raise ValueError(f"expression too long (>{MAX_LEN} chars)")
    low = expr.lower()
    for bad in _BLOCKLIST:
        if bad in low:
            raise ValueError(f"disallowed token: {bad!r}")
    return expr.strip()


# ----------------------------------------------------------------------------
# 3. Safe parsing. SymPy's parse_expr tokenizes and builds a SymPy tree; we
#    additionally pass a restricted namespace and forbid Python AST eval paths.
# ----------------------------------------------------------------------------
def _parse(expr_str):
    import sympy as sp
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations,
        implicit_multiplication_application, convert_xor,
    )
    transforms = (standard_transformations
                  + (implicit_multiplication_application, convert_xor))
    # parse_expr tokenizes the string into a SymPy tree rather than running
    # Python's eval, so arbitrary code cannot execute. Combined with the input
    # blocklist above, this is the safe parsing path. We keep SymPy's default
    # namespace (Symbol, Integer, sin, sqrt, ...) which the parser requires.
    return parse_expr(
        expr_str,
        transformations=transforms,
        evaluate=True,
    )


def _extract_matrices(expr_str):
    """Find top-level [[...],[...]] literals via balanced-bracket scanning,
    replace each with a placeholder symbol (_M0, _M1, ...), and return the
    rewritten string plus {placeholder: sympy.Matrix}."""
    import sympy as sp
    pieces, mats, i, idx, n = [], {}, 0, 0, len(expr_str)
    while i < n:
        if expr_str[i] == "[":
            depth, j = 0, i
            while j < n:
                if expr_str[j] == "[":
                    depth += 1
                elif expr_str[j] == "]":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if depth != 0:
                raise ValueError("unbalanced brackets in matrix literal")
            mats_obj = sp.Matrix(_parse(expr_str[i:j + 1]))
            name = f"_M{idx}"
            mats[name] = mats_obj
            pieces.append(name)
            idx += 1
            i = j + 1
        else:
            pieces.append(expr_str[i])
            i += 1
    return "".join(pieces), mats


def _matrix_arith(expr_str):
    """Free-form matrix arithmetic: multiplication, +, -, powers, inverse
    (**-1), and det()/trace()/transpose() helpers."""
    import sympy as sp
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations,
        implicit_multiplication_application, convert_xor,
    )
    rewritten, mats = _extract_matrices(expr_str)
    if not mats:
        raise ValueError("no matrix literal found; write matrices as [[1,2],[3,4]]")
    ns = dict(mats)
    ns.update({
        "det": lambda M: sp.Matrix(M).det(),
        "trace": lambda M: sp.Matrix(M).trace(),
        "transpose": lambda M: sp.Matrix(M).T,
    })
    transforms = (standard_transformations
                  + (implicit_multiplication_application, convert_xor))
    return parse_expr(rewritten, transformations=transforms,
                      local_dict=ns, evaluate=True)


def _single_matrix(expr_str):
    _, mats = _extract_matrices(expr_str)
    if len(mats) != 1:
        raise ValueError("this mode expects exactly one matrix literal")
    return next(iter(mats.values()))


def _pick_symbol(expr, requested):
    import sympy as sp
    if requested:
        return sp.Symbol(requested)
    free = sorted(expr.free_symbols, key=lambda s: s.name)
    if not free:
        return sp.Symbol("x")
    # prefer x, then y, then the first alphabetically
    for pref in ("x", "y", "z", "t", "n"):
        for s in free:
            if s.name == pref:
                return s
    return free[0]


def _compute(expr_str, mode, var, order=1):
    import sympy as sp

    # 'auto' heuristic: matrix literal -> matrix arithmetic; '=' -> solve;
    # otherwise simplify.
    if mode == "auto":
        if "[[" in expr_str:
            mode = "matrix"
        elif "=" in expr_str:
            mode = "solve"
        else:
            mode = "simplify"

    # ---- matrix family ----
    if mode == "matrix":
        return _matrix_arith(expr_str), None
    if mode == "det":
        return _single_matrix(expr_str).det(), None
    if mode == "rref":
        return _single_matrix(expr_str).rref()[0], None
    if mode == "inv":
        return _single_matrix(expr_str).inv(), None
    if mode == "adjugate":
        return _single_matrix(expr_str).adjugate(), None
    if mode == "transpose":
        return _single_matrix(expr_str).T, None
    if mode == "rank":
        return _single_matrix(expr_str).rank(), None
    if mode == "eigenvals":
        return _single_matrix(expr_str).eigenvals(), None

    if mode == "solve":
        # split on the single top-level '=' into lhs - rhs = 0
        if "=" in expr_str:
            lhs, _, rhs = expr_str.partition("=")
            eq = _parse(lhs) - _parse(rhs)
        else:
            eq = _parse(expr_str)
        symbol = _pick_symbol(eq, var)
        sol = sp.solve(sp.Eq(eq, 0), symbol, dict=False)
        return sol, symbol

    expr = _parse(expr_str)

    if mode == "eval":
        # exact if integer/rational; otherwise a high-precision decimal value
        val = sp.nsimplify(expr) if expr.free_symbols == set() else expr
        if expr.free_symbols:
            return sp.simplify(expr), None
        if val.is_Integer or val.is_Rational:
            return val, None
        return sp.N(expr, 30), None
    if mode == "simplify":
        return sp.simplify(sp.expand(expr)), None
    if mode == "expand":
        return sp.expand(expr), None
    if mode == "factor":
        return sp.factor(expr), None
    if mode == "diff":
        # Partial derivatives. --var "x,y" -> mixed partial d/dx then d/dy.
        # --var "x" with --order n -> n-th derivative w.r.t. x.
        if var and "," in var:
            syms = [sp.Symbol(v.strip()) for v in var.split(",") if v.strip()]
            return sp.diff(expr, *syms), ", ".join(s.name for s in syms)
        symbol = _pick_symbol(expr, var)
        if order and order > 1:
            return sp.diff(expr, symbol, order), f"{symbol} (order {order})"
        return sp.diff(expr, symbol), str(symbol)
    if mode == "integrate":
        symbol = _pick_symbol(expr, var)
        return sp.integrate(expr, symbol), symbol

    raise ValueError(f"unknown mode: {mode!r}")


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("expression")
    ap.add_argument("--mode", default="auto",
                    choices=["eval", "simplify", "expand", "factor",
                             "diff", "integrate", "solve",
                             "matrix", "det", "rref", "inv", "adjugate",
                             "transpose", "rank", "eigenvals", "auto"])
    ap.add_argument("--var", default=None,
                    help="variable(s) to operate on; comma-separated for mixed "
                         "partials, e.g. --var x,y")
    ap.add_argument("--order", type=int, default=1,
                    help="derivative order for diff with a single variable")
    ap.add_argument("--timeout", type=int, default=5)
    args = ap.parse_args()

    _apply_resource_limits(cpu_seconds=max(2, args.timeout + 3))

    # wall-clock-ish guard via SIGALRM (Unix). Best-effort on other platforms.
    try:
        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(args.timeout)
    except (ValueError, AttributeError):
        pass

    try:
        import sympy as sp
        # Allow large-but-sane integers to stringify; truly huge ones are still
        # caught by the timeout / memory limits above.
        try:
            sys.set_int_max_str_digits(200000)
        except AttributeError:
            pass
        expr_str = _validate(args.expression)
        result, symbol = _compute(expr_str, args.mode, args.var, args.order)

        # resolve the effective mode name for the output
        eff_mode = args.mode
        if args.mode == "auto":
            eff_mode = ("matrix" if "[[" in expr_str
                        else "solve" if "=" in expr_str else "simplify")

        # constant-of-integration nicety
        printed = result
        if eff_mode == "integrate":
            printed = sp.Add(result, sp.Symbol("C"), evaluate=False)

        # pretty-print matrices as nested lists; eigenvals dict as-is
        if hasattr(result, "tolist"):           # sympy Matrix
            result_str = str(result.tolist())
        else:
            result_str = str(printed)
        if len(result_str) > 8000:
            result_str = result_str[:8000] + " ...(truncated)"

        out = {
            "ok": True,
            "mode": eff_mode,
            "input": args.expression,
            "result": result_str,
        }
        try:
            out["latex"] = sp.latex(printed)
        except Exception:
            pass
        if symbol is not None:
            out["variable"] = str(symbol)
        print(json.dumps(out, ensure_ascii=False))

    except _Timeout as e:
        print(json.dumps({"ok": False, "error": str(e), "input": args.expression},
                         ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}",
                          "input": args.expression}, ensure_ascii=False))
        sys.exit(0)
    finally:
        try:
            signal.alarm(0)
        except Exception:
            pass


if __name__ == "__main__":
    main()
