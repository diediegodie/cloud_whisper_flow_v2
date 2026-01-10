"""Basic translator integration tests.

Note: these tests perform real network calls and require an internet
connection. They may be skipped in CI environments.
"""

from src.core.translator import Translator, TranslatorError


def test_available_languages() -> None:
    langs = Translator.get_available_languages()
    print("Available languages:", langs)
    assert "English" in langs
    assert "Spanish" in langs
    assert len(langs) == 7


def test_empty_text() -> None:
    t = Translator()
    assert t.translate("", "English") == ""
    assert t.translate("   ", "English") == ""


def test_basic_translation() -> None:
    t = Translator()
    res = t.translate("Olá, como você está?", "English")
    print("Translated (basic):", res)
    print("Engine used:", t.get_last_engine())
    assert isinstance(res, str)
    assert res.strip() != ""


def test_multiple_languages() -> None:
    t = Translator()
    results = {}
    for lang in ("English", "Spanish", "French"):
        results[lang] = t.translate("Bom dia", lang)
        print(f"{lang}: {results[lang]}")

    assert all(isinstance(v, str) and v.strip() != "" for v in results.values())


if __name__ == "__main__":
    print("Note: These tests require internet connection")
    test_available_languages()
    test_empty_text()
    try:
        test_basic_translation()
        test_multiple_languages()
    except TranslatorError as e:
        print("Translation tests failed (network/service):", e)
    else:
        print("All translator tests passed!")
