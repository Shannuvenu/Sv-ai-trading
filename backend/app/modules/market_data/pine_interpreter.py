"""
Safe Pine-like script interpreter for chart indicators and strategies.
No eval, exec, or arbitrary code execution. Pure Python AST-based parser.

Supports: indicator(), strategy(), plot(), plotshape(), hline(),
  sma(), ema(), wma(), rsi(), macd(), atr(), stdev(),
  highest(), lowest(), crossover(), crossunder(),
  abs(), min(), max(), close, open, high, low, volume,
  hl2, hlc3, ohlc4, basic arithmetic, comparisons, ternaries.
"""
import ast
import logging
import math
import operator as op
from typing import Any, Callable, Optional

logger = logging.getLogger("pine_interpreter")

# ─── SAFE BUILTIN FUNCTIONS ───
SAFE_FUNCTIONS: dict[str, Callable] = {
    "abs": abs, "min": min, "max": max, "round": round,
    "int": int, "float": float, "len": len, "sum": sum,
    "list": list, "range": range, "str": str, "bool": bool,
    "print": lambda *a, **k: None,  # no-op
}

SAFE_BINARY_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod, ast.Pow: op.pow,
    ast.LShift: op.lshift, ast.RShift: op.rshift,
    ast.BitOr: op.or_, ast.BitAnd: op.and_,
    ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b,
}

SAFE_COMPARE_OPS = {
    ast.Eq: op.eq, ast.NotEq: op.ne,
    ast.Lt: op.lt, ast.LtE: op.le,
    ast.Gt: op.gt, ast.GtE: op.ge,
    ast.Is: op.is_, ast.IsNot: op.is_not,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
}

BANNED_MODULES = {"os", "sys", "subprocess", "shutil", "importlib", "ctypes", "socket", "http", "requests", "open", "file"}
BANNED_FUNCTIONS = {"eval", "exec", "compile", "__import__", "open", "input", "globals", "locals", "getattr", "setattr", "delattr"}


class PineError(Exception):
    pass


class PineResult:
    def __init__(self):
        self.plots: list[dict] = []
        self.shapes: list[dict] = []
        self.hlines: list[dict] = []
        self.trades: list[dict] = []
        self.strategy_name: str = ""
        self.warnings: list[str] = []
        self.errors: list[str] = []


