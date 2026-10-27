"""Behavioral scanner tests. Run in this folder: python -m unittest -v."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lexer import Lexer

LEXER_PATH = Path(__file__).resolve().parent / "lexer.py"


class LexerTests(unittest.TestCase):
    def scan(self, source):
        return Lexer(source).scan()

    def pairs(self, result):
        return [(t.type, t.lexeme) for t in result.tokens if t.type != "EOF"]

    def clean(self, result):
        self.assertEqual(result.errors, [])

    def test_empty_source(self):
        r = self.scan("")
        self.clean(r)
        self.assertEqual(len(r.tokens), 1)
        t = r.tokens[0]
        self.assertEqual((t.type, t.lexeme, t.line, t.column), ("EOF", "", 1, 1))
        self.assertIsNone(t.symbol_id)
        self.assertEqual(r.symbols, {})

    def test_all_keywords(self):
        r = self.scan("class public static void int float boolean char String if else while for return")
        self.assertEqual([t.type for t in r.tokens[:-1]], [
            "CLASS", "PUBLIC", "STATIC", "VOID", "INT", "FLOAT", "BOOLEAN_TYPE",
            "CHAR", "STRING_TYPE", "IF", "ELSE", "WHILE", "FOR", "RETURN"])
        self.clean(r)
        self.assertEqual(r.symbols, {})

    def test_case_sensitivity_and_main_policy(self):
        r = self.scan("class Class String string main")
        self.assertEqual(self.pairs(r), [
            ("CLASS", "class"), ("IDENTIFIER", "Class"), ("STRING_TYPE", "String"),
            ("IDENTIFIER", "string"), ("IDENTIFIER", "main")])
        self.clean(r)

    def test_boolean_literals(self):
        r = self.scan("true false True FALSE")
        self.assertEqual(self.pairs(r), [("BOOLEAN", "true"), ("BOOLEAN", "false"),
                                       ("IDENTIFIER", "True"), ("IDENTIFIER", "FALSE")])
        self.clean(r)

    def test_identifier_forms(self):
        names = ["age", "studentName", "total_marks", "x1", "_count", "_", "a0_b"]
        r = self.scan(" ".join(names))
        self.assertEqual(self.pairs(r), [("IDENTIFIER", n) for n in names])
        self.clean(r)

    def test_keyword_prefixes(self):
        names = ["classroom", "int2", "StringBuilder", "trueValue", "false_"]
        r = self.scan(" ".join(names))
        self.assertEqual(self.pairs(r), [("IDENTIFIER", n) for n in names])
        self.clean(r)

    def test_integer_and_decimal_numbers(self):
        values = ["0", "10", "001", "25.5", "0.0", "1234567890"]
        r = self.scan(" ".join(values))
        self.assertEqual(self.pairs(r), [("NUMBER", n) for n in values])
        self.clean(r)

    def test_signs_and_dots_are_separate(self):
        r = self.scan("-5 +2 .5 10. 1.2.3")
        self.assertEqual(self.pairs(r), [
            ("MATHOP", "-"), ("NUMBER", "5"), ("MATHOP", "+"), ("NUMBER", "2"),
            ("DOT", "."), ("NUMBER", "5"), ("NUMBER", "10"), ("DOT", "."),
            ("NUMBER", "1.2"), ("DOT", "."), ("NUMBER", "3")])
        self.clean(r)

    def test_invalid_digit_start_names_have_no_partial_tokens(self):
        r = self.scan("12abc 1_name 25.5abc 1e3;")
        self.assertEqual(self.pairs(r), [("SEMICOLON", ";")])
        self.assertEqual([(e.line, e.column) for e in r.errors], [(1, 1), (1, 7), (1, 14), (1, 22)])
        for error, name in zip(r.errors, ["12abc", "1_name", "25.5abc", "1e3"]):
            self.assertIn("invalid identifier", error.message.lower())
            self.assertIn(name, error.message)
        self.assertEqual(r.symbols, {})

    def test_arithmetic_assignment_and_comparison(self):
        r = self.scan("+ - * / % = < > <= >= == !=")
        self.assertEqual(self.pairs(r), [("MATHOP", c) for c in "+-*/%"] +
                         [("ASSIGN", "=")] + [("LOGOP", c) for c in ["<", ">", "<=", ">=", "==", "!="]])
        self.clean(r)

    def test_longest_operator_match(self):
        r = self.scan("a>=b!=c==d<=e")
        self.assertEqual([t.lexeme for t in r.tokens[:-1]], ["a", ">=", "b", "!=", "c", "==", "d", "<=", "e"])
        self.clean(r)

    def test_logical_operators(self):
        r = self.scan("!a&&b||false")
        self.assertEqual(self.pairs(r), [("LOGOP", "!"), ("IDENTIFIER", "a"), ("LOGOP", "&&"),
                                       ("IDENTIFIER", "b"), ("LOGOP", "||"), ("BOOLEAN", "false")])
        self.clean(r)

    def test_lone_ampersand_and_pipe_are_invalid(self):
        r = self.scan("&&& |||")
        self.assertEqual(self.pairs(r), [("LOGOP", "&&"), ("LOGOP", "||")])
        self.assertEqual([(e.line, e.column) for e in r.errors], [(1, 3), (1, 7)])

    def test_all_delimiters(self):
        r = self.scan("(){}[];,.")
        self.assertEqual(self.pairs(r), list(zip(
            ["LPAR", "RPAR", "LCUR", "RCUR", "LSQU", "RSQU", "SEMICOLON", "COMMA", "DOT"], "(){}[];,.")))
        self.clean(r)

    def test_quoted_values(self):
        values = ['"Hello"', "'A'", "'many characters'", '""', "''"]
        r = self.scan(" ".join(values))
        self.assertEqual(self.pairs(r), [("STRING", s) for s in values])
        self.clean(r)

    def test_escaped_quote_and_backslash_preserved(self):
        source = r'"a\"b\\c"'
        r = self.scan(source)
        self.assertEqual(self.pairs(r), [("STRING", source)])
        self.clean(r)

    def test_comment_markers_in_strings(self):
        source = '"// /* @ 1name */"'
        r = self.scan(source)
        self.assertEqual(self.pairs(r), [("STRING", source)])
        self.clean(r)
        self.assertEqual(r.symbols, {})

    def test_single_line_comments_and_comment_at_eof(self):
        r = self.scan("a// @ discarded\nb // no final newline")
        self.assertEqual(self.pairs(r), [("IDENTIFIER", "a"), ("IDENTIFIER", "b")])
        self.assertEqual((r.tokens[1].line, r.tokens[1].column), (2, 1))
        self.clean(r)

    def test_block_comment_and_positions(self):
        r = self.scan("/* a\n b */x+1")
        self.assertEqual(self.pairs(r), [("IDENTIFIER", "x"), ("MATHOP", "+"), ("NUMBER", "1")])
        self.assertEqual((r.tokens[0].line, r.tokens[0].column), (2, 6))
        self.assertEqual((r.tokens[-1].line, r.tokens[-1].column), (2, 9))
        self.clean(r)

    def test_comments_separate_names(self):
        r = self.scan("one/**/two/* @ \" ' */three")
        self.assertEqual([t.lexeme for t in r.tokens[:-1]], ["one", "two", "three"])
        self.clean(r)

    def test_unterminated_comment_reports_start(self):
        r = self.scan("\n  /* no end\n still a comment")
        self.assertEqual(self.pairs(r), [])
        self.assertEqual(len(r.errors), 1)
        self.assertEqual((r.errors[0].line, r.errors[0].column), (2, 3))
        self.assertIn("comment", r.errors[0].message.lower())
        self.assertEqual(r.tokens[-1].type, "EOF")

    def test_unclosed_string_at_eof(self):
        r = self.scan('String name = "Ali;')
        self.assertEqual(len(r.errors), 1)
        self.assertEqual((r.errors[0].line, r.errors[0].column), (1, 15))
        self.assertIn("string", r.errors[0].message.lower())
        self.assertNotIn("STRING", [t.type for t in r.tokens])

    def test_unclosed_string_recovers_at_next_line(self):
        r = self.scan('"bad\nint age=5;')
        self.assertEqual(len(r.errors), 1)
        self.assertEqual((r.errors[0].line, r.errors[0].column), (1, 1))
        self.assertEqual(self.pairs(r), [("INT", "int"), ("IDENTIFIER", "age"),
                                       ("ASSIGN", "="), ("NUMBER", "5"), ("SEMICOLON", ";")])
        self.assertEqual((r.tokens[0].line, r.tokens[0].column), (2, 1))

    def test_backslash_cannot_escape_actual_line_break(self):
        r = self.scan('"bad\\' + "\nnext")
        self.assertEqual(len(r.errors), 1)
        self.assertEqual(self.pairs(r), [("IDENTIFIER", "next")])
        self.assertEqual((r.tokens[0].line, r.tokens[0].column), (2, 1))

    def test_unknown_character_position_and_recovery(self):
        r = self.scan("int x = 10 @ 5;")
        self.assertEqual(len(r.errors), 1)
        self.assertEqual((r.errors[0].line, r.errors[0].column), (1, 12))
        self.assertIn("@", r.errors[0].message)
        self.assertEqual([t.lexeme for t in r.tokens[:-1]], ["int", "x", "=", "10", "5", ";"])

    def test_subtraction_and_invalid_at_sign(self):
        r = self.scan("total-marks student@id")
        self.assertEqual(self.pairs(r), [("IDENTIFIER", "total"), ("MATHOP", "-"),
                                       ("IDENTIFIER", "marks"), ("IDENTIFIER", "student"), ("IDENTIFIER", "id")])
        self.assertEqual([(e.line, e.column) for e in r.errors], [(1, 20)])

    def test_line_endings_and_tab_column_policy(self):
        r = self.scan("a\r\nb\rc\nd\t=")
        self.assertEqual([(t.lexeme, t.line, t.column) for t in r.tokens[:-1]],
                         [("a", 1, 1), ("b", 2, 1), ("c", 3, 1), ("d", 4, 1), ("=", 4, 3)])
        self.clean(r)

    def test_symbol_reuse_and_case_sensitivity(self):
        r = self.scan("Alpha alpha Alpha _x Alpha")
        self.assertEqual(r.symbols, {"Alpha": 1, "alpha": 2, "_x": 3})
        self.assertEqual([t.symbol_id for t in r.tokens[:-1]], [1, 2, 1, 3, 1])
        self.clean(r)

    def test_only_identifiers_enter_symbols(self):
        r = self.scan('String s="x"; boolean b=true; // ignoredName')
        self.assertEqual(r.symbols, {"s": 1, "b": 2})
        for token in r.tokens:
            if token.type != "IDENTIFIER":
                self.assertIsNone(token.symbol_id)
        self.clean(r)

    def test_assignment_sample_stream_and_symbols(self):
        source = (Path(__file__).parent / "inputs" / "sample.txt").read_text(encoding="utf-8-sig")
        r = self.scan(source)
        expected_lexemes = [
            "class", "Student", "{", "public", "static", "void", "main", "(", ")", "{",
            "int", "age", "=", "20", ";", "float", "grade", "=", "85.5", ";",
            "String", "name", "=", '"Ali"', ";", "if", "(", "grade", ">=", "50", ")", "{",
            "grade", "=", "grade", "+", "5", ";", "}", "}", "}"]
        self.assertEqual([t.lexeme for t in r.tokens[:-1]], expected_lexemes)
        self.assertEqual(len(r.tokens) - 1, 41)
        self.assertEqual(r.symbols, {"Student": 1, "main": 2, "age": 3, "grade": 4, "name": 5})
        self.clean(r)

    def test_scan_is_idempotent(self):
        lexer = Lexer("int x=1; @")
        first = lexer.scan()
        second = lexer.scan()
        self.assertEqual(first, second)
        self.assertEqual(sum(t.type == "EOF" for t in second.tokens), 1)
        self.assertEqual(len(second.errors), 1)
        self.assertEqual(second.symbols, {"x": 1})

    def test_cli_readable_output_from_another_directory(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            (root / "program.txt").write_text("int total=5;", encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(LEXER_PATH), "program.txt"],
                cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("Token: INT", process.stdout)
            self.assertIn("Token: EOF", process.stdout)
            self.assertIn("SYMBOL TABLE", process.stdout)
            self.assertIn("total", process.stdout)
            self.assertIn("ERRORS\nNone.", process.stdout)

    def test_cli_lexical_error_exit_status_and_position(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            (root / "bad.txt").write_text("int x=1;\n@", encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(LEXER_PATH), "bad.txt"],
                cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 1, process.stderr)
            self.assertIn("Error: invalid character '@' at line 2, column 1.", process.stdout)

    def test_cli_missing_file_exit_status(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            process = subprocess.run(
                [sys.executable, str(LEXER_PATH), "missing.txt"],
                cwd=directory, capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 2)
            self.assertIn("Cannot read input", process.stderr)
            self.assertEqual(process.stdout, "")

if __name__ == "__main__":
    unittest.main()
