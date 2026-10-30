# Symbol Table Generator
**Compiler Design mini-project** - reads a C-like or a Python program and builds its symbol table, with scope handling and semantic error detection.

The input language is chosen with the **Language** dropdown in the web UI (C or Python) or with `--lang` on the command line.

## Run it
Requires Python 3.8+. No external libraries (the Python front end uses only the standard `ast` and `tokenize` modules).

**Web frontend (recommended for the demo):**
```
python server.py
```
Then open http://localhost:8000. Choose the language (C or Python) in the dropdown, paste or edit code, pick a sample, press Analyze (or Ctrl+Enter). You get nested scope boxes with each scope's symbol table, the token stream, clickable diagnostics that jump to the source line, and JSON download. Use `python server.py 5000` for another port.

**Command line:**

```
python main.py samples/sample_valid.c
python main.py samples/sample_errors.c
python main.py samples/sample_valid.py                # Python (guessed from .py)
python main.py samples/sample_errors.py --lang python # or choose it explicitly
python main.py samples/sample_valid.c --tokens        # also show lexer output
python main.py samples/sample_valid.c --json out.json # export table as JSON
python -m unittest discover -s tests -v               # run the tests
```

## Project structure
```
symbol-table-generator/
|-- main.py                 CLI entry point (--lang c|python)
|-- server.py               Web server (stdlib http.server) with /api/analyze
|-- web/                    Frontend: index.html, style.css, app.js
|-- symtab/
|   |-- lexer.py            C phase 1: source -> tokens (regex based, tracks line/col)
|   |-- parser.py           C phase 2: recursive-descent parser + semantic checks
|   |-- py_lexer.py         Python phase 1: tokens incl. INDENT / DEDENT / NEWLINE
|   |-- py_analyzer.py      Python phase 2: syntax tree walk, scopes, semantic checks
|   |-- symbol_table.py     Symbol, Scope, SymbolTable (stack of hash tables)
|   |-- report.py           Tables, scope tree, JSON export
|   `-- diagnostics.py      Error / warning record
|-- samples/                sample_valid / sample_errors, as .c and .py
`-- tests/test_symtab.py    59 unit tests (C and Python)
```

## How it works
1. **Lexer** removes comments and `#include` lines, then converts the text into tokens (KEYWORD, ID, NUM, STRING, CHAR, OP, PUNCT) with line numbers.
2. **Parser** is a recursive-descent parser for a C subset: global and local declarations, arrays with initializers, functions and prototypes, `if/else`, `while`, `for`, `return`, `break/continue`, and expressions with correct operator precedence.
3. **Symbol table** is a *stack of hash tables*, one per scope.
   - `{` pushes a new scope, `}` pops it (closed scopes are kept so they can be printed).
   - **insert** checks only the current scope, so a redeclaration in the same scope is an error but shadowing an outer name is legal.
   - **lookup** searches from the innermost scope outwards.
4. Each symbol stores: name, category (variable / array / parameter / function), type, scope, size in bytes, aligned offset within its scope, declaration line, initialized flag, used flag, and for functions the parameter types and whether it is defined or only a prototype.

## Python support
Python has no braces, no declarations and no fixed sizes, so the Python front end works differently while sharing the same `SymbolTable`:
- **Lexer** wraps the standard `tokenize` module and adds the `INDENT`, `DEDENT` and `NEWLINE` tokens that Python's grammar depends on.
- **Parser** uses the standard `ast` module for the syntax tree. After a syntax error the offending line is replaced by a harmless statement and parsing is retried, so you still get a symbol table and can see several errors at once.
- **Scopes** follow Python's LEGB rule: module (`global`), function, class, lambda and comprehension scopes. `if`/`for`/`while` blocks do **not** create scopes. A name assigned anywhere in a function is local to the whole function, `global` and `nonlocal` redirect a name to an outer scope, and class-body names are not visible inside methods.
- **Types** are inferred from literals, operators, annotations, return statements and calls (`int`, `float`, `str`, `list`, ...). If a variable is assigned different types it is shown as a union such as `int | str`; unknown is `any`.
- **Categories**: variable, parameter, function, class, import, and attribute (`self.x = ...` inside a method is recorded in the class scope).
- Size and offset are not meaningful for Python objects, so those columns are hidden in the UI (and shown as `-` on the command line).

## Errors and warnings detected (C)
| Kind | Example |
|---|---|
| error | redeclaration in the same scope |
| error | use of an undeclared identifier (including a name used outside its scope) |
| error | wrong number of arguments in a function call |
| error | string assigned to a non-array, void value used, assigning to a whole array |
| error | `return value;` in a void function, function redefinition, `break` outside a loop |
| error | syntax errors (parser recovers and continues) |
| warning | float -> int narrowing, variable used before initialization, variable never used |

## Errors and warnings detected (Python)
| Kind | Example |
|---|---|
| error | syntax errors (reported, then the parser recovers) |
| error | undefined name, including a local used outside its function or a comprehension variable used after it |
| error | module-level name used before it is defined |
| error | wrong number of arguments, unexpected keyword argument (defaults, `*args`, `**kwargs` understood) |
| error | `'x' is of type 'int' and is not callable`, `'a' + 1` (str and int), and similar operand type mismatches |
| error | `return` outside a function, `break` / `continue` outside a loop, `nonlocal` with no enclosing binding, duplicate parameter |
| warning | local variable used before assignment, variable assigned but never used, unused import |
| warning | function redefined in the same scope, wildcard import |

## Design notes (useful for viva)
- **Why a stack of hash tables?** O(1) lookup per scope, and entering/leaving a scope is just push/pop.
- **Why keep exited scopes?** The final report needs them; real compilers keep this info for later phases (type checking, code generation).
- **Offsets** show how a compiler would lay out variables in a stack frame, with each variable aligned to its own size.
- **Error recovery** uses panic mode: after a syntax error the parser skips to the next `;` or `}` so one mistake does not hide the rest.

## Limitations / future work
C: pointers, structs, `switch`, and the preprocessor are not supported. Python: type inference is flow-insensitive and only checks simple built-in types, attribute and method calls (`obj.method()`) are not checked, and `exec`/`eval`/`import *` names are not tracked. Possible extensions: a Lex/Yacc version, type checking of full expression trees, intermediate code generation, a GUI view of the scope tree.
