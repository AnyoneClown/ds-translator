import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Optional

from google import genai

logger = logging.getLogger(__name__)


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

    def __init__(self, client: genai.Client):
        """Initialize translation service with Gemini client - Dependency Injection."""
        self._client = client
        logger.info("TranslationService initialized with Gemini client")
        logger.debug(f"Available models: {client.models.list()}")

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
            You are a deterministic language detection and translation engine used in a backend service.

            Your responsibilities:
            1. Analyze the provided input text.
            2. Detect the original language of the text.
            3. Translate the text into English.

            Detection rules:
            - Detect the actual source language, not the script.
            - If the text is already English, detect the language as "English".
            - If the text contains multiple languages, detect the dominant one.
            - If the text is meaningless, random characters, or empty after trimming, return null.

            Translation rules:
            - Translate accurately without adding, removing, or rephrasing content.
            - Preserve original meaning, intent, tone, and level of formality.
            - Do NOT summarize or explain.
            - Do NOT normalize slang beyond accurate translation.
            - If the source language is English, return the original text unchanged.

            Output rules (MANDATORY):
            - Output MUST be valid JSON.
            - Output MUST contain ONLY the JSON object.
            - Do NOT include markdown, comments, explanations, or extra text.
            - Property names MUST match exactly.

            Required output format:
            {{
            "language": "<detected language name in English>",
            "text": "<English translation or original English text>"
            }}

            Failure handling:
            - If the task cannot be completed reliably, return null.
            - Never guess the language or translation.

            Input text:
            "{text_cleaned}"
        """

        try:
            response = self._client.models.generate_content(
                model="gemma-3-27b-it",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0,
                ),
            )
            return self._parse_response(response.text)

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

Respond ONLY with a JSON object in this exact format:
{{"text": "translated text"}}
"""

        try:
            response = self._client.models.generate_content(
                model="gemma-3-27b-it",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0,
                ),
            )
            return self._parse_response(response.text)

        except Exception as e:
            print(f"Translation to {target_language} failed: {e}")
            return None
