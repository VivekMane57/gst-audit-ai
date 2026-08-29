"""
app/services/ocr/base.py
Abstract OCR engine base class.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from .schemas import OCRLanguage, OCRProvider, OCRResult

logger = logging.getLogger(__name__)


class BaseOCREngine(ABC):

    @property
    @abstractmethod
    def provider(self) -> OCRProvider: ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool: ...

    @abstractmethod
    def _run_ocr(
        self,
        image_source: Union[bytes, Path, str],
        language: OCRLanguage,
    ) -> OCRResult: ...

    def extract(
        self,
        image_source: Union[bytes, Path, str],
        language: OCRLanguage = OCRLanguage.AUTO,
    ) -> OCRResult:
        logger.info("OCR | provider=%s language=%s", self.provider.value, language.value)
        try:
            result = self._run_ocr(image_source, language)
        except Exception as exc:
            logger.exception("Unhandled error in %s", self.provider.value)
            return OCRResult.failure(self.provider, f"Engine error: {exc}")

        logger.info(
            "OCR done | provider=%s success=%s confidence=%.2f",
            self.provider.value, result.success, result.overall_confidence,
        )
        return result

    @staticmethod
    def _to_bytes(image_source: Union[bytes, Path, str]):
        if isinstance(image_source, (bytes, bytearray)):
            return bytes(image_source)
        path = Path(image_source)
        if path.exists():
            return path.read_bytes()
        return None

    @staticmethod
    def _language_hints(language: OCRLanguage) -> list:
        return {
            OCRLanguage.ENGLISH: ["en"],
            OCRLanguage.HINDI:   ["hi"],
            OCRLanguage.MARATHI: ["mr"],
            OCRLanguage.AUTO:    ["en", "hi", "mr"],
        }.get(language, ["en"])