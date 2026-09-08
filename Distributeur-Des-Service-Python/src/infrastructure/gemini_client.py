import requests
import time

from src.config.config import settings


class GeminiClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def configured(self) -> bool:
        return bool(self.api_key)

    def _generate_content_text(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY non configurée dans le .env.")

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        last_error = None
        data = None
        for attempt in range(1, settings.GEMINI_MAX_RETRIES + 1):
            try:
                response = requests.post(url, json=payload, timeout=settings.GEMINI_TIMEOUT_SECONDS)
                response.raise_for_status()
                data = response.json()
                break
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < settings.GEMINI_MAX_RETRIES:
                    time.sleep(attempt * 1.5)
                    continue
                raise RuntimeError(
                    "Timeout Gemini. Vérifie la connexion internet / firewall / proxy et réessaie."
                ) from e
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < settings.GEMINI_MAX_RETRIES:
                    time.sleep(attempt * 1.5)
                    continue
                raise RuntimeError(f"Erreur HTTP Gemini: {str(e)}") from e
        else:
            raise RuntimeError(f"Erreur Gemini: {str(last_error)}")

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini n'a retourné aucun résultat.")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts or "text" not in parts[0]:
            raise RuntimeError("Réponse Gemini invalide.")

        return parts[0]["text"].strip()

    def generate_keywords_from_name(self, robot_name: str):
        prompt = (
            "Role: You are an expert in Arabic linguistics and Speech-to-Text (STT) systems.\n\n"
            "Objective: From a proper name (robot name), generate an exhaustive list of keyword variants. "
            "The list must include correct spellings, phonetic variants, and frequent STT transcription errors.\n\n"
            "Generation constraints:\n"
            "- Arabic variants: include permutations of phonetically similar letters (e.g. ح/ه/خ, س/ص/ش, ن/م).\n"
            "- Latin variants: transliterate the name with different French/English spellings.\n"
            "- Typical STT errors: simulate segmentation mistakes (spaces, hyphens) and end-of-word confusions.\n"
            "- Output format: return ONLY a JSON array of strings.\n\n"
            f"Input name: {robot_name}\n"
            "Output: JSON array."
        )
        return self._generate_content_text(prompt)
