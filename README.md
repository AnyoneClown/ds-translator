# Discord Translator Bot

A Discord bot that automatically translates messages using Google Gemini AI. Users with the "Translator" role will have their non-English messages automatically translated to English.

## Features

- **Automatic Translation**: Messages from users with the "Translator" role are automatically translated to English
- **Manual Translation Commands**: 
  - `!en` or `!translate en`: Translate a replied-to message to English
  - `!t <language>`: Translate a replied-to message to any specified language
- **Language Detection**: Automatically detects the source language
- **Smart Filtering**: Ignores commands, bot messages, and DMs

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended) OR Python 3.12+
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))
- Google Gemini API Key ([Get one here](https://aistudio.google.com/app/apikey))

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/AnyoneClown/ds-translator.git
   cd ds-translator
   ```

2. Create environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your credentials:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   GOOGLE_GENAI_API_KEY=your_gemini_api_key_here
   ```

4. Start the bot:
   ```bash
   docker compose up -d
   ```

## Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Enable the following **Privileged Gateway Intents**:
   - Message Content Intent
   - Server Members Intent
5. Copy the bot token and add it to your `.env` file
6. Go to OAuth2 > URL Generator:
   - Scopes: `bot`
   - Bot Permissions: 
     - Read Messages/View Channels
     - Send Messages
     - Read Message History
7. Use the generated URL to invite the bot to your server
8. Create a role named "Translator" in your Discord server
9. Assign the role to users who should have their messages auto-translated

## Usage

### Automatic Translation
Users with the "Translator" role will have their non-English messages automatically translated to English with a reply.

### Manual Commands
- **Translate to English**: Reply to a message and type `!en`
- **Translate to specific language**: Reply to a message and type `!t spanish` (or any other language)

## Deployment

For detailed deployment instructions including production setup, Docker options, and CI/CD information, see [DEPLOYMENT.md](DEPLOYMENT.md).

### Quick Deploy with Pre-built Image

```bash
docker pull ghcr.io/anyoneclown/ds-translator:latest
docker run -d --name discord-translator-bot --env-file .env --restart unless-stopped ghcr.io/anyoneclown/ds-translator:latest
```

## Development

### Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export DISCORD_TOKEN=your_token
   export GOOGLE_GENAI_API_KEY=your_key
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Architecture

- **main.py**: Discord bot logic and command handlers
- **gemini.py**: Google Gemini AI integration for translation
- **Dockerfile**: Container image definition
- **compose.yaml**: Docker Compose orchestration
- **requirements.txt**: Python dependencies

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on GitHub.