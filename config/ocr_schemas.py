"""OCR Schema configurations for different data extraction types."""

from typing import Dict, Any


class OCRSchemas:
    """Centralized OCR schema definitions for different extraction types."""

    # Alliance Ranking Schema
    ALLIANCE_RANKING = {
        "name": "alliance_ranking_extraction",
        "schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": ["string", "null"],
                    "description": "Title or heading of the ranking page"
                },
                "phase": {
                    "type": ["string", "null"],
                    "description": "KVK phase or event phase information"
                },
                "rankings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "placement": {
                                "type": ["integer", "null"],
                                "description": "Rank position"
                            },
                            "hash_number": {
                                "type": ["integer", "null"],
                                "description": "Kingdom or alliance identifier number"
                            },
                            "name": {
                                "type": ["string", "null"],
                                "description": "Alliance or kingdom name"
                            },
                            "points_contributed": {
                                "type": ["integer", "null"],
                                "description": "Total points or power contributed"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "extracted_text": {
                    "type": "string",
                    "description": "Full extracted text from the image"
                },
                "confidence_score": {
                    "type": "number",
                    "description": "Confidence score of extraction (0.0 to 1.0)"
                },
                "notes": {
                    "type": ["string", "null"],
                    "description": "Any additional notes or observations"
                }
            },
            "required": ["rankings", "confidence_score", "extracted_text"],
            "additionalProperties": False
        },
        "strict": False
    }

    # Kingdom Power Ranking Schema
    KINGDOM_POWER_RANKING = {
        "name": "kingdom_power_ranking_extraction",
        "schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": ["string", "null"],
                    "description": "Title of the ranking page"
                },
                "kingdom": {
                    "type": ["string", "null"],
                    "description": "Kingdom identifier or number"
                },
                "rankings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rank": {
                                "type": ["integer", "null"],
                                "description": "Rank position"
                            },
                            "governor": {
                                "type": ["string", "null"],
                                "description": "Governor/player name"
                            },
                            "power": {
                                "type": ["string", "null"],
                                "description": "Total power (may include letters like K, M, B)"
                            },
                            "alliance": {
                                "type": ["string", "null"],
                                "description": "Alliance tag or name"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "extracted_text": {
                    "type": "string",
                    "description": "Full extracted text from the image"
                },
                "confidence_score": {
                    "type": "number",
                    "description": "Confidence score of extraction (0.0 to 1.0)"
                },
                "notes": {
                    "type": ["string", "null"],
                    "description": "Additional notes"
                }
            },
            "required": ["rankings", "confidence_score", "extracted_text"],
            "additionalProperties": False
        },
        "strict": False
    }

    # KVK Points Schema
    KVK_POINTS = {
        "name": "kvk_points_extraction",
        "schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": ["string", "null"],
                    "description": "Title or event name"
                },
                "phase": {
                    "type": ["string", "null"],
                    "description": "KVK phase (preparation, conquest, etc.)"
                },
                "timestamp": {
                    "type": ["string", "null"],
                    "description": "Date or time information from the screenshot"
                },
                "player_points": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rank": {
                                "type": ["integer", "null"],
                                "description": "Rank position"
                            },
                            "player_name": {
                                "type": ["string", "null"],
                                "description": "Player/governor name"
                            },
                            "kills": {
                                "type": ["integer", "null"],
                                "description": "Number of kills"
                            },
                            "deaths": {
                                "type": ["integer", "null"],
                                "description": "Number of deaths"
                            },
                            "points": {
                                "type": ["integer", "null"],
                                "description": "Total KVK points"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "extracted_text": {
                    "type": "string",
                    "description": "Full extracted text"
                },
                "confidence_score": {
                    "type": "number",
                    "description": "Confidence score (0.0 to 1.0)"
                },
                "notes": {
                    "type": ["string", "null"],
                    "description": "Additional notes"
                }
            },
            "required": ["player_points", "confidence_score", "extracted_text"],
            "additionalProperties": False
        },
        "strict": False
    }

    # Alliance Members Schema
    ALLIANCE_MEMBERS = {
        "name": "alliance_members_extraction",
        "schema": {
            "type": "object",
            "properties": {
                "alliance_name": {
                    "type": ["string", "null"],
                    "description": "Name of the alliance"
                },
                "alliance_tag": {
                    "type": ["string", "null"],
                    "description": "Alliance tag/abbreviation"
                },
                "total_members": {
                    "type": ["integer", "null"],
                    "description": "Total number of members"
                },
                "total_power": {
                    "type": ["string", "null"],
                    "description": "Total alliance power"
                },
                "members": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": ["string", "null"],
                                "description": "Member name"
                            },
                            "power": {
                                "type": ["string", "null"],
                                "description": "Member power"
                            },
                            "rank": {
                                "type": ["string", "null"],
                                "description": "Alliance rank/role (R4, R5, etc.)"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "extracted_text": {
                    "type": "string",
                    "description": "Full extracted text"
                },
                "confidence_score": {
                    "type": "number",
                    "description": "Confidence score (0.0 to 1.0)"
                },
                "notes": {
                    "type": ["string", "null"],
                    "description": "Additional notes"
                }
            },
            "required": ["members", "confidence_score", "extracted_text"],
            "additionalProperties": False
        },
        "strict": False
    }

    @classmethod
    def get_schema(cls, ocr_type: str) -> Dict[str, Any]:
        """
        Get the OCR schema for a specific type.

        Args:
            ocr_type: Type of OCR extraction (alliance-ranking, kingdom-power-ranking, etc.)

        Returns:
            Schema dictionary for the specified type

        Raises:
            ValueError: If the ocr_type is not supported
        """
        schema_map = {
            "alliance-ranking": cls.ALLIANCE_RANKING,
            "kingdom-power-ranking": cls.KINGDOM_POWER_RANKING,
            "kvk-points": cls.KVK_POINTS,
            "alliance-members": cls.ALLIANCE_MEMBERS,
        }

        schema = schema_map.get(ocr_type)
        if not schema:
            raise ValueError(
                f"Unsupported OCR type: {ocr_type}. "
                f"Supported types: {', '.join(schema_map.keys())}"
            )

        return schema

    @classmethod
    def get_available_types(cls) -> list[str]:
        """Get list of all available OCR types."""
        return [
            "alliance-ranking",
            "kingdom-power-ranking",
            "kvk-points",
            "alliance-members",
        ]
