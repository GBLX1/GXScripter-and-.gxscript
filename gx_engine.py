import re
import ast

class GXRuntimeError(Exception):
    def __init__(self, message, line):
        super().__init__(message)
        self.line = line

class GXEngine:
    def __init__(self, console_write, debugger_write, input_request, run_python_block=None, run_lua_block=None):
        self.vars = {}
        self.console_write = console_write
        self.debugger_write = debugger_write
        self.input_request = input_request
        self.run_python_block = run_python_block
        self.run_lua_block = run_lua_block
        self.lines = []
        self.current_line = 0
        self.flags = {"include_python": False, "include_lua": False}

    def execute(self, code):
        self.vars = {}
        self.lines = code.split("\n")
        self.current_line = 0
        self.flags = self._scan_directives()
        self._execute_block(0, len(self.lines))

    def _scan_directives(self):
        inc_py = False
        inc_lua = False
        for raw in self.lines:
            s = raw.strip()
            if not s:
                continue
            if s.startswith("#include_lua&python"):
                inc_py = True
                inc_lua = True
            elif s.startswith("#include_python"):
                inc_py = True
            elif s.startswith("#include_lua"):
                inc_lua = True
        return {"include_python": inc_py, "include_lua": inc_lua}

    def _execute_block(self, start, end):
        i = start
        while i < end:
            self.current_line = i + 1
            line = self.lines[i].strip()

            if not line:
                i += 1
                continue

            if line.startswith("#"):
                i += 1
                continue

            if line == "end":
                return

            if line == "lua_snippet:":
                if not self.flags["include_lua"] or self.run_lua_block is None:
                    raise GXRuntimeError("lua_snippet used but Lua is not enabled", self.current_line)
                snippet_code, next_i, snippet_start_line = self._consume_snippet(i + 1)
                self.run_lua_block(snippet_code, snippet_start_line)
                i = next_i
                continue

            if line == "py_snippet:":
                if not self.flags["include_python"] or self.run_python_block is None:
                    raise GXRuntimeError("py_snippet used but Python is not enabled", self.current_line)
                snippet_code, next_i, snippet_start_line = self._consume_snippet(i + 1)
                self.run_python_block(snippet_code, snippet_start_line)
                i = next_i
                continue

            if line.startswith("repeat"):
                count = self._eval_expr(line.split(" ", 1)[1])
                block_start = i + 1
                block_end = self._find_end_for_gx_blocks(block_start)
                for _ in range(int(count)):
                    self._execute_block(block_start, block_end)
                i = block_end + 1
                continue

            if line.startswith("if"):
                i = self._handle_if(i)
                continue

            self._execute_line(line)
            i += 1

    def _consume_snippet(self, start_index):
        i = start_index
        while i < len(self.lines):
            s = self.lines[i].strip()
            if not s:
                i += 1
                continue
            if s == "--s--":
                snippet_start_line = i + 2
                i += 1
                break
            raise GXRuntimeError("Expected --s-- after snippet header", self.current_line)

        buf = []
        while i < len(self.lines):
            s = self.lines[i].strip()
            if s == "--e--":
                return ("\n".join(buf), i + 1, snippet_start_line)
            buf.append(self.lines[i])
            i += 1

        raise GXRuntimeError("Missing --e-- for snippet", self.current_line)

    def _find_end_for_gx_blocks(self, start):
        depth = 0
        for i in range(start, len(self.lines)):
            s = self.lines[i].strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith(("if", "repeat")) or s in ("lua_snippet:", "py_snippet:"):
                depth += 1
            if s == "end":
                if depth == 0:
                    return i
                depth -= 1
        raise GXRuntimeError("Missing end", self.current_line)

    def _handle_if(self, index):
        block_start = index + 1
        block_end = self._find_end_for_gx_blocks(block_start)

        branches = []
        i = index
        while i <= block_end:
            line = self.lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue

            if line.startswith("if") or line.startswith("elif"):
                cond = line.split(" ", 1)[1]
                start = i + 1
                end = self._find_next_branch_or_end(start)
                branches.append(("cond", cond, start, end))
                i = end
                continue

            if line.startswith("else"):
                start = i + 1
                end = block_end
                branches.append(("else", None, start, end))
                break

            i += 1

        for kind, cond, s, e in branches:
            if kind == "cond":
                if self._eval_expr(cond):
                    self._execute_block(s, e)
                    break
            else:
                self._execute_block(s, e)
                break

        return block_end + 1

    def _find_next_branch_or_end(self, start):
        depth = 0
        for i in range(start, len(self.lines)):
            line = self.lines[i].strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(("if", "repeat")) or line in ("lua_snippet:", "py_snippet:"):
                depth += 1
            if line == "end":
                if depth == 0:
                    return i
                depth -= 1
            if depth == 0 and (line.startswith("elif") or line.startswith("else")):
                return i
        return len(self.lines)

    def _execute_line(self, line):
        if line == "console.clear()":
            self._console_clear()
        elif line.startswith("var.set"):
            self._var_set(line)
        elif line.startswith("var.ask"):
            self._var_ask(line)
        elif line.startswith("var.math_"):
            self._var_math_typed(line)
        elif line.startswith("var.math"):
            self._var_math_expr(line)
        elif line.startswith("var.inc"):
            var = self._after_equals_or_space(line, "var.inc")
            if var not in self.vars:
                self.vars[var] = 0
            self.vars[var] = self.vars[var] + 1
        elif line.startswith("var.dec"):
            var = self._after_equals_or_space(line, "var.dec")
            if var not in self.vars:
                self.vars[var] = 0
            self.vars[var] = self.vars[var] - 1
        elif line.startswith("table.add"):
            self._table_add(line)
        elif line.startswith("table.remove"):
            self._table_remove(line)
        elif line.startswith("table.get"):
            self._table_get(line)
        elif line.startswith("say"):
            content = line[4:].strip()
            values = self._eval_say_args(content)
            self.console_write(" ".join(str(v) for v in values) + "\n")
        elif line.startswith("debugprint"):
            self._debug_print(line)
        else:
            raise GXRuntimeError("Unknown command: " + line, self.current_line)

    def _eval_say_args(self, content: str):
        if not content:
            return []

        parts = []
        buf = ""
        depth = 0
        in_str = False
        str_ch = ""

        for ch in content:
            if in_str:
                buf += ch
                if ch == str_ch:
                    in_str = False
                continue

            if ch in ('"', "'"):
                in_str = True
                str_ch = ch
                buf += ch
                continue

            if ch in "([{":
                depth += 1
                buf += ch
                continue

            if ch in ")]}":
                depth = max(0, depth - 1)
                buf += ch
                continue

            if ch == "," and depth == 0:
                if buf.strip():
                    parts.append(buf.strip())
                buf = ""
                continue

            buf += ch

        if buf.strip():
            parts.append(buf.strip())

        return [self._eval_expr(p) for p in parts]

    def _console_clear(self):
        obj = getattr(self.console_write, "__self__", None)
        if obj is not None and hasattr(obj, "clear_output"):
            obj.clear_output()
            return
        self.console_write("\n")

    def _after_equals_or_space(self, line, head):
        s = line[len(head):].strip()
        if s.startswith("="):
            s = s[1:].strip()
        return s.strip()

    def _var_set(self, line):
        parts = line.split("=", 1)[1].split(",", 1)
        var = parts[0].strip()
        value = self._eval_expr(parts[1].strip())
        self.vars[var] = value

    def _var_ask(self, line):
        parts = line.split("=", 1)[1].split(",", 1)
        var = parts[0].strip()
        question = self._eval_expr(parts[1].strip())
        value = self.input_request(question)
        self.vars[var] = value

    def _var_math_typed(self, line):
        match = re.match(r"var\.math_(add|sub|mul|div)\s*=\s*(.*)", line)
        if not match:
            raise GXRuntimeError("Invalid var.math_* syntax", self.current_line)
        op = match.group(1)
        parts = [p.strip() for p in match.group(2).split(",")]
        if len(parts) != 3:
            raise GXRuntimeError("Invalid var.math_* args", self.current_line)
        a = self._eval_expr(parts[0])
        b = self._eval_expr(parts[1])
        out = parts[2]
        if op == "add":
            self.vars[out] = a + b
        elif op == "sub":
            self.vars[out] = a - b
        elif op == "mul":
            self.vars[out] = a * b
        elif op == "div":
            self.vars[out] = a / b

    def _var_math_expr(self, line):
        parts = line.split("=", 1)[1].split(",", 1)
        out = parts[0].strip()
        expr = parts[1].strip()
        self.vars[out] = self._eval_expr(expr)

    def _table_add(self, line):
        parts = line.split("=", 1)[1].split(",")
        table = parts[0].strip()
        value = self._eval_expr(parts[1].strip())
        if table not in self.vars or not isinstance(self.vars[table], list):
            self.vars[table] = []
        self.vars[table].append(value)

    def _table_remove(self, line):
        parts = line.split("=", 1)[1].split(",")
        table = parts[0].strip()
        value = self._eval_expr(parts[1].strip())
        if table not in self.vars or not isinstance(self.vars[table], list):
            raise GXRuntimeError("table.remove target is not a table", self.current_line)
        self.vars[table].remove(value)

    def _table_get(self, line):
        parts = line.split("=", 1)[1].split(",")
        table = parts[0].strip()
        index = int(self._eval_expr(parts[1].strip()))
        out = parts[2].strip()
        if table not in self.vars or not isinstance(self.vars[table], list):
            raise GXRuntimeError("table.get target is not a table", self.current_line)
        self.vars[out] = self.vars[table][index]

    def _debug_print(self, line):
        level = "info"
        if "-e" in line:
            level = "error"
        elif "-w" in line:
            level = "warning"
        message = re.findall(r'"(.*?)"', line)
        if message:
            self.debugger_write(message[0], level, line=self.current_line, source="GX")
        else:
            self.debugger_write("debugprint missing string", "warning", line=self.current_line, source="GX")

    def _eval_expr(self, expr):
        expr = expr.replace("true", "True").replace("false", "False")
        try:
            tree = ast.parse(expr, mode="eval")
            return eval(compile(tree, filename="", mode="eval"), {}, self.vars)
        except Exception:
            raise GXRuntimeError("Invalid expression: " + expr, self.current_line)