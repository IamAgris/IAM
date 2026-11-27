"""OCR and media transcription for the Web Intelligence Engine.

OCR runs Tesseract in an isolated container so no host system packages are
required. Media transcription delegates to IAM's existing voice service and
returns its explicit limitation when no STT provider is configured. Extracted
text is untrusted reference data, never instructions.
"""

from __future__ import annotations

import asyncio
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

TESSERACT_IMAGE = "minidocks/tesseract:latest"
_LANGUAGE = re.compile(r"^[a-z_]{3,10}$")


class LiveMediaService:
    async def ocr(self, image_bytes: bytes, language: str = "eng") -> Dict[str, Any]:
        if not _LANGUAGE.fullmatch(language):
            return {"text": "", "error": "invalid OCR language", "untrusted": True}
        if not image_bytes:
            return {"text": "", "error": "empty image", "untrusted": True}

        directory = Path(tempfile.mkdtemp(prefix="iam-live-ocr-"))
        image_path = directory / "input.png"
        image_path.write_bytes(image_bytes)
        mount = str(directory).replace("\\", "/")
        command = [
            "docker", "run", "--rm", "--entrypoint", "sh",
            "-v", f"{mount}:/data", TESSERACT_IMAGE,
            "-c",
            f"apk add --no-cache tesseract-ocr-data-{language} >/dev/null "
            f"&& tesseract /data/input.png stdout -l {language}",
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180.0)
        except asyncio.TimeoutError:
            return {"text": "", "error": "OCR timed out", "untrusted": True}
        except Exception as exc:  # pragma: no cover - docker may be unavailable
            return {
                "text": "",
                "error": f"OCR unavailable: {type(exc).__name__}",
                "untrusted": True,
            }
        finally:
            try:
                image_path.unlink(missing_ok=True)
                directory.rmdir()
            except OSError:
                pass

        text = stdout.decode("utf-8", errors="replace").strip()
        if process.returncode != 0 or not text:
            detail = stderr.decode("utf-8", errors="replace").strip()[:200]
            return {
                "text": "",
                "error": f"OCR failed: {detail or 'no text extracted'}",
                "untrusted": True,
            }
        return {
            "text": text[:4000],
            "provider": "tesseract-docker",
            "language": language,
            "untrusted": True,
        }

    async def transcribe(
        self, audio_bytes: bytes, content_type: str = "audio/wav", language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Use the configured IAM STT provider; never fabricate a transcript."""
        from app.services.voice_service import voice_service

        result: Dict[str, Any] = await voice_service.speech_to_text(
            audio_bytes, content_type, language
        )
        result["untrusted"] = True
        return result


live_media_service = LiveMediaService()
