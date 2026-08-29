"""
app/services/ocr/router.py
Smart routing — feature flagged, safe defaults.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from .schemas import OCRLanguage, OCRProvider, OCRResult

if TYPE_CHECKING:
    from .base import BaseOCREngine

logger = logging.getLogger(__name__)


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


USE_OCR_ROUTER         = _flag("USE_OCR_ROUTER",         False)
ENABLE_AWS_TEXTRACT    = _flag("ENABLE_AWS_TEXTRACT",     False)
MIN_CONFIDENCE         = float(os.getenv("OCR_MIN_CONFIDENCE", "0.50"))


class OCRRouter:

    def __init__(self, engines: List["BaseOCREngine"]) -> None:
        self._engines          = engines
        self._forced_provider: Optional[OCRProvider] = None

    @classmethod
    def build(cls, *, extra_engines=None) -> "OCRRouter":
        from .google_vision import GoogleVisionOCR
        from .aws_textract  import AWSTextractOCR

        available: List["BaseOCREngine"] = []
        if GoogleVisionOCR.is_available():
            available.append(GoogleVisionOCR())
        if AWSTextractOCR.is_available():
            available.append(AWSTextractOCR())
        if extra_engines:
            available.extend(extra_engines)
        return cls(available)

    def route(
        self,
        image_source: Union[bytes, Path, str],
        language: OCRLanguage = OCRLanguage.AUTO,
    ) -> Optional[OCRResult]:
        """
        Returns OCRResult on success, None to signal Tesseract fallback.
        """
        if not USE_OCR_ROUTER:
            return self._run_first(image_source, language)

        for engine in self._ordered_engines(language):
            result = engine.extract(image_source, language)
            if result.success and result.is_usable(MIN_CONFIDENCE):
                logger.info("Router selected %s (confidence=%.2f)", engine.provider.value, result.overall_confidence)
                return result
            logger.warning("Router skipping %s (success=%s confidence=%.2f)", engine.provider.value, result.success, result.overall_confidence)

        logger.warning("All engines failed/low-confidence → Tesseract fallback")
        return None

    def _ordered_engines(self, language: OCRLanguage) -> List["BaseOCREngine"]:
        if self._forced_provider:
            return [e for e in self._engines if e.provider == self._forced_provider]
        if language in (OCRLanguage.HINDI, OCRLanguage.MARATHI):
            # Indic → Vision first
            pref = [OCRProvider.GOOGLE_VISION, OCRProvider.AWS_TEXTRACT]
        elif language == OCRLanguage.ENGLISH and ENABLE_AWS_TEXTRACT:
            # English structured → Textract first
            pref = [OCRProvider.AWS_TEXTRACT, OCRProvider.GOOGLE_VISION]
        else:
            pref = [OCRProvider.GOOGLE_VISION, OCRProvider.AWS_TEXTRACT]
        idx = {p: i for i, p in enumerate(pref)}
        return sorted(self._engines, key=lambda e: idx.get(e.provider, len(pref)))

    def _run_first(self, image_source, language) -> Optional[OCRResult]:
        if not self._engines:
            return None
        return self._engines[0].extract(image_source, language)

    @property
    def available_providers(self) -> List[OCRProvider]:
        return [e.provider for e in self._engines]