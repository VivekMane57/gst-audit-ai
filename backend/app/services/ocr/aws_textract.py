"""
app/services/ocr/aws_textract.py
AWS Textract — activated only when ENABLE_AWS_TEXTRACT=true + credentials set.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import BaseOCREngine
from .schemas import (
    ExtractedInvoiceFields,
    OCRKeyValue,
    OCRLanguage,
    OCRProvider,
    OCRResult,
    OCRTable,
    OCRTableCell,
)

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False
    BotoCoreError = Exception   # type: ignore
    ClientError   = Exception   # type: ignore


class AWSTextractOCR(BaseOCREngine):

    def __init__(
        self,
        region:     Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ) -> None:
        self._region     = region     or os.getenv("AWS_REGION", "ap-south-1")
        self._access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID", "")
        self._secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY", "")

    @property
    def provider(self) -> OCRProvider:
        return OCRProvider.AWS_TEXTRACT

    @classmethod
    def is_available(cls) -> bool:
        if not _BOTO3_AVAILABLE:
            return False
        if os.getenv("ENABLE_AWS_TEXTRACT", "").lower() not in ("1", "true", "yes"):
            return False
        return bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))

    def _run_ocr(
        self,
        image_source: Union[bytes, Path, str],
        language: OCRLanguage,
    ) -> OCRResult:
        if not _BOTO3_AVAILABLE:
            return OCRResult.failure(self.provider, "boto3 not installed. Run: pip install boto3>=1.34.0")
        image_bytes = self._to_bytes(image_source)
        if image_bytes is None:
            return OCRResult.failure(self.provider, f"Cannot read image: {image_source}")
        raw = self._call_textract(image_bytes)
        if raw is None:
            return OCRResult.failure(self.provider, "AWS Textract call failed.")
        return self._parse_response(raw)

    def _call_textract(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        try:
            client = boto3.client(
                "textract",
                region_name          = self._region,
                aws_access_key_id    = self._access_key or None,
                aws_secret_access_key= self._secret_key or None,
            )
            return client.analyze_document(
                Document     = {"Bytes": image_bytes},
                FeatureTypes = ["FORMS", "TABLES"],
            )
        except (BotoCoreError, ClientError) as exc:
            logger.warning("Textract error: %s", exc)
            return None

    def _parse_response(self, raw: Dict[str, Any]) -> OCRResult:
        blocks: List[Dict] = raw.get("Blocks", [])
        if not blocks:
            return OCRResult.failure(self.provider, "No blocks returned by Textract.")

        block_map  = {b["Id"]: b for b in blocks}
        raw_text   = "\n".join(b["Text"] for b in blocks if b.get("BlockType") == "LINE" and "Text" in b)
        tables     = self._extract_tables(blocks, block_map)
        key_values = self._extract_key_values(blocks, block_map)
        confidence = self._overall_confidence(blocks)
        extracted  = self._map_fields(key_values, tables)

        return OCRResult(
            provider           = self.provider,
            raw_text           = raw_text,
            tables             = tables,
            key_values         = key_values,
            extracted          = extracted,
            overall_confidence = confidence,
            language_detected  = "en",
            success            = True,
            provider_metadata  = {"block_count": len(blocks)},
        )

    @staticmethod
    def _overall_confidence(blocks: List[Dict]) -> float:
        scores = [
            b["Confidence"] / 100.0
            for b in blocks
            if "Confidence" in b and b.get("BlockType") in ("WORD", "LINE")
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def _get_children_text(self, block: Dict, block_map: Dict) -> str:
        texts = []
        for rel in block.get("Relationships", []):
            if rel["Type"] == "CHILD":
                for cid in rel["Ids"]:
                    child = block_map.get(cid, {})
                    if child.get("BlockType") == "WORD":
                        texts.append(child.get("Text", ""))
        return " ".join(texts).strip()

    def _extract_tables(self, blocks: List[Dict], block_map: Dict) -> List[OCRTable]:
        tables = []
        for tb in [b for b in blocks if b.get("BlockType") == "TABLE"]:
            cells = []
            max_r = max_c = 0
            for rel in tb.get("Relationships", []):
                if rel["Type"] != "CHILD":
                    continue
                for cid in rel["Ids"]:
                    cb = block_map.get(cid, {})
                    if cb.get("BlockType") != "CELL":
                        continue
                    ri   = cb.get("RowIndex", 1) - 1
                    ci   = cb.get("ColumnIndex", 1) - 1
                    rs   = cb.get("RowSpan", 1)
                    cs   = cb.get("ColumnSpan", 1)
                    text = self._get_children_text(cb, block_map)
                    conf = cb.get("Confidence", 0.0) / 100.0
                    is_h = cb.get("EntityTypes", []) == ["COLUMN_HEADER"]
                    max_r = max(max_r, ri + rs)
                    max_c = max(max_c, ci + cs)
                    cells.append(OCRTableCell(
                        text=text, row_index=ri, col_index=ci,
                        row_span=rs, col_span=cs, confidence=conf, is_header=is_h,
                    ))
            if cells:
                tables.append(OCRTable(rows=max_r, cols=max_c, cells=cells))
        return tables

    def _extract_key_values(self, blocks: List[Dict], block_map: Dict) -> List[OCRKeyValue]:
        kvs      = []
        kv_set   = [b for b in blocks if b.get("BlockType") == "KEY_VALUE_SET"]
        key_bl   = {b["Id"]: b for b in kv_set if "KEY"   in b.get("EntityTypes", [])}
        val_bl   = {b["Id"]: b for b in kv_set if "VALUE" in b.get("EntityTypes", [])}

        for kid, kb in key_bl.items():
            key_text = self._get_children_text(kb, block_map)
            if not key_text:
                continue
            val_text = ""
            for rel in kb.get("Relationships", []):
                if rel["Type"] == "VALUE":
                    for vid in rel["Ids"]:
                        vb = val_bl.get(vid)
                        if vb:
                            val_text = self._get_children_text(vb, block_map)
            kvs.append(OCRKeyValue(
                key        = key_text,
                value      = val_text,
                confidence = kb.get("Confidence", 0.0) / 100.0,
            ))
        return kvs

    # Map Textract KVs → ExtractedInvoiceFields (Invoice model field names)
    _KV_MAP: Dict[str, str] = {
        "invoice no":     "invoice_number",
        "invoice number": "invoice_number",
        "invoice #":      "invoice_number",
        "invoice date":   "invoice_date",
        "date":           "invoice_date",
        "party name":     "party_name",
        "customer name":  "party_name",
        "supplier name":  "party_name",
        "gstin":          "party_gstin",
        "party gstin":    "party_gstin",
        "taxable value":  "taxable_value",
        "taxable amount": "taxable_value",
        "cgst":           "cgst",
        "sgst":           "sgst",
        "igst":           "igst",
        "hsn code":       "hsn_code",
        "hsn":            "hsn_code",
        "irn":            "irn",
        "grand total":    "total_amount",
        "total amount":   "total_amount",
    }

    def _map_fields(self, key_values: List[OCRKeyValue], tables: List[OCRTable]) -> ExtractedInvoiceFields:
        f = ExtractedInvoiceFields()
        for kv in key_values:
            fname = self._KV_MAP.get(kv.key.lower().strip())
            if not fname or not kv.value:
                continue
            try:
                if fname in ("taxable_value", "cgst", "sgst", "igst", "total_amount"):
                    setattr(f, fname, float(kv.value.replace(",", "").replace("₹", "").strip()))
                else:
                    setattr(f, fname, kv.value.strip())
            except (ValueError, TypeError):
                pass
        return f