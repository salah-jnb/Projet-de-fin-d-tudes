"""Traduction sans clé API (via deep-translator → endpoint public Google Translate)."""

from deep_translator import GoogleTranslator


class FreeTranslateClient:
    """Alternative à Gemini pour le pipeline vocal / n8n : aucune GEMINI_API_KEY requise."""

    @staticmethod
    def _primary_lang(bcp47: str) -> str:
        return (bcp47 or "").strip().split("-")[0].lower()

    @staticmethod
    def _to_google_code(primary: str) -> str:
        if primary == "zh":
            return "zh-CN"
        if primary == "he":
            return "iw"
        return primary

    def translate_text(self, text: str, source_bcp47: str, target_bcp47: str) -> str:
        stripped = (text or "").strip()
        if not stripped:
            return text or ""

        s = self._to_google_code(self._primary_lang(source_bcp47))
        t = self._to_google_code(self._primary_lang(target_bcp47))
        if s == t:
            return text

        try:
            return GoogleTranslator(source=s, target=t).translate(stripped)
        except Exception as e:
            if s != "auto":
                try:
                    return GoogleTranslator(source="auto", target=t).translate(stripped)
                except Exception as e2:
                    raise RuntimeError(
                        f"Traduction échouée ({source_bcp47}→{target_bcp47}): {e2}"
                    ) from e2
            raise RuntimeError(
                f"Traduction échouée ({source_bcp47}→{target_bcp47}): {e}"
            ) from e
