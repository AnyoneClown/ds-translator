"""Translation service - Single Responsibility Principle."""

import json
import re
from typing import Dict, Optional
from google import genai
from abc import ABC, abstractmethod


class ITranslationService(ABC):
    """Interface for translation service - Interface Segregation Principle."""

    @abstractmethod
    def translate_to_english(self, text: str) -> Optional[Dict[str, str]]:
        """Translate text to English."""
        pass

    @abstractmethod
    def translate_to_language(
        self, text: str, target_language: str
    ) -> Optional[Dict[str, str]]:
        """Translate text to a specific language."""
        pass


class TranslationService(ITranslationService):
    """Service responsible for translation operations using Gemini API."""

    def __init__(self, client: genai.Client):
        """Initialize translation service with Gemini client - Dependency Injection."""
        self._client = client
        print(client.models.list())

    def _clean_text(self, text: str) -> str:
        """Remove emojis and special characters from text."""
        return re.sub(r"[^\w\s.,!?-]", "", text)

    def _parse_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """Parse JSON from model response."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
        except json.JSONDecodeError:
            return None

    def translate_to_english(self, text: str) -> Optional[Dict[str, str]]:
        """
        Translate text to English and detect source language.

        Args:
            text: Text to translate

        Returns:
            Dictionary with 'language' and 'text' keys, or None on failure
        """
        text_cleaned = self._clean_text(text)
        if not text_cleaned.strip():
            return None

        prompt = f"""
Analyze the following text. Identify its source language and translate it into English.
If the original text is already in English, identify the language as "English".

Input: "{text_cleaned}"

Respond ONLY with a JSON object in this exact format:
{{"language": "detected language name", "text": "English translation"}}
"""

        try:
            response = self._client.models.generate_content(
                model="gemma-3-12b-it",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0,
                ),
            )
            return self._parse_response(response.text)

        except Exception as e:
            print(f"Translation to English failed: {e}")
            return None

    def translate_to_language(
        self, text: str, target_language: str
    ) -> Optional[Dict[str, str]]:
        """
        Translate text to a specified language.

        Args:
            text: Text to translate
            target_language: Target language name

        Returns:
            Dictionary with 'text' key, or None on failure
        """
        text_cleaned = self._clean_text(text)
        if not text_cleaned.strip():
            return None

        prompt = f"""
Translate the following text into {target_language}.

Input: "{text_cleaned}"

Respond ONLY with a JSON object in this exact format:
{{"text": "translated text"}}
"""

        try:
            response = self._client.models.generate_content(
                model="gemma-3-12b-it",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0,
                ),
            )
            return self._parse_response(response.text)

        except Exception as e:
            print(f"Translation to {target_language} failed: {e}")
            return None
