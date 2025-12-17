"""Database service for managing users and statistics."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PlayerLookupLog, TranslationLog, User

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations related to users and stats."""

    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        user_id: int,
        username: str,
        discriminator: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> User:
        """
        Get an existing user or create a new one.

        Args:
            session: Database session
            user_id: Discord user ID
            username: Username
            discriminator: User discriminator (for legacy Discord usernames)
            display_name: Display name/nickname

        Returns:
            User object
        """
        # Try to get existing user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            # Update last seen and other info if changed
            user.last_seen = datetime.utcnow()
            user.username = username
            user.discriminator = discriminator
            if display_name:
                user.display_name = display_name
            logger.debug(f"Updated existing user: {user_id}")
        else:
            # Create new user
            user = User(
                id=user_id,
                username=username,
                discriminator=discriminator,
                display_name=display_name,
            )
            session.add(user)
            logger.info(f"Created new user: {user_id} ({username})")

        await session.flush()
        return user

    @staticmethod
    async def log_translation(
        session: AsyncSession,
        user_id: int,
        original_text: str,
        translated_text: str,
        target_language: str,
        source_language: Optional[str] = None,
        translation_type: str = "manual",
        guild_id: Optional[int] = None,
        channel_id: Optional[int] = None,
    ) -> TranslationLog:
        """
        Log a translation to the database.

        Args:
            session: Database session
            user_id: Discord user ID
            original_text: Original text
            translated_text: Translated text
            target_language: Target language code
            source_language: Source language code (optional)
            translation_type: Type of translation (manual, reaction, command, etc.)
            guild_id: Discord guild ID (optional)
            channel_id: Discord channel ID (optional)

        Returns:
            TranslationLog object
        """
        log = TranslationLog(
            user_id=user_id,
            original_text=original_text,
            translated_text=translated_text,
            target_language=target_language,
            source_language=source_language,
            translation_type=translation_type,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        session.add(log)
        await session.flush()
        logger.info(f"Logged translation for user {user_id}: {target_language} ({translation_type})")
        return log

    @staticmethod
    async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
        """
        Get user information.

        Args:
            session: Database session
            user_id: Discord user ID

        Returns:
            User object or None if not found
        """
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def log_player_lookup(
        session: AsyncSession,
        user_id: int,
        player_id: str,
        player_name: Optional[str] = None,
        kingdom: Optional[str] = None,
        castle_level: Optional[int] = None,
        success: bool = True,
        guild_id: Optional[int] = None,
        channel_id: Optional[int] = None,
    ) -> PlayerLookupLog:
        """
        Log a player stats lookup to the database.

        Args:
            session: Database session
            user_id: Discord user ID who requested the lookup
            player_id: The player ID that was looked up
            player_name: Player name (if found)
            kingdom: Player's kingdom (if found)
            castle_level: Player's castle level (if found)
            success: Whether the lookup was successful
            guild_id: Discord guild ID (optional)
            channel_id: Discord channel ID (optional)

        Returns:
            PlayerLookupLog object
        """
        log = PlayerLookupLog(
            user_id=user_id,
            kingshot_id=player_id,
            kingshot_name=player_name,
            kingdom=kingdom,
            castle_level=castle_level,
            success=success,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        session.add(log)
        await session.flush()
        logger.info(f"Logged player lookup by user {user_id}: player {player_id} (success={success})")
        return log
