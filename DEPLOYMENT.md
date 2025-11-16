# Deployment Guide

This guide provides instructions for deploying the Discord Translator Bot.

## Prerequisites

- Docker and Docker Compose installed
- Discord Bot Token
- Google Gemini API Key

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   GOOGLE_GENAI_API_KEY=your_gemini_api_key_here
   ```

## Deployment Options

### Option 1: Docker Compose (Recommended)

1. Build and start the bot:
   ```bash
   docker compose up -d
   ```

2. View logs:
   ```bash
   docker compose logs -f translator-bot
   ```

3. Stop the bot:
   ```bash
   docker compose down
   ```

### Option 2: Using Pre-built Docker Image from GitHub Container Registry

1. Pull the latest image:
   ```bash
   docker pull ghcr.io/anyoneclown/ds-translator:latest
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name discord-translator-bot \
     --env-file .env \
     --restart unless-stopped \
     ghcr.io/anyoneclown/ds-translator:latest
   ```

### Option 3: Manual Docker Build

1. Build the image:
   ```bash
   docker build -t discord-translator-bot .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name discord-translator-bot \
     --env-file .env \
     --restart unless-stopped \
     discord-translator-bot
   ```

### Option 4: Direct Python Execution

1. Install Python 3.12 or higher

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   export DISCORD_TOKEN=your_discord_bot_token_here
   export GOOGLE_GENAI_API_KEY=your_gemini_api_key_here
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

## Automated Deployment with GitHub Actions

This repository includes a GitHub Actions workflow that automatically:
- Builds a Docker image on every push to the main branch
- Publishes the image to GitHub Container Registry (GHCR)
- Tags images with branch name, commit SHA, and 'latest' for main branch

The workflow runs on:
- Push to main branch
- Pull requests to main branch
- Manual workflow dispatch

### Using the Automated Image

After a successful workflow run, you can use the published image:

```bash
# Pull the latest image
docker pull ghcr.io/anyoneclown/ds-translator:latest

# Or use a specific commit
docker pull ghcr.io/anyoneclown/ds-translator:main-<commit-sha>
```

## Production Deployment Considerations

### Security
- Never commit `.env` file to version control
- Use secrets management for production (e.g., Docker secrets, Kubernetes secrets)
- Regularly update dependencies for security patches

### Monitoring
- Check logs regularly: `docker compose logs -f`
- Set up external monitoring for bot uptime
- Monitor API usage for Discord and Gemini APIs

### Scaling
- This bot is designed to run as a single instance
- For multiple servers, one instance is sufficient
- Monitor memory and CPU usage

### Updates
1. Pull the latest code or image
2. Rebuild or pull new image: `docker compose pull`
3. Restart the service: `docker compose up -d`

## Troubleshooting

### Bot not starting
- Check that environment variables are set correctly in `.env`
- Verify Discord token is valid
- Verify Gemini API key is valid
- Check logs: `docker compose logs translator-bot`

### Translation not working
- Verify Gemini API key has proper permissions
- Check API quota limits
- Review logs for API errors

### Discord connection issues
- Verify bot has proper intents enabled in Discord Developer Portal
- Check network connectivity
- Ensure Discord token hasn't expired

## Configuration Files

- `Dockerfile`: Defines the Docker image build process
- `compose.yaml`: Docker Compose configuration
- `.env.example`: Template for environment variables
- `.dockerignore`: Files excluded from Docker build context
- `.github/workflows/deploy.yml`: CI/CD pipeline configuration
