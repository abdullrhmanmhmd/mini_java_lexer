"""A character-by-character lexer for Mini Java.

Run: python lexer.py inputs/sample.txt
API: result = Lexer(source).scan()
"""

import sys
from dataclasses import dataclass
from pathlib import Path


KEYWORDS = {
    "class": "CLASS", "public": "PUBLIC", "static": "STATIC",
    "void": "VOID", "int": "INT", "float": "FLOAT",
    "boolean": "BOOLEAN_TYPE", "char": "CHAR", "String": "STRING_TYPE",
    "if": "IF", "else": "ELSE", "while": "WHILE", "for": "FOR",
    "return": "RETURN",
}
DELIMITERS = {
    "(": "LPAR", ")": "RPAR", "{": "LCUR", "}": "RCUR",
    "[": "LSQU", "]": "RSQU", ";": "SEMICOLON", ",": "COMMA", ".": "DOT",
}
TWO_CHAR_OPERATORS = {"==", "!=", "<=", ">=", "&&", "||"}
ONE_CHAR_OPERATORS = {
    **{op: "MATHOP" for op in "+-*/%"},
    **{op: "LOGOP" for op in "<>!"},
    "=": "ASSIGN",
}


@dataclass(frozen=True)
class Token:
    type: str
    lexeme: str
    line: int
    column: int
    symbol_id: int | None = None


@dataclass(frozen=True)
class LexicalError:
    line: int
    column: int
    message: str

    def __str__(self) -> str:
        return f"Error: {self.message} at line {self.line}, column {self.column}."


@dataclass
class ScanResult:
    tokens: list[Token]
    symbols: dict[str, int]
    errors: list[LexicalError]


def is_letter(character: str) -> bool:
    return "a" <= character <= "z" or "A" <= character <= "Z"


def is_digit(character: str) -> bool:
    return "0" <= character <= "9"


def is_identifier_start(character: str) -> bool:
    return is_letter(character) or character == "_"


def is_identifier_part(character: str) -> bool:
    return is_identifier_start(character) or is_digit(character)


class Lexer:
    """Lines and columns start at 1. Each identifier gets one symbol ID."""

    def __init__(self, source: str):
        # Treat Windows and Unix line endings the same.
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self.errors: list[LexicalError] = []
        self.symbols: dict[str, int] = {}
        self._result: ScanResult | None = None

    def _peek(self, offset: int = 0) -> str:
        index = self.index + offset
        return self.source[index] if index < len(self.source) else ""

    def _advance(self) -> str:
        character = self.source[self.index]
        self.index += 1
        if character == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return character

    def _emit(self, kind: str, start: int, line: int, column: int) -> None:
        lexeme = self.source[start:self.index]
        symbol_id = None
        if kind == "IDENTIFIER":
            if lexeme not in self.symbols:
                self.symbols[lexeme] = len(self.symbols) + 1
            symbol_id = self.symbols[lexeme]
        self.tokens.append(Token(kind, lexeme, line, column, symbol_id))

    def _error(self, message: str, line: int, column: int) -> None:
        self.errors.append(LexicalError(line, column, message))

    def _scan_identifier(self, start: int, line: int, column: int) -> None:
        while is_identifier_part(self._peek()):
            self._advance()
        lexeme = self.source[start:self.index]
        kind = "BOOLEAN" if lexeme in ("true", "false") else KEYWORDS.get(lexeme, "IDENTIFIER")
        self._emit(kind, start, line, column)

    def _scan_number(self, start: int, line: int, column: int) -> None:
        while is_digit(self._peek()):
            self._advance()
        if self._peek() == "." and is_digit(self._peek(1)):
            self._advance()
            while is_digit(self._peek()):
                self._advance()
        # Consume an entire malformed word so the parser sees no valid prefix.
        if is_identifier_start(self._peek()):
            while is_identifier_part(self._peek()):
                self._advance()
            lexeme = self.source[start:self.index]
            self._error(f"invalid identifier {lexeme!r}", line, column)
        else:
            self._emit("NUMBER", start, line, column)

    def _scan_string(self, start: int, line: int, column: int) -> None:
        quote = self._advance()
        while self._peek():
            character = self._peek()
            if character == "\n":
                break
            if character == quote:
                self._advance()
                self._emit("STRING", start, line, column)
                return
            if character == "\\":
                self._advance()
                if self._peek() and self._peek() != "\n":
                    self._advance()
            else:
                self._advance()
        self._error("unclosed string literal starting", line, column)

    def _skip_block_comment(self, line: int, column: int) -> None:
        self._advance()
        self._advance()
        while self._peek():
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        self._error("unclosed comment starting", line, column)

    def scan(self) -> ScanResult:
        if self._result is not None:
            return self._result
        while self.index < len(self.source):
            character = self._peek()
            start, line, column = self.index, self.line, self.column
            if character in " \t\n\f\v":
                self._advance()
            elif character == "/" and self._peek(1) == "/":
                while self._peek() and self._peek() != "\n":
                    self._advance()
            elif character == "/" and self._peek(1) == "*":
                self._skip_block_comment(line, column)
            elif is_identifier_start(character):
                self._scan_identifier(start, line, column)
            elif is_digit(character):
                self._scan_number(start, line, column)
            elif character in ("'", '"'):
                self._scan_string(start, line, column)
            elif self.source[self.index:self.index + 2] in TWO_CHAR_OPERATORS:
                self._advance()
                self._advance()
                self._emit("LOGOP", start, line, column)
            elif character in ONE_CHAR_OPERATORS:
                self._advance()
                self._emit(ONE_CHAR_OPERATORS[character], start, line, column)
            elif character in DELIMITERS:
                self._advance()
                self._emit(DELIMITERS[character], start, line, column)
            else:
                self._error(f"invalid character {character!r}", line, column)
                self._advance()
        self.tokens.append(Token("EOF", "", self.line, self.column))
        self._result = ScanResult(self.tokens, self.symbols, self.errors)
        return self._result


def print_result(result: ScanResult) -> None:
    print("TOKENS")
    for token in result.tokens:
        print(f"Lexeme: {token.lexeme!r}, Token: {token.type}, "
              f"Line: {token.line}, Column: {token.column}")
    print("\nSYMBOL TABLE")
    print("ID  Identifier")
    for name, symbol_id in result.symbols.items():
        print(f"{symbol_id:<3} {name}")
    print("\nERRORS")
    if not result.errors:
        print("None.")
    for error in result.errors:
        print(error)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python lexer.py <input.txt>", file=sys.stderr)
        return 2
    try:
        source = Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        print(f"Cannot read input: {error}", file=sys.stderr)
        return 2
    result = Lexer(source).scan()
    print_result(result)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
