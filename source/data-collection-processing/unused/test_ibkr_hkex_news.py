import ast
from pathlib import Path


# Load pure helpers without requiring IBKR's separately distributed SDK in CI.
source = Path(__file__).with_name("ibkr_hkex_news.py").read_text()
tree = ast.parse(source)
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {
    "normalize_symbol", "ibkr_symbol", "clean_article_text"
}]
namespace = {"re": __import__("re")}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "helpers", "exec"), namespace)


def test_symbol_normalization():
    assert namespace["normalize_symbol"]("700") == "00700"
    assert namespace["ibkr_symbol"]("00700") == "700"


def test_invalid_symbol():
    try:
        namespace["normalize_symbol"]("0700.HK")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_clean_article_text():
    assert namespace["clean_article_text"]("<p>Hello&nbsp; world</p>\n") == "Hello&nbsp; world"
