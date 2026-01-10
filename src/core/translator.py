"""Translator wrapper with engine fallback (Google -> Bing).

Uses the `translators` package's `translate_text` function and exposes a
small, testable `Translator` class for the app.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import translators as ts


class TranslatorError(Exception):
    pass


class Translator:
    """Translate text from Portuguese (pt) to supported target languages.

    Behavior:
    - Returns empty string for whitespace-only input.
    - Tries engines in order: Google then Bing, with a 10s timeout each.
    - Tracks last engine used in `self._last_engine`.
    """

    SUPPORTED_LANGUAGES: Dict[str, str] = {
        "English": "en",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Italian": "it",
        "Japanese": "ja",
        "Chinese": "zh",
    }

    ENGINES: List[str] = ["google", "bing"]

    def __init__(self) -> None:
        self._last_engine: Optional[str] = None

    def translate(
        self, text: str, target_language: str = "English", source_language: str = "pt"
    ) -> str:
        """Translate `text` from `source_language` to `target_language`.

        `target_language` may be a friendly name from `SUPPORTED_LANGUAGES`
        or a language code.
        """
        if not isinstance(text, str):
            raise TranslatorError("text must be a str")

        if text.strip() == "":
            return ""

        # Resolve target code
        target_code = None
        if target_language in self.SUPPORTED_LANGUAGES:
            target_code = self.SUPPORTED_LANGUAGES[target_language]
        else:
            # allow passing language code directly
            if target_language in self.SUPPORTED_LANGUAGES.values():
                target_code = target_language
        if not target_code:
            raise TranslatorError(f"Unsupported target language: {target_language}")

        last_exc: Optional[Exception] = None

        for engine in self.ENGINES:
            try:
                # translators.translate_text signature:
                # translate_text(query_text, translator='bing', from_language='auto', to_language='en', **kwargs)
                result = ts.translate_text(
                    query_text=text,
                    translator=engine,
                    from_language=source_language,
                    to_language=target_code,
                    timeout=10,
                )
                self._last_engine = engine
                # result may be dict if is_detail_result, ensure string
                if isinstance(result, dict):
                    # try to extract best string representation
                    result = str(result)
                return result
            except Exception as e:  # keep broad to allow network/3rd-party failures
                last_exc = e
                # try next engine
                continue

        # all engines failed
        raise TranslatorError(f"All translation engines failed: {last_exc}")

    def get_last_engine(self) -> Optional[str]:
        return self._last_engine

    @classmethod
    def get_available_languages(cls) -> List[str]:
        return list(cls.SUPPORTED_LANGUAGES.keys())
