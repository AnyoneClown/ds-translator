#!/bin/bash

# Discord Translator Bot - Deployment Script
# This script helps with the initial setup and deployment of the bot

set -e

echo "=== Discord Translator Bot Deployment ==="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "No .env file found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ Created .env file from .env.example"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env file and add your credentials:"
        echo "   - DISCORD_TOKEN"
        echo "   - GOOGLE_GENAI_API_KEY"
        echo ""
        read -p "Press Enter after you've updated the .env file..."
    else
        echo "Error: .env.example not found"
        exit 1
    fi
else
    echo "✓ .env file already exists"
fi

# Validate .env file has required variables
if ! grep -q "DISCORD_TOKEN=" .env || ! grep -q "GOOGLE_GENAI_API_KEY=" .env; then
    echo "Error: .env file is missing required variables"
    echo "Required: DISCORD_TOKEN, GOOGLE_GENAI_API_KEY"
    exit 1
fi

# Check if values are set (not default)
if grep -q "your_discord_bot_token_here" .env || grep -q "your_gemini_api_key_here" .env; then
    echo "⚠️  Warning: .env file contains placeholder values"
    echo "Please update .env with your actual credentials"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "=== Building and starting the bot ==="
echo ""

# Build and start the service
docker compose up -d --build

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Bot is now running in the background."
echo ""
echo "Useful commands:"
echo "  View logs:         docker compose logs -f translator-bot"
echo "  Stop bot:          docker compose down"
echo "  Restart bot:       docker compose restart translator-bot"
echo "  Rebuild and start: docker compose up -d --build"
echo ""
echo "Check logs to verify the bot is running correctly:"
echo "  docker compose logs translator-bot"
