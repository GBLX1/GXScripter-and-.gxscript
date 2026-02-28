Please be aware that there might be some bugs since this all was written in python.


# GXScripter Snippet Reference

This file documents all GXScript snippets/commands supported by the current GXScripter IDE build.

---

## Directives

`#include_lua`  
Enables `lua_snippet:` blocks and Lua autocomplete.

`#include_python`  
Enables `py_snippet:` blocks and Python autocomplete.

`#include_lua&python`  
Enables both Lua + Python snippets and both autocompletions.

---

## Output

`say [value]`  
`say [value1], [value2], [value3] ...`  
Prints values to the console (space-separated).

Example:
- `say "Hello", name`

---

## Console

`console.clear()`  
Clears the console output and resets the prompt/header.

---

## Input

`var.ask = [variable name], "Question String"`  
Prompts the user in the console and stores the input string.

Example:
- `var.ask = v1, "What is your name?"`

---

## Variables

`var.set = [variable name], [value]`  
Sets a variable to a value.

Value can be:
- `"string"`
- `123` / `12.5`
- `true` / `false`
- `[1, 2, 3]` (table/list)
- `["a", "b"]`

Examples:
- `var.set = x, 10`
- `var.set = items, [1,2,3]`

---

## Math

`var.math_add = [a], [b], [output var]`  
`var.math_sub = [a], [b], [output var]`  
`var.math_mul = [a], [b], [output var]`  
`var.math_div = [a], [b], [output var]`

Example:
- `var.math_add = x, 5, result`

`var.math = [output var], [math expression]`  
Expression can use variables and operators `+ - * / ** ( )`

Examples:
- `var.math = power, a ** b`
- `var.math = total, (x + y) * 2`

---

## Increment / Decrement

`var.inc [variable name]`  
`var.inc = [variable name]`  
Adds 1 to the variable.

`var.dec [variable name]`  
`var.dec = [variable name]`  
Subtracts 1 from the variable.

---

## Tables (Lists)

`table.add = [table var], [value]`  
Appends value to a list. If the list doesn’t exist yet, it becomes an empty list first.

`table.remove = [table var], [value]`  
Removes the first matching value from the list.

`table.get = [table var], [index], [output var]`  
Gets list item at index (0-based) and stores it in output variable.

Example:
- `var.set = nums, [10,20,30]`
- `table.add = nums, 40`
- `table.get = nums, 0, first`

---

## Control Flow

`repeat [count]`  
Starts a repeat block.

`end`  
Ends a block (`repeat`, `if`, `lua_snippet`, `py_snippet`).

Example:
```gx
repeat 3
    say "Hi"
end
```

`if [condition]`  
`elif [condition]`  
`else`  
Conditional blocks. Conditions are Python-style expressions using your variables.

Example:
```gx
if x > 10
    say "Big"
elif x == 10
    say "Equal"
else
    say "Small"
end
```

---

## Debugger

`debugprint "Message"`  
Outputs to debugger only (info).

`debugprint "Message" -w`  
Outputs to debugger only (warning).

`debugprint "Message" -e`  
Outputs to debugger only (error).

---

## Lua Snippet Block

`lua_snippet:`  
Starts a Lua snippet section (requires `#include_lua` or `#include_lua&python` somewhere in the file).

`--s--`  
Start of snippet code.

`--e--`  
End of snippet code.

Example:
```gx
#include_lua

lua_snippet:
--s--
print("Hello from Lua", v1)
x = x + 1
--e--
```

Notes:
- GX variables are injected into Lua before running.
- Lua globals sync back into GX after running.
- Any Lua global starting with `gx_` is also copied into GX.

---

## Python Snippet Block

`py_snippet:`  
Starts a Python snippet section (requires `#include_python` or `#include_lua&python` somewhere in the file).

`--s--`  
Start of snippet code.

`--e--`  
End of snippet code.

Example:
```gx
#include_python

py_snippet:
--s--
print("Hello from Python", v1)
--e--
```

Notes:
- GX variables are injected into Python snippet globals before running.
