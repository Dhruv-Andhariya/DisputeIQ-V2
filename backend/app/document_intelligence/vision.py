from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class VisionProcessor(ABC):
    name = "VISION_PROCESSOR"
    version = "1.0"

    @abstractmethod
    def extract(self, content: bytes, mime_type: str, document_type: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class GeminiVisionProcessor(VisionProcessor):
    """Opt-in VLM adapter. Phase 4 stores its output as extraction, never truth."""
    name = "GEMINI_VISION"

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        self.version = model

    def extract(self, content: bytes, mime_type: str, document_type: str):
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=[types.Part.from_bytes(data=content, mime_type=mime_type),
                      f"Extract fields from this {document_type} document. Return JSON only. Do not verify authenticity."],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
        )
        return {"raw_response": response.text if response else "", "provider": self.name, "model": self.model}
