import doctest
import math
import unittest
from pathlib import Path

import jsun.decoder
import jsun.scanner

from jsun import decode, decode_file
from jsun.exc import (
    DecodeError,
    ExpectedKeyError,
    ExpectedValueError,
    ExtraneousDataError,
    ScanStringError,
    UnexpectedCharError,
    UnknownCharError,
    UnmatchedBracketError,
    INIDecodeError,
)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(jsun.decoder))
    tests.addTests(doctest.DocTestSuite(jsun.obj))
    tests.addTests(doctest.DocTestSuite(jsun.scanner))
    return tests


class TestJSONishScanner(unittest.TestCase):
    def decode(self, string, object_converter=None, enable_extras=True):
        return decode(
            string,
            object_converter=object_converter,
            enable_extras=enable_extras,
        )

    def test_empty_string_is_none(self):
        result = self.decode("")
        self.assertIsNone(result)
        self.assertRaises(ExpectedValueError, self.decode, " ")

    def test_inf(self):
        self.assertEqual(self.decode("inf"), math.inf)
        self.assertEqual(self.decode("+inf"), math.inf)
        self.assertEqual(self.decode("-inf"), -math.inf)

    def test_nan(self):
        self.assertTrue(math.isnan(float("nan")))
        self.assertTrue(math.isnan(self.decode("nan")))
        self.assertTrue(math.isnan(self.decode("+nan")))
        self.assertTrue(math.isnan(self.decode("-nan")))

    def test_empty_object(self):
        self.assertEqual(self.decode("{}"), {})

    def test_empty_string(self):
        self.assertIsNone(self.decode(""))
        self.assertRaises(ExpectedValueError, self.decode, "", enable_extras=False)

    def test_decode_multiline_object(self):
        self.assertEqual(self.decode("{\n\n\n}"), {})

    def test_empty_array(self):
        self.assertEqual(self.decode("[]"), [])

    def test_decode_multiline_array(self):
        self.assertEqual(self.decode("[\n\n\n]"), [])

    def test_simple_object(self):
        self.assertEqual(self.decode('{"a": 1}'), {"a": 1})

    def test_object_with_space_before_key(self):
        self.assertEqual(self.decode('{ "a": 1}'), {"a": 1})

    def test_unclosed_object(self):
        self.assertRaises(UnmatchedBracketError, self.decode, '{"a": 1')
        self.assertRaises(ExtraneousDataError, self.decode, '"a": 1}')

    def test_unclosed_array(self):
        self.assertRaises(UnmatchedBracketError, self.decode, "[1, 2")
        self.assertRaises(ExtraneousDataError, self.decode, "1, 2]")

    def test_nesting(self):
        result = self.decode('{ "1": 0b1, "2": [[1, 2]], }')
        self.assertEqual(result, {"1": 1, "2": [[1, 2]]})

    def test_comments(self):
        self.decode(
            """
            // This is a JSON object
            {
                // "a" is really special
                "a": 1,
                "b": 2,  // end-of-line comment
            }
            """
        )
        self.assertEqual(self.decode('"//"'), "//")
        self.assertRaises(ExpectedValueError, self.decode, "//{}")
        self.assertRaises(ExpectedKeyError, self.decode, "{//}")
        self.assertRaises(ExpectedValueError, self.decode, '{"a": //}')
        self.assertRaises(UnmatchedBracketError, self.decode, '{"a": 1//}')

    def test_comments_with_extra_features_disabled(self):
        doc = """
        // Comment
        {
            // Comment
            "a": 1,
            "b": 2,
        }
        """
        self.assertRaises(UnknownCharError, self.decode, doc, enable_extras=False)

    def test_trailing_commas_with_extra_features_disabled(self):
        self.assertRaises(
            UnexpectedCharError, self.decode, "[1, 2,]", enable_extras=False
        )


class TestJSONishAgainstJSONCheckerFiles(unittest.TestCase):
    def decode_file(self, name, enable_extras=True):
        file_name = f"{name}.json"
        path = Path(__file__).parent / "json_checker_files" / file_name
        return decode_file(path, enable_extras=enable_extras)

    def test_pass1_with_extra_features_disabled(self):
        # Standard JSON shouldn't require any extra features.
        self.decode_file("pass1", enable_extras=False)

    def test_pass1_with_extra_features_enabled(self):
        # JSONish's extra features are a superset of the standard
        # features, so there shouldn't be any issues parsing a standard
        # JSON doc with them turned on.
        self.decode_file("pass1")

    def test_pass2_with_extra_features_disabled(self):
        self.decode_file("pass2", enable_extras=False)

    def test_pass2_with_extra_features_enabled(self):
        self.decode_file("pass2")

    def test_pass3_with_extra_features_disabled(self):
        self.decode_file("pass3", enable_extras=False)

    def test_pass3_with_extra_features_enabled(self):
        self.decode_file("pass3")

    def test_expected_failures(self):
        root = Path(__file__).parent / "json_checker_files"
        paths = root.glob("fail*.json")
        for path in paths:
            if path.stem in ("fail1", "fail18"):
                # These match stdlib behavior (i.e., they don't fail)
                decode_file(path)
                decode_file(path, enable_extras=False)

            elif path.stem in (
                "fail15",
                "fail17",
                "fail25",
                "fail26",
                "fail27",
                "fail28",
            ):
                self.assertRaises(
                    ScanStringError, decode_file, path, enable_extras=False
                )

            else:
                # TODO: Check for specific exceptions?
                with self.subTest(path.name):
                    self.assertRaises(
                        DecodeError, decode_file, path, enable_extras=False
                    )


class TestDecodeINI(unittest.TestCase):
    def test_decode_ini(self):
        config = """\
[section.one]
a.b = 1
x.y = 2
[section.two]
a.b = 3
x.y = 4
[other]
a = 1
b = 2
[x.(not.split)]
(x.y) = 1
(also.not.split).x = 2
        """
        result = decode(config, ini=True)
        self.assertEqual(
            result,
            {
                "section": {
                    "one": {"a": {"b": 1}, "x": {"y": 2}},
                    "two": {"a": {"b": 3}, "x": {"y": 4}},
                },
                "other": {
                    "a": 1,
                    "b": 2,
                },
                "x": {
                    "not.split": {
                        "x.y": 1,
                        "also.not.split": {
                            "x": 2,
                        },
                    },
                },
            },
        )

    def test_bad_section_names(self):
        bad_names = [
            "[section)]",
            "[(section]",
            "[x(yz)]",
            "[(xy)z]",
            "[)(abc)]",
            "[(abc)(]",
            "[(abc))]",
            "[((xyz))]",
        ]
        for name in bad_names:
            with self.subTest(name=name):
                self.assertRaises(INIDecodeError, decode, name, ini=True)

    def test_nested_sections(self):
        path = Path(__file__).parent / "nested.ini"
        obj = decode_file(path)
        self.assertEqual(
            obj,
            {
                "envs": {
                    "base": {"debug": False},
                    "development": {
                        "debug": True,
                        "database": {
                            "host": "localhost",
                            "name": "xyz_dev",
                        },
                    },
                    "production": {
                        "database": {
                            "host": "db.example.com",
                            "name": "xyz",
                        },
                    },
                }
            },
        )
