import json
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

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


def translate_to_english(text_to_translate: str) -> dict | None:
    text_no_emojis = re.sub(r"[^\w\s.,!?-]", "", text_to_translate)
    if not text_no_emojis.strip():
        return None

    prompt = f"""
Analyze the following text. Identify its source language and translate it into English.
If the original text is already in English, identify the language as "English".

Input: "{text_no_emojis}"
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TRANSLATION_SCHEMA,
                temperature=0,
            ),
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"An error occurred with Gemini API: {e}")
        print(
            f"Raw model response: {response.text if 'response' in locals() else 'No response'}"
        )
        return None


def translate_to_language(text_to_translate: str, target_language: str) -> str | None:
    """
    Translates text to a specified language using Gemini's JSON mode.
    Returns the translated text string, or None on failure.
    """
    text_no_emojis = re.sub(r"[^\w\s.,!?-]", "", text_to_translate)

    if not text_no_emojis.strip():
        return None

    prompt = f"""
Translate the following text into {target_language}.

Input: "{text_no_emojis}"
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TRANSLATE_TO_LANG_SCHEMA,
                temperature=0,
            ),
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"An error occurred with Gemini API during specific translation: {e}")
        if "response" in locals() and hasattr(response, "parts"):
            print(f"Raw model response parts: {response.parts}")
        return None
