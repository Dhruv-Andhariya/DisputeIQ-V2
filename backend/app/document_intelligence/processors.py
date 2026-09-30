import io
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.document_intelligence.schemas import OCRBlock, OCRPage


class DocumentProcessor(ABC):
    name = "DOCUMENT_PROCESSOR"
    version = "1.0"

    @abstractmethod
    def process(self, content: bytes, filename: str, mime_type: str) -> Tuple[str, List[OCRPage], Dict[str, Any]]:
        raise NotImplementedError


class TextDocumentProcessor(DocumentProcessor):
    name = "BUILTIN_TEXT"
    version = "1.0"

    def process(self, content: bytes, filename: str, mime_type: str):
        if mime_type == "application/json":
            text = json.dumps(json.loads(content.decode("utf-8")), indent=2)
        else:
            text = content.decode("utf-8")
        blocks = [OCRBlock(text=line, confidence=1.0, page=1) for line in text.splitlines() if line.strip()]
        return text, [OCRPage(page=1, blocks=blocks)], {"ocr_confidence": 1.0, "pages": 1}


class PDFTextProcessor(DocumentProcessor):
    name = "PYPDF_TEXT"

    def __init__(self):
        import pypdf
        self.version = getattr(pypdf, "__version__", "unknown")

    def process(self, content: bytes, filename: str, mime_type: str):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        pages = []
        text_parts = []
        for page_number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            text_parts.append(text)
            blocks = [OCRBlock(text=line, confidence=1.0, page=page_number) for line in text.splitlines() if line.strip()]
            pages.append(OCRPage(page=page_number, blocks=blocks))
        text = "\n".join(text_parts).strip()
        if not text:
            raise ValueError("PDF has no readable text layer; scanned PDF rendering is not available in this processor.")
        return text, pages, {"ocr_confidence": 1.0, "pages": len(pages), "text_layer": True}


class PaddleOCRProcessor(DocumentProcessor):
    name = "PADDLEOCR"

    def __init__(self):
        import paddleocr
        self._paddleocr = paddleocr
        self.version = getattr(paddleocr, "__version__", "unknown")

    def process(self, content: bytes, filename: str, mime_type: str):
        import os
        import tempfile

        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        from paddleocr import PaddleOCR

        suffix = Path(filename).suffix.lower() or ".img"
        descriptor, temp_path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(descriptor, "wb") as temp:
                temp.write(content)
            engine = PaddleOCR(
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False,
            )
            results = engine.predict(temp_path)
            pages = []
            all_text = []
            for page_number, result in enumerate(results, 1):
                data = result.json if hasattr(result, "json") else result
                if callable(data):
                    data = data()
                if isinstance(data, str):
                    data = json.loads(data)
                data = data.get("res", data) if isinstance(data, dict) else {}
                texts = data.get("rec_texts", [])
                scores = data.get("rec_scores", [])
                boxes = data.get("rec_boxes", data.get("dt_polys", []))
                blocks = []
                for index, text in enumerate(texts):
                    confidence = float(scores[index]) if index < len(scores) else 0.0
                    bbox = boxes[index] if index < len(boxes) else None
                    blocks.append(OCRBlock(text=str(text), confidence=max(0.0, min(1.0, confidence)), bbox=bbox, page=page_number))
                    all_text.append(str(text))
                pages.append(OCRPage(page=page_number, blocks=blocks))
        finally:
            os.unlink(temp_path)
        confidences = [block.confidence for page in pages for block in page.blocks]
        return "\n".join(all_text), pages, {"ocr_confidence": sum(confidences) / len(confidences) if confidences else 0.0, "pages": len(pages)}


def select_processor(content: bytes, filename: str, mime_type: str) -> DocumentProcessor:
    if mime_type == "application/pdf" or Path(filename).suffix.lower() == ".pdf":
        return PDFTextProcessor()
    if mime_type in {"application/json", "text/plain", "text/csv"}:
        return TextDocumentProcessor()
    if mime_type.startswith("image/"):
        return PaddleOCRProcessor()
    raise ValueError(f"Unsupported document type: {mime_type}")


def classify_document(declared_type: str, filename: str, raw_text: str) -> Tuple[str, float]:
    haystack = f"{filename} {raw_text}".lower()
    rules = [
        ("PAYMENT_RECEIPT", ("receipt", "payment successful", "payment receipt")),
        ("INVOICE", ("invoice", "tax invoice", "invoice number")),
        ("DELIVERY_PROOF", ("delivered", "proof of delivery", "tracking")),
        ("REFUND_RECORD", ("refund", "refunded", "refund id")),
        ("CANCELLATION_RECORD", ("cancelled", "cancellation")),
        ("CUSTOMER_COMMUNICATION", ("dear", "hello", "customer", "message")),
        ("TRANSACTION_RECORD", ("transaction id", "transaction status")),
        ("ORDER_RECORD", ("order id", "order number")),
    ]
    for document_type, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            return document_type, 0.94 if document_type == declared_type else 0.78
    return declared_type, 0.60


