# Discord Translator Bot

A Discord bot that translates messages using Google's Gemini API, built with SOLID principles for easy maintenance and extensibility.

## Features

- 🌐 **Auto-translation**: Automatically translate messages from users with the "Translator" role
- 🔄 **Manual translation**: Translate messages to English or any language on command
- ⏰ **Event scheduling**: Schedule role pings at specific times (UTC)
- 📊 **User statistics**: Track translations, messages, and user activity
- 💾 **Database integration**: CockroachDB with SQLAlchemy for persistent storage
- 🏗️ **SOLID architecture**: Clean, maintainable, and extensible code structure

## Architecture

The project follows SOLID principles:

- **Single Responsibility**: Each class has one clear purpose
  - `TranslationService`: Handles all translation logic
  - `EventSchedulerService`: Manages scheduled events
  - `TranslationHandler`: Handles translation commands
  - `EventHandler`: Handles scheduling commands
  - `BotConfig`: Manages configuration

- **Open/Closed**: Easy to extend without modifying existing code
- **Liskov Substitution**: Services implement interfaces
- **Interface Segregation**: Focused, minimal interfaces
- **Dependency Injection**: Dependencies injected through constructors

## Project Structure

```
ds-translator/
├── config/
│   ├── __init__.py
│   └── bot_config.py          # Configuration management
├── services/
│   ├── __init__.py
│   ├── translation_service.py  # Translation business logic
│   ├── event_scheduler_service.py  # Event scheduling logic
│   └── database_service.py    # Database operations
├── handlers/
│   ├── __init__.py
│   ├── translation_handler.py  # Translation command handlers
│   ├── event_handler.py        # Event command handlers
│   └── database_handler.py     # Stats and user commands
├── db/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy models
│   └── session.py             # Database session management
├── alembic/                   # Database migrations
│   ├── versions/
│   └── env.py
├── main.py                    # Application entry point
├── test_db.py                 # Database test script
├── requirements.txt
└── DATABASE.md                # Database documentation
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with:
```env
DISCORD_TOKEN=your_discord_bot_token
COMMAND_PREFIX=!
TRANSLATOR_ROLE=Translator
COCKROACHDB_URL=cockroachdb+asyncpg://user:password@host:26257/database
```

4. Run database migrations:
```bash
python -m alembic upgrade head
```

5. Test database connection (optional):
```bash
python test_db.py
```

## Commands

### Translation Commands

- `!en` - Translate a replied-to message to English
- `!t <language>` or `!translate <language>` - Translate to specified language

### Player Stats Commands

- `!stats <player_id>` - Fetch and display player statistics from kingshot.net API

### Event Scheduling Commands

- `!schedule YYYY-MM-DD HH:MM @Role1 @Role2 Message` - Schedule a role ping
- `!events` - List all scheduled events in the channel
- `!cancel <number>` - Cancel a scheduled event

### User Statistics Commands

- `!profile [@user]` - Show user profile (yours or another user's)

### Examples

```
!en
Reply to a message to translate it to English

!t Spanish
Translate to Spanish: Hello, how are you?

!schedule 2025-12-25 15:30 @Everyone @Moderators Christmas event starting!
Schedule an event for December 25, 2025 at 3:30 PM UTC

!events
List all scheduled events

!cancel 1
Cancel the first scheduled event

!stats 123456789
Fetch player statistics from API

!profile @SomeUser
View another user's profile
```

## Auto-Translation

Users with the "Translator" role will have their messages automatically translated to English.

## Database

The bot uses CockroachDB (PostgreSQL-compatible) for persistent storage of:
- User information and activity tracking
- Translation statistics
- Translation logs

See [DATABASE.md](DATABASE.md) for detailed documentation on:
- Database schema and models
- Migration management with Alembic
- Using DatabaseService in your code
- Best practices and troubleshooting

## Development

### Adding New Features

Thanks to the SOLID architecture, adding new features is straightforward:

1. **New Service**: Create a new service class in `services/`
2. **New Handler**: Create a handler in `handlers/`
3. **Register**: Add to `main.py` in the `TranslatorBot` class

### Example: Adding a New Feature

```python
# 1. Create service
class MyNewService(IMyService):
    def do_something(self):
        pass

# 2. Create handler
class MyNewHandler:
    def __init__(self, service: IMyService, bot: commands.Bot):
        self._service = service
        self._bot = bot
    
    def register_commands(self):
        @self._bot.command(name="mycommand")
        async def my_command(ctx):
            await self._handle_command(ctx)

# 3. Register in main.py
self.my_service = MyNewService()
self.my_handler = MyNewHandler(self.my_service, self.bot)
self.my_handler.register_commands()
```

## License

MIT License
