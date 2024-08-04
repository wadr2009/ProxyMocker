import unittest

from mock_service import parser


class TestParserBasic(unittest.TestCase):

    def test_parse_string_value(self):
        self.assertEqual(parser.parse_string_value("123"), 123)
        self.assertEqual(parser.parse_string_value("12.3"), 12.3)
        self.assertEqual(parser.parse_string_value("a123"), "a123")
        self.assertEqual(parser.parse_string_value("$var"), "$var")
        self.assertEqual(parser.parse_string_value("${func}"), "${func}")



    def test_parse_function_params(self):
        self.assertEqual(parser.parse_function_params(""), {"args": [], "kwargs": {}})
        self.assertEqual(parser.parse_function_params("5"), {"args": [5], "kwargs": {}})
        self.assertEqual(
            parser.parse_function_params("1, 2"), {"args": [1, 2], "kwargs": {}}
        )
        self.assertEqual(
            parser.parse_function_params("a=1, b=2"),
            {"args": [], "kwargs": {"a": 1, "b": 2}},
        )
        self.assertEqual(
            parser.parse_function_params("a= 1, b =2"),
            {"args": [], "kwargs": {"a": 1, "b": 2}},
        )
        self.assertEqual(
            parser.parse_function_params("1, 2, a=3, b=4"),
            {"args": [1, 2], "kwargs": {"a": 3, "b": 4}},
        )
        self.assertEqual(
            parser.parse_function_params("$request, 123"),
            {"args": ["$request", 123], "kwargs": {}},
        )
        self.assertEqual(parser.parse_function_params("  "), {"args": [], "kwargs": {}})
        self.assertEqual(
            parser.parse_function_params("hello world, a=3, b=4"),
            {"args": ["hello world"], "kwargs": {"a": 3, "b": 4}},
        )
        self.assertEqual(
            parser.parse_function_params("$request, 12 3"),
            {"args": ["$request", "12 3"], "kwargs": {}},
        )



    def test_parse_data_string_with_variables(self):
        variables_mapping = {
            "var_1": "abc",
            "var_2": "def",
            "var_3": 123,
            "var_4": {"a": 1},
            "var_5": True,
            "var_6": None,
        }
        self.assertEqual(parser.parse_data("$var_1", variables_mapping), "abc")
        self.assertEqual(parser.parse_data("${var_1}", variables_mapping), "abc")
        self.assertEqual(parser.parse_data("var_1", variables_mapping), "var_1")
        self.assertEqual(parser.parse_data("$var_1#XYZ", variables_mapping), "abc#XYZ")
        self.assertEqual(
            parser.parse_data("${var_1}#XYZ", variables_mapping), "abc#XYZ"
        )
        self.assertEqual(
            parser.parse_data("/$var_1/$var_2/var3", variables_mapping), "/abc/def/var3"
        )
        self.assertEqual(parser.parse_data("$var_3", variables_mapping), 123)
        self.assertEqual(parser.parse_data("$var_4", variables_mapping), {"a": 1})
        self.assertEqual(parser.parse_data("$var_5", variables_mapping), True)
        self.assertEqual(parser.parse_data("abc$var_5", variables_mapping), "abcTrue")
        self.assertEqual(
            parser.parse_data("abc$var_4", variables_mapping), "abc{'a': 1}"
        )
        self.assertEqual(parser.parse_data("$var_6", variables_mapping), None)


        self.assertEqual(
            parser.parse_data(["$var_1", "$var_2"], variables_mapping), ["abc", "def"]
        )
        self.assertEqual(
            parser.parse_data({"$var_1": "$var_2"}, variables_mapping), {"abc": "def"}
        )

        # format: $var
        value = parser.parse_data("ABC$var_1", variables_mapping)
        self.assertEqual(value, "ABCabc")

        value = parser.parse_data("ABC$var_1$var_3", variables_mapping)
        self.assertEqual(value, "ABCabc123")

        value = parser.parse_data("ABC$var_1/$var_3", variables_mapping)
        self.assertEqual(value, "ABCabc/123")

        value = parser.parse_data("ABC$var_1/", variables_mapping)
        self.assertEqual(value, "ABCabc/")

        value = parser.parse_data("ABC$var_1$", variables_mapping)
        self.assertEqual(value, "ABCabc$")

        value = parser.parse_data("ABC$var_1/123$var_1/456", variables_mapping)
        self.assertEqual(value, "ABCabc/123abc/456")

        value = parser.parse_data("ABC$var_1/$var_2/$var_1", variables_mapping)
        self.assertEqual(value, "ABCabc/def/abc")

        value = parser.parse_data("func1($var_1, $var_3)", variables_mapping)
        self.assertEqual(value, "func1(abc, 123)")

        # format: ${var}
        value = parser.parse_data("ABC${var_1}", variables_mapping)
        self.assertEqual(value, "ABCabc")

        value = parser.parse_data("ABC${var_1}${var_3}", variables_mapping)
        self.assertEqual(value, "ABCabc123")

        value = parser.parse_data("ABC${var_1}/${var_3}", variables_mapping)
        self.assertEqual(value, "ABCabc/123")

        value = parser.parse_data("ABC${var_1}/", variables_mapping)
        self.assertEqual(value, "ABCabc/")

        value = parser.parse_data("ABC${var_1}123", variables_mapping)
        self.assertEqual(value, "ABCabc123")

        value = parser.parse_data("ABC${var_1}/123${var_1}/456", variables_mapping)
        self.assertEqual(value, "ABCabc/123abc/456")

        value = parser.parse_data("ABC${var_1}/${var_2}/${var_1}", variables_mapping)
        self.assertEqual(value, "ABCabc/def/abc")

        value = parser.parse_data("func1(${var_1}, ${var_3})", variables_mapping)
        self.assertEqual(value, "func1(abc, 123)")

    def test_parse_data_multiple_identical_variables(self):
        variables_mapping = {
            "var_1": "abc",
            "var_2": "def",
        }
        self.assertEqual(
            parser.parse_data("/$var_1/$var_2/$var_1", variables_mapping),
            "/abc/def/abc",
        )

        variables_mapping = {"userid": 100, "data": 1498}
        content = "/users/$userid/training/$data?userId=$userid&data=$data"
        self.assertEqual(
            parser.parse_data(content, variables_mapping),
            "/users/100/training/1498?userId=100&data=1498",
        )

        variables_mapping = {"user": 100, "userid": 1000, "data": 1498}
        content = "/users/$user/$userid/$data?userId=$userid&data=$data"
        self.assertEqual(
            parser.parse_data(content, variables_mapping),
            "/users/100/1000/1498?userId=1000&data=1498",
        )

    def test_parse_data_string_with_functions(self):
        import random
        import string

        functions_mapping = {
            "gen_random_string": lambda str_len: "".join(
                random.choice(string.ascii_letters + string.digits)
                for _ in range(str_len)
            )
        }
        result = parser.parse_data(
            "${gen_random_string(5)}", functions_mapping=functions_mapping
        )
        self.assertEqual(len(result), 5)

        functions_mapping["add_two_nums"] = lambda a, b=1: a + b
        self.assertEqual(
            parser.parse_data(
                "${add_two_nums(1)}", functions_mapping=functions_mapping
            ),
            2,
        )
        self.assertEqual(
            parser.parse_data(
                "${add_two_nums(1, 2)}", functions_mapping=functions_mapping
            ),
            3,
        )
        self.assertEqual(
            parser.parse_data(
                "/api/${add_two_nums(1, 2)}", functions_mapping=functions_mapping
            ),
            "/api/3",
        )

        with self.assertRaises(RuntimeError):
            parser.parse_data("/api/${gen_md5(abc)}")

        variables_mapping = {
            "var_1": "abc",
            "var_2": "def",
            "var_3": 123,
            "var_4": {"a": 1},
            "var_5": True,
            "var_6": None,
        }
        functions_mapping = {"func1": lambda x, y: str(x) + str(y)}

        value = parser.parse_data(
            "${func1($var_1, $var_3)}", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "abc123")

        value = parser.parse_data(
            "ABC${func1($var_1, $var_3)}DE", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "ABCabc123DE")

        value = parser.parse_data(
            "ABC${func1($var_1, $var_3)}$var_5", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "ABCabc123True")

        value = parser.parse_data(
            "ABC${func1($var_1, $var_3)}DE$var_4", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "ABCabc123DE{'a': 1}")

        value = parser.parse_data(
            "ABC$var_5${func1($var_1, $var_3)}", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "ABCTrueabc123")

        value = parser.parse_data(
            "ABC${ord(a)}DEF${len(abcd)}", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "ABC97DEF4")

    def test_parse_data_func_var_duplicate(self):
        variables_mapping = {
            "var_1": "abc",
            "var_2": "def",
            "var_3": 123,
            "var_4": {"a": 1},
            "var_5": True,
            "var_6": None,
        }
        functions_mapping = {"func1": lambda x, y: str(x) + str(y)}
        value = parser.parse_data(
            "ABC${func1($var_1, $var_3)}--${func1($var_1, $var_3)}",
            variables_mapping,
            functions_mapping,
        )
        self.assertEqual(value, "ABCabc123--abc123")

        value = parser.parse_data(
            "ABC${func1($var_1, $var_3)}$var_1", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "ABCabc123abc")

        value = parser.parse_data(
            "ABC${func1($var_1, $var_3)}$var_1--${func1($var_1, $var_3)}$var_1",
            variables_mapping,
            functions_mapping,
        )
        self.assertEqual(value, "ABCabc123abc--abc123abc")

    def test_parse_data_func_abnormal(self):
        variables_mapping = {
            "var_1": "abc",
            "var_2": "def",
            "var_3": 123,
            "var_4": {"a": 1},
            "var_5": True,
            "var_6": None,
        }
        functions_mapping = {"func1": lambda x, y: str(x) + str(y)}

        # {
        value = parser.parse_data("ABC$var_1{", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABCabc{")

        value = parser.parse_data(
            "{ABC$var_1{}a}", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "{ABCabc{}a}")

        value = parser.parse_data(
            "AB{C$var_1{}a}", variables_mapping, functions_mapping
        )
        self.assertEqual(value, "AB{Cabc{}a}")

        # }
        value = parser.parse_data("ABC$var_1}", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABCabc}")

        # $$
        value = parser.parse_data("ABC$$var_1{", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABC$var_1{")

        # $$$
        value = parser.parse_data("ABC$$$var_1{", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABC$abc{")

        # $$$$
        value = parser.parse_data("ABC$$$$var_1{", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABC$$var_1{")

        # ${
        value = parser.parse_data("ABC$var_1${", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABCabc${")

        value = parser.parse_data("ABC$var_1${a", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABCabc${a")

        # $}
        value = parser.parse_data("ABC$var_1$}a", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABCabc$}a")

        # }{
        value = parser.parse_data("ABC$var_1}{a", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABCabc}{a")

        # {}
        value = parser.parse_data("ABC$var_1{}a", variables_mapping, functions_mapping)
        self.assertEqual(value, "ABCabc{}a")

