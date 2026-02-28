import io
import os
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr

class PythonEngine:
    def __init__(self, console_write, debugger_write, input_request=None):
        self.console_write = console_write
        self.debugger_write = debugger_write
        self.input_request = input_request

        # Optional: persistent session globals (so state persists across runs)
        self.session_globals = {}

    def execute(self, code: str, filename: str = "<python>", extra_globals=None, persist_session=True):
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        def _input(prompt=""):
            if prompt:
                self.console_write(str(prompt))
            if self.input_request is None:
                raise RuntimeError("Input requested but no input handler is set")
            return self.input_request(prompt if prompt else "Input:")

        script_dir = None
        if filename and filename not in ("<python>", "<string>"):
            script_dir = os.path.dirname(os.path.abspath(filename))

        # Build globals
        if persist_session:
            glb = self.session_globals
        else:
            glb = {}

        # Always refresh these
        glb.update({
            "__name__": "__main__",
            "__file__": filename,
            "input": _input,
        })

        if extra_globals:
            glb.update(extra_globals)

        # Make imports behave
        old_cwd = os.getcwd()
        old_sys_path = list(sys.path)

        try:
            if script_dir:
                # Put script directory first (like running python file.py)
                if script_dir not in sys.path:
                    sys.path.insert(0, script_dir)
                os.chdir(script_dir)

            compiled = compile(code, filename, "exec")
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compiled, glb, glb)

        except Exception:
            tb = traceback.format_exc()
            line = self._extract_line_from_traceback(tb, filename)
            self.debugger_write(tb.strip(), "error", line=line, source="PY")

        finally:
            # Restore process state
            os.chdir(old_cwd)
            sys.path[:] = old_sys_path

            out = stdout_buf.getvalue()
            err = stderr_buf.getvalue()
            if out:
                self.console_write(out)
            if err:
                self.console_write(err)

    def _extract_line_from_traceback(self, tb: str, filename: str):
        for line in tb.splitlines():
            if line.strip().startswith('File "') and f'File "{filename}"' in line:
                parts = line.split(",")
                for p in parts:
                    p = p.strip()
                    if p.startswith("line "):
                        try:
                            return int(p.replace("line ", "").strip())
                        except:
                            pass
        return None