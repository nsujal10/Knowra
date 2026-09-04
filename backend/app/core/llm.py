from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Type
import os
import httpx
import json
import structlog

logger = structlog.get_logger(__name__)

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, response_schema: Type[BaseModel], **kwargs) -> BaseModel:
        pass

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate(self, prompt: str, **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs
        }
        try:
            response = httpx.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("LLM text generation failed", error=str(e))
            raise

    def generate_structured(self, prompt: str, response_schema: Type[BaseModel], **kwargs) -> BaseModel:
        schema_json = response_schema.model_json_schema()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"Output JSON conforming exactly to this schema: {json.dumps(schema_json)}"},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            **kwargs
        }
        try:
            response = httpx.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return response_schema.model_validate_json(content)
        except Exception as e:
            logger.error("LLM structured generation failed", error=str(e))
            raise
