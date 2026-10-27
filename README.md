# Mini Java lexical analyzer

Phase 1 of the Mini Java compiler project. Uses Python 3.10 or later with no extra packages.

## Run

Open a terminal in this folder:

```text
python lexer.py inputs/sample.txt
python lexer.py inputs/valid_programs.txt
python lexer.py inputs/errors.txt
python lexer.py inputs/unclosed_comment.txt
python -m unittest -v
```

The lexer prints tokens, an identifier symbol table, and errors. The first two inputs are valid; the last two demonstrate errors. Input files use UTF-8. Exit codes: `0` = no errors, `1` = lexical errors, `2` = incorrect usage or an unreadable file.

## Files

- `lexer.py`: the scanner and command-line entry point.
- `inputs/`: the assignment sample, additional valid programs, and error examples.
- `test_lexer.py`: automated tests.
- `report.pdf`: the required brief report; `report.md` is its editable text version.

## Use in Phase 2

```python
from lexer import Lexer

result = Lexer('int age = 20; age = age + 1;').scan()
if result.errors:
    for error in result.errors:
        print(error)
else:
    for token in result.tokens:
        print(token.type, token.lexeme, token.line, token.column)

print(result.symbols)  # {'age': 1}
```

Each token has a type, lexeme, line, column, and optional `symbol_id`. The token list ends with `EOF`. The symbol table maps each distinct identifier to a stable ID starting at 1; repeated names reuse that ID.

## Language rules

- Keywords follow the assignment list. `String` becomes `STRING_TYPE`, `boolean` becomes `BOOLEAN_TYPE`, and `true`/`false` become `BOOLEAN`.
- Names are case-sensitive and use ASCII letters, digits, and underscores; the first character cannot be a digit. `main` is an `IDENTIFIER` because it is absent from the reserved-word list, despite `MAIN` in the sample output.
- Integers and decimal fractions become `NUMBER`. Both quote styles produce `STRING`; quotes and backslash escapes are preserved.
- Arithmetic operators are `+ - * / %`; comparisons are `== != < <= > >=`; logical operators are `&& || !`; assignment is `=`. All nine required punctuation marks are supported.
- Whitespace and both comment styles are skipped. Lines and columns start at 1. Windows and Unix newlines are supported; a tab counts as one column.

Unknown characters and digit-led names are reported and skipped. Unclosed strings report the opening quote and recover at the next line. Unclosed block comments report their opening position. Every error includes its line and column. `total-marks` is scanned as subtraction; `student@id` reports the illegal `@`.

See `report.md` for the full token list and implementation notes. Syntax and type checking belong to later phases.