def _value(text: str, labels: List[str]) -> str | None:
    label_pattern = "|".join(r"\"?" + re.escape(label) + r"\"?" for label in sorted(labels, key=len, reverse=True))
    pattern = r"(?:" + label_pattern + r")\s*[:#-]?\s*\"?([^\"\n,;]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip().strip('"\'') if match else None


def _amount(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"\d[\d,]*(?:\.\d+)?", value)
    return float(match.group(0).replace(",", "")) if match else None


def _amount_for_labels(text: str, labels: List[str]) -> float | None:
    label_pattern = "|".join(r"\"?" + re.escape(label) + r"\"?" for label in sorted(labels, key=len, reverse=True))
    pattern = (
        r"(?:" + label_pattern + r")\s*[:#-]?\s*"
        r"(?:₹|INR\s*|Rs\.?\s*)?([0-9][0-9,]*(?:\.\d+)?)"
    )
    match = re.search(pattern, text, re.IGNORECASE)
    return _amount(match.group(1)) if match else None


def extract_structured(document_type: str, raw_text: str) -> Tuple[Dict[str, Any], str, Dict[str, float]]:
    from app.document_intelligence.schemas import (
        DeliveryProofExtraction, GenericExtraction, InvoiceExtraction,
        PaymentReceiptExtraction, RefundExtraction,
    )

    currency = "INR" if any(token in raw_text.lower() for token in ("inr", "rs.", "₹", "rupees")) else None
    if document_type == "INVOICE":
        model = InvoiceExtraction(
            invoice_number=_value(raw_text, ["invoice_number", "invoice", "invoice number", "invoice no"]),
            invoice_date=_value(raw_text, ["invoice_date", "invoice date", "date"]),
            customer_name=_value(raw_text, ["customer_name", "customer", "customer name"]),
            merchant_name=_value(raw_text, ["merchant_name", "merchant", "seller"]),
            order_id=_value(raw_text, ["order_id", "order id", "order"]),
            transaction_id=_value(raw_text, ["transaction_id", "transaction id", "transaction"]),
            subtotal=_amount_for_labels(raw_text, ["subtotal"]), tax=_amount_for_labels(raw_text, ["tax", "gst"]),
            total_amount=_amount_for_labels(raw_text, ["total_amount", "total", "total amount", "amount"]), currency=currency,
        )
        return model.model_dump(), "invoice.v1", {"field_extraction_confidence": 0.85}
    if document_type == "PAYMENT_RECEIPT":
        model = PaymentReceiptExtraction(
            transaction_id=_value(raw_text, ["transaction id", "transaction"]),
            payment_date=_value(raw_text, ["payment date", "date"]),
            payment_method=_value(raw_text, ["payment method", "method"]),
            amount=_amount_for_labels(raw_text, ["amount", "total"]), currency=currency,
            merchant=_value(raw_text, ["merchant", "seller"]), customer=_value(raw_text, ["customer"]),
            status=_value(raw_text, ["status"]),
        )
        return model.model_dump(), "payment_receipt.v1", {"field_extraction_confidence": 0.85}
    if document_type == "DELIVERY_PROOF":
        model = DeliveryProofExtraction(
            order_id=_value(raw_text, ["order id", "order"]), delivery_date=_value(raw_text, ["delivery date", "date"]),
            recipient_name=_value(raw_text, ["recipient", "signed by"]), delivery_address=_value(raw_text, ["address"]),
            delivery_status=_value(raw_text, ["delivery status", "status"]), tracking_id=_value(raw_text, ["tracking", "tracking id"]),
        )
        return model.model_dump(), "delivery_proof.v1", {"field_extraction_confidence": 0.82}
    if document_type == "REFUND_RECORD":
        model = RefundExtraction(
            refund_id=_value(raw_text, ["refund id", "refund"]), transaction_id=_value(raw_text, ["transaction id", "transaction"]),
            refund_date=_value(raw_text, ["refund date", "date"]), refund_amount=_amount_for_labels(raw_text, ["refund amount", "amount"]),
            currency=currency, refund_status=_value(raw_text, ["refund status", "status"]),
        )
        return model.model_dump(), "refund.v1", {"field_extraction_confidence": 0.82}
    model = GenericExtraction(fields={"raw_text": raw_text})
    return model.model_dump(), "generic.v1", {"field_extraction_confidence": 0.50}