class PineInterpreter:
    def __init__(self, ohlc_data: dict):
        """
        ohlc_data: {
            "open": [float, ...],
            "high": [float, ...],
            "low": [float, ...],
            "close": [float, ...],
            "volume": [int, ...],
            "time": [str, ...],
        }
        """
        self.o = ohlc_data.get("open", [])
        self.h = ohlc_data.get("high", [])
        self.l = ohlc_data.get("low", [])
        self.c = ohlc_data.get("close", [])
        self.v = ohlc_data.get("volume", [])
        self.t = ohlc_data.get("time", [])
        self.n = len(self.c)
        self.result = PineResult()

        # Built-in series variables (Pine compatible)
        self._vars: dict[str, list] = {
            "open": self.o,
            "high": self.h,
            "low": self.l,
            "close": self.c,
            "volume": self.v,
            "hl2": [(hi + lo) / 2 for hi, lo in zip(self.h, self.l)],
            "hlc3": [(hi + lo + cl) / 3 for hi, lo, cl in zip(self.h, self.l, self.c)],
            "ohlc4": [(op_ + hi + lo + cl) / 4 for op_, hi, lo, cl in zip(self.o, self.h, self.l, self.c)],
        }
        self._user_vars: dict[str, list] = {}
        self._functions: dict[str, Callable] = {
            "sma": self._sma,
            "ema": self._ema,
            "wma": self._wma,
            "rsi": self._rsi,
            "macd": self._macd,
            "atr": self._atr,
            "stdev": self._stdev,
            "highest": self._highest,
            "lowest": self._lowest,
            "crossover": self._crossover,
            "crossunder": self._crossunder,
            "nz": self._nz,
            "plot": self._plot,
            "plotshape": self._plotshape,
            "hline": self._hline,
            "indicator": self._indicator,
            "strategy": self._strategy,
            "color": lambda *a: None,
        }

    def execute(self, script: str) -> PineResult:
        try:
            tree = ast.parse(script)
            self._run_body(tree.body)
        except PineError as e:
            self.result.errors.append(str(e))
        except SyntaxError as e:
            self.result.errors.append(f"Syntax error: {e}")
        except Exception as e:
            self.result.errors.append(f"Runtime error: {e}")
        return self.result

    def _run_body(self, body: list[ast.stmt]):
        for stmt in body:
            self._run_stmt(stmt)

    def _run_stmt(self, stmt: ast.stmt):
        if isinstance(stmt, ast.Assign):
            self._handle_assign(stmt)
        elif isinstance(stmt, ast.Expr):
            self._eval(stmt.value)
        elif isinstance(stmt, ast.FunctionDef):
            pass  # skip user function defs for now
        elif isinstance(stmt, ast.If):
            self._handle_if(stmt)
        else:
            pass

    def _handle_assign(self, stmt: ast.Assign):
        if len(stmt.targets) != 1:
            raise PineError("Only single target assignment supported")
        target = stmt.targets[0]
        if not isinstance(target, ast.Name):
            raise PineError("Only simple variable assignment supported")
        name = target.id
        value = self._eval(stmt.value)
        if isinstance(value, list):
            self._user_vars[name] = value
        else:
            self._user_vars[name] = [value] * self.n

    def _handle_if(self, stmt: ast.If):
        condition = self._eval(stmt.test)
        if condition:
            self._run_body(stmt.body)

    def _eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.Name):
            name = node.id
            # Check user vars, built-in series, and our functions FIRST
            # before checking banned functions — 'open', 'close' are both
            # OHLC series AND Python builtins that happen to be on our banned list.
            if name in self._user_vars:
                return self._user_vars[name]
            if name in self._vars:          # OHLC series: open, high, low, close, volume, hl2, hlc3, ohlc4
                return self._vars[name]
            if name in self._functions:     # pine built-ins: sma, ema, rsi, plot, etc.
                return self._functions[name]
            if name in SAFE_FUNCTIONS:
                return SAFE_FUNCTIONS[name]
            if name in BANNED_FUNCTIONS:
                raise PineError(f"Function '{name}' is not allowed")
            raise PineError(f"Unknown variable: {name}")
        if isinstance(node, ast.List):
            return [self._eval(elt) for elt in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._eval(elt) for elt in node.elts)
        if isinstance(node, ast.BinOp):
            left = self._eval(node.left)
            right = self._eval(node.right)
            op_type = type(node.op)
            if op_type not in SAFE_BINARY_OPS:
                raise PineError(f"Unsupported operator: {op_type.__name__}")
            return self._apply_binary(op_type, left, right)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval(node.operand)
            if isinstance(node.op, ast.USub):
                if isinstance(operand, list):
                    return [-x for x in operand]
                return -operand
            if isinstance(node.op, ast.UAdd):
                return operand if isinstance(operand, list) else +operand
            raise PineError(f"Unsupported unary operator: {type(node.op).__name__}")
        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            result = True
            for op_node, comp_node in zip(node.ops, node.comparators):
                right = self._eval(comp_node)
                op_type = type(op_node)
                if op_type not in SAFE_COMPARE_OPS:
                    raise PineError(f"Unsupported comparison: {op_type.__name__}")
                fn = SAFE_COMPARE_OPS[op_type]
                if isinstance(left, list) and isinstance(right, list):
                    result = [fn(l, r) for l, r in zip(left, right)]
                elif isinstance(left, list):
                    result = [fn(l, right) for l in left]
                elif isinstance(right, list):
                    result = [fn(left, r) for r in right]
                else:
                    result = fn(left, right)
                left = result
            return result
        if isinstance(node, ast.IfExp):
            test = self._eval(node.test)
            if test:
                return self._eval(node.body)
            return self._eval(node.orelse)
        if isinstance(node, ast.Call):
            func = self._eval(node.func)
            if not callable(func):
                raise PineError(f"Not callable: {node.func}")
            args = [self._eval(a) for a in node.args]
            kwargs = {kw.arg: self._eval(kw.value) for kw in node.keywords}
            if func.__name__ in BANNED_FUNCTIONS:
                raise PineError(f"Banned function: {func.__name__}")
            return func(*args, **kwargs)
        if isinstance(node, ast.Attribute):
            obj = self._eval(node.value)
            attr = node.attr
            if isinstance(obj, str) and attr in ("entry", "close", "exit"):
                # strategy.entry / strategy.close / strategy.exit — record trade signals
                return self._strategy_action(attr)
            raise PineError(f"Unsupported attribute: {attr}")
        if isinstance(node, ast.Dict):
            return {self._eval(k): self._eval(v) for k, v in zip(node.keys, node.values)}
        raise PineError(f"Unsupported expression: {type(node).__name__}")

    def _apply_binary(self, op_type, left, right):
        fn = SAFE_BINARY_OPS[op_type]
        if isinstance(left, list) and isinstance(right, list):
            return [fn(l, r) for l, r in zip(left, right)]
        if isinstance(left, list):
            return [fn(l, right) for l in left]
        if isinstance(right, list):
            return [fn(left, r) for r in right]
        return fn(left, right)

    # ─── BUILT-IN INDICATORS ───

    def _sma(self, source, length=20):
        s = self._resolve(source)
        n = int(length)
        result = [None] * self.n
        for i in range(n - 1, self.n):
            result[i] = sum(s[i - n + 1:i + 1]) / n
        return result

    def _ema(self, source, length=50):
        s = self._resolve(source)
        n = int(length)
        result = [None] * self.n
        mult = 2.0 / (n + 1)
        result[0] = s[0]
        for i in range(1, self.n):
            result[i] = (s[i] - (result[i - 1] or s[i])) * mult + (result[i - 1] or s[i])
        return result

    def _wma(self, source, length=20):
        s = self._resolve(source)
        n = int(length)
        result = [None] * self.n
        weight_sum = n * (n + 1) / 2
        for i in range(n - 1, self.n):
            window = s[i - n + 1:i + 1]
            result[i] = sum((j + 1) * window[j] for j in range(n)) / weight_sum
        return result

    def _rsi(self, source, length=14):
        s = self._resolve(source)
        n = int(length)
        result = [None] * self.n
        gains, losses = [], []
        for i in range(1, self.n):
            delta = s[i] - s[i - 1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))
        for i in range(n, self.n):
            idx = i - n
            avg_gain = sum(gains[idx:idx + n]) / n
            avg_loss = sum(losses[idx:idx + n]) / n
            rs = avg_gain / avg_loss if avg_loss > 0 else float('inf')
            result[i] = 100.0 - (100.0 / (1.0 + rs))
        return result

    def _macd(self, source, fast=12, slow=26, signal=9):
        s = self._resolve(source)
        fast_ema = self._ema(s, fast)
        slow_ema = self._ema(s, slow)
        macd_line = [f - sl if f is not None and sl is not None else None for f, sl in zip(fast_ema, slow_ema)]
        sig_line = self._ema([(x or 0) for x in macd_line], signal)
        histogram = [m - s_ if m is not None and s_ is not None else None for m, s_ in zip(macd_line, sig_line)]
        return {"macd": macd_line, "signal": sig_line, "histogram": histogram}

    def _atr(self, length=14):
        trs = [self.h[0] - self.l[0]]
        for i in range(1, self.n):
            tr = max(self.h[i] - self.l[i], abs(self.h[i] - self.c[i - 1]), abs(self.l[i] - self.c[i - 1]))
            trs.append(tr)
        return self._sma(trs, int(length))

    def _stdev(self, source, length=20):
        s = self._resolve(source)
        n = int(length)
        result = [None] * self.n
        import statistics
        for i in range(n - 1, self.n):
            result[i] = statistics.stdev(s[i - n + 1:i + 1])
        return result

    def _highest(self, source, length=20):
        s = self._resolve(source)
        n = int(length)
        result = [None] * self.n
        for i in range(n - 1, self.n):
            result[i] = max(s[i - n + 1:i + 1])
        return result

    def _lowest(self, source, length=20):
        s = self._resolve(source)
        n = int(length)
        result = [None] * self.n
        for i in range(n - 1, self.n):
            result[i] = min(s[i - n + 1:i + 1])
        return result

    def _crossover(self, a, b):
        a = self._resolve(a)
        b = self._resolve(b)
        result = [False] * self.n
        for i in range(1, self.n):
            if a[i] is not None and b[i] is not None and a[i - 1] is not None and b[i - 1] is not None:
                result[i] = a[i] > b[i] and a[i - 1] <= b[i - 1]
        return result

    def _crossunder(self, a, b):
        a = self._resolve(a)
        b = self._resolve(b)
        result = [False] * self.n
        for i in range(1, self.n):
            if a[i] is not None and b[i] is not None and a[i - 1] is not None and b[i - 1] is not None:
                result[i] = a[i] < b[i] and a[i - 1] >= b[i - 1]
        return result

    def _nz(self, source, replacement=0):
        s = self._resolve(source)
        return [(x if x is not None else replacement) for x in s]

    # ─── PLOT FUNCTIONS ───

    def _plot(self, series, title="", color="", style="", linewidth=""):
        s = self._resolve(series)
        self.result.plots.append({
            "title": str(title) or "plot",
            "color": str(color) or "#6366f1",
            "style": str(style) or "line",
            "linewidth": int(linewidth) if linewidth else 1,
            "data": [{"time": self.t[i], "value": round(s[i], 4) if s[i] is not None else None} for i in range(self.n)],
        })

    def _plotshape(self, series, title="", style="", location=""):
        s = self._resolve(series)
        self.result.shapes.append({
            "title": str(title) or "shape",
            "style": str(style) or "circle",
            "location": str(location) or "abovebar",
            "data": [{"time": self.t[i], "value": round(s[i], 4) if s[i] is not None else None} for i in range(self.n)],
        })

    def _hline(self, price, title="", color="", linewidth=""):
        self.result.hlines.append({
            "title": str(title) or "hline",
            "price": float(price),
            "color": str(color) or "#71717a",
            "linewidth": int(linewidth) if linewidth else 1,
        })

    def _indicator(self, title, shorttitle="", overlay=""):
        self.result.strategy_name = str(title)
        logger.info(f"Pine indicator: {title}")

    def _strategy(self, title, shorttitle="", overlay=""):
        self.result.strategy_name = f"Strategy: {title}"

    def _strategy_action(self, action):
        if action == "entry":
            self.result.trades.append({"action": "entry", "time": self.t[-1], "price": self.c[-1]})
        elif action == "close":
            self.result.trades.append({"action": "close", "time": self.t[-1], "price": self.c[-1]})
        elif action == "exit":
            self.result.trades.append({"action": "exit", "time": self.t[-1], "price": self.c[-1]})

    def _resolve(self, value):
        if isinstance(value, str):
            v = value.lower().replace(" ", "")
            if v in self._vars:
                return self._vars[v]
            if v in self._user_vars:
                return self._user_vars[v]
        if isinstance(value, (int, float)):
            return [float(value)] * self.n
        if isinstance(value, list):
            return value
        return [0.0] * self.n
