"""Document 26 (OD-45): model-based translation and multilingual semantics.

Local-first by default: the local IAM model is preferred; a hosted provider is
optional and never primary. Translation is a derivative artefact — the original
source remains authoritative and is always preserved.
"""

from typing import Any, Callable, Dict, Optional

from app.services.hbi.ingestion import (
    cultural_tags,
    detect_language_detail,
    extract_claims,
)

TRANSLATION_PROMPT = (
    "Translate the following text into {target}. Preserve meaning and uncertainty. "
    "Return only the translation.\n\n{text}"
)


class TranslationService:
    def __init__(self, inference: Any = None, translator: Optional[Callable[[str, str, str], str]] = None):
        self.inference = inference
        self.translator = translator

    async def translate(self, text: str, target_language: str = "en",
                        source_language: Optional[str] = None,
                        model: Optional[str] = None) -> Dict[str, Any]:
        detection = detect_language_detail(text, source_language)
        if self.translator is not None:
            translated = self.translator(text, detection["language"], target_language)
            engine = "injected_translator"
        elif self.inference is not None:
            messages = [{
                "role": "user",
                "content": TRANSLATION_PROMPT.format(target=target_language, text=text),
            }]
            try:
                result = await self.inference.chat(messages, model=model, temperature=0.0)
            except Exception as error:  # fail closed, never invent a translation
                return {
                    "status": "not_performed", "reason": str(error)[:300],
                    "language_detail": detection, "original_preserved": text,
                }
            translated = result.get("translated") or _text_from_chat(result)
            engine = "local_model" if result.get("iam_inference", {}).get("mode") != "hosted" else "hosted_model"
        else:
            return {
                "status": "not_performed",
                "reason": "no_translation_engine_configured",
                "language_detail": detection,
                "original_preserved": text,
            }
        if not translated or not str(translated).strip():
            return {
                "status": "not_performed", "reason": "empty_translation",
                "language_detail": detection, "original_preserved": text,
            }
        return {
            "status": "translated",
            "engine": engine,
            "source_language": detection["language"],
            "target_language": target_language,
            "language_detail": detection,
            "translated_text": str(translated),
            "original_preserved": text,
            "note": "Translation is a derivative; original source remains authoritative.",
        }

    async def multilingual_semantics(self, text: str, language: Optional[str] = None,
                                      region: Optional[str] = None) -> Dict[str, Any]:
        detection = detect_language_detail(text, language)
        translation = await self.translate(text, "en", detection["language"])
        original_claims = extract_claims(text)
        translated_claims = []
        if translation["status"] == "translated":
            translated_claims = extract_claims(translation["translated_text"])
        overlap = 0.0
        if original_claims and translated_claims:
            overlap = round(
                len(set(original_claims) & set(translated_claims)) /
                len(set(original_claims) | set(translated_claims)), 3
            )
        return {
            "language_detail": detection,
            "cultural_tags": cultural_tags(region),
            "original_claims": original_claims,
            "translated_claims": translated_claims,
            "claim_overlap": overlap,
            "translation": translation,
            "caveat": "Cross-lingual semantic equivalence is not guaranteed by wording overlap.",
        }


def _text_from_chat(result: Dict[str, Any]) -> str:
    choices = result.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or "")
