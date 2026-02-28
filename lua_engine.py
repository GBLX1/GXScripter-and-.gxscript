import re
import traceback
from lupa import LuaRuntime


class LuaEngine:
    def __init__(self, console_write, debugger_write, input_request=None):
        self.console_write = console_write
        self.debugger_write = debugger_write
        self.input_request = input_request
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self._install_hooks()

    def _install_hooks(self):
        def _print(*args):
            out = " ".join(str(a) for a in args)
            self.console_write(out + "\n")

        def _input(prompt=""):
            if prompt:
                self.console_write(str(prompt))
            if self.input_request is None:
                raise RuntimeError("Input requested but no input handler is set")
            return self.input_request(prompt if prompt else "Input:")

        self.lua.globals()["print"] = _print
        self.lua.globals()["gx_input"] = _input

    def execute(self, code: str, filename: str = "<lua>"):
        try:
            self.lua.execute(code)
        except Exception:
            tb = traceback.format_exc()
            line = self._extract_line(tb)
            self.debugger_write(tb.strip(), "error", line=line, source="LUA")

    def inject_globals(self, gx_vars: dict):
        g = self.lua.globals()
        for k, v in (gx_vars or {}).items():
            if not isinstance(k, str):
                continue
            if not k or k.startswith("_"):
                continue
            try:
                g[k] = self._py_to_lua(v)
            except Exception:
                pass

    def sync_back(self, gx_vars: dict):
        g = self.lua.globals()

        keys_to_pull = set()
        for k in (gx_vars or {}).keys():
            if isinstance(k, str) and k and not k.startswith("_"):
                keys_to_pull.add(k)

        try:
            for k in g.keys():
                if isinstance(k, str) and k.startswith("gx_"):
                    keys_to_pull.add(k)
        except Exception:
            pass

        for k in keys_to_pull:
            try:
                gx_vars[k] = self._lua_to_py(g[k])
            except Exception:
                pass

    def _py_to_lua(self, v):
        if isinstance(v, (int, float, str, bool)) or v is None:
            return v
        if isinstance(v, list):
            t = self.lua.table()
            for i, item in enumerate(v, start=1):
                t[i] = self._py_to_lua(item)
            return t
        if isinstance(v, dict):
            t = self.lua.table()
            for k, item in v.items():
                t[k] = self._py_to_lua(item)
            return t
        return str(v)

    def _lua_to_py(self, v, depth=0):
        if depth > 6:
            return str(v)
        if isinstance(v, (int, float, str, bool)) or v is None:
            return v

        try:
            if hasattr(v, "keys"):
                keys = list(v.keys())
                if all(isinstance(k, int) for k in keys) and keys:
                    mx = max(keys)
                    if set(keys) == set(range(1, mx + 1)):
                        return [self._lua_to_py(v[i], depth + 1) for i in range(1, mx + 1)]
                out = {}
                for k in keys:
                    out[k] = self._lua_to_py(v[k], depth + 1)
                return out
        except Exception:
            pass

        return str(v)

    def _extract_line(self, tb: str):
        m = re.search(r":(\d+):", tb)
        if m:
            try:
                return int(m.group(1))
            except:
                return None
        return None