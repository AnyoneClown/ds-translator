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
    def translate_to_language(self, text: str, target_language: str) -> Optional[Dict[str, str]]:
        """Translate text to a specific language."""
        pass


class TranslationService(ITranslationService):
    """Service responsible for translation operations using Gemini API."""

    TRANSLATION_SCHEMA = {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "description": "The full name of the detected source language (e.g., 'Spanish'). If the text is already English, this should be 'English'.",
            },
            "text": {
                "type": "string",
                "description": "The English translation of the text. If the source is English, this is the original text.",
            },
        },
        "required": ["language", "text"],
    }

    TRANSLATE_TO_LANG_SCHEMA = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The translated text in the specified target language.",
            },
        },
        "required": ["text"],
    }

    def __init__(self, client: genai.Client):
        """Initialize translation service with Gemini client - Dependency Injection."""
        self._client = client

    def _clean_text(self, text: str) -> str:
        """Remove emojis and special characters from text."""
        return re.sub(r"[^\w\s.,!?-]", "", text)

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
"""

        try:
            response = self._client.models.generate_content(
                model="gemma-3-12b-it",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=self.TRANSLATION_SCHEMA,
                    temperature=0,
                ),
            )
            return json.loads(response.text)

        except Exception as e:
            print(f"Translation to English failed: {e}")
            return None

    def translate_to_language(self, text: str, target_language: str) -> Optional[Dict[str, str]]:
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
"""

        try:
            response = self._client.models.generate_content(
                model="gemma-3-12b-it",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=self.TRANSLATE_TO_LANG_SCHEMA,
                    temperature=0,
                ),
            )
            return json.loads(response.text)

        except Exception as e:
            print(f"Translation to {target_language} failed: {e}")
            return None
