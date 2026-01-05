"""OCR Service for extracting structured data from images using Kolosal AI."""

import base64
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import aiohttp

from config.ocr_schemas import OCRSchemas

logger = logging.getLogger(__name__)


class IOCRService(ABC):
    """Interface for OCR service - Interface Segregation Principle."""

    @abstractmethod
    async def process_images(
        self,
        image_data_list: List[bytes],
        ocr_type: str
    ) -> List[Dict[str, Any]]:
        """Process multiple images with OCR."""
        pass


class OCRService(IOCRService):
    """Service for OCR extraction using Kolosal AI API."""

    def __init__(self, api_key: str, api_url: str = "https://api.kolosal.ai/ocr"):
        """
        Initialize OCR service.

        Args:
            api_key: Kolosal AI API key
            api_url: Base URL for the OCR API
        """
        self._api_key = api_key
        self._api_url = api_url
        logger.info(f"OCRService initialized with API URL: {api_url}")

    async def process_images(
        self,
        image_data_list: List[bytes],
        ocr_type: str
    ) -> List[Dict[str, Any]]:
        """
        Process multiple images with OCR extraction.

        Args:
            image_data_list: List of image data in bytes
            ocr_type: Type of OCR extraction (alliance-ranking, kingdom-power-ranking, etc.)

        Returns:
            List of dictionaries containing OCR results for each image

        Raises:
            ValueError: If ocr_type is not supported
        """
        logger.info(f"Processing {len(image_data_list)} image(s) with OCR type: {ocr_type}")

        # Get the schema for this OCR type
        try:
            schema = OCRSchemas.get_schema(ocr_type)
        except ValueError as e:
            logger.error(f"Invalid OCR type: {str(e)}")
            raise

        results = []
        for index, image_data in enumerate(image_data_list):
            logger.info(f"Processing image {index + 1}/{len(image_data_list)}")
            try:
                result = await self._process_single_image(image_data, schema, index)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing image {index + 1}: {str(e)}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "image_index": index
                })

        logger.info(f"Completed OCR processing for {len(results)} images")
        return results

    async def _process_single_image(
        self,
        image_data: bytes,
        schema: Dict[str, Any],
        image_index: int
    ) -> Dict[str, Any]:
        """
        Process a single image with OCR.

        Args:
            image_data: Image data in bytes
            schema: OCR schema to use for extraction
            image_index: Index of the image in the batch

        Returns:
            Dictionary containing OCR result
        """
        # Encode image to base64
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        
        # Add data URI prefix for proper image format recognition
        image_data_uri = f"data:image/png;base64,{encoded_image}"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._api_key}'
        }
        
        payload = {
            'image_data': image_data_uri,
            'language': 'en',
            'auto_fix': True,
            'custom_schema': schema
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Image {image_index} processed successfully")
                        logger.debug(f"Full API response: {result}")
                        
                        # Extract the structured data from the response
                        # The API may return data directly in 'content' or at root level
                        extracted_data = result.get('content', result)
                        
                        logger.debug(f"Extracted data structure: {extracted_data}")
                        
                        raw_text = extracted_data.get('extracted_text', '') if isinstance(extracted_data, dict) else ''
                        confidence = extracted_data.get('confidence_score', 0.0) if isinstance(extracted_data, dict) else 0.0
                        
                        logger.debug(f"Raw text: {raw_text[:100] if raw_text else 'None'}")
                        logger.debug(f"Confidence: {confidence}")
                        
                        return {
                            "success": True,
                            "image_index": image_index,
                            "extracted_data": extracted_data,
                            "raw_text": raw_text,
                            "confidence_score": confidence,
                            "error": None
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"OCR API error for image {image_index}: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "image_index": image_index,
                            "extracted_data": None,
                            "raw_text": None,
                            "confidence_score": None,
                            "error": f"API error: {response.status} - {error_text}"
                        }

        except aiohttp.ClientError as e:
            logger.error(f"Network error processing image {image_index}: {str(e)}")
            return {
                "success": False,
                "image_index": image_index,
                "extracted_data": None,
                "raw_text": None,
                "confidence_score": None,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error processing image {image_index}: {str(e)}")
            return {
                "success": False,
                "image_index": image_index,
                "extracted_data": None,
                "raw_text": None,
                "confidence_score": None,
                "error": f"Unexpected error: {str(e)}"
            }

    def get_available_types(self) -> List[str]:
        """Get list of all available OCR types."""
        return OCRSchemas.get_available_types()
