# F1 Live Timetable System Deployment Guide

A real-time Formula 1 race data tracking system that fetches lap times and race standings, processes them through a message queue, and delivers updates to Telegram.

## System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │     │                 │
│   F1 Producer   │────▶│    RabbitMQ     │────▶│  Nuclio Function│────▶│  Telegram Bot   │
│                 │     │                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                                                        │
        │                                                                        │
        ▼                                                                        ▼
┌─────────────────┐                                                    ┌─────────────────┐
│                 │                                                    │                 │
│   FastF1 API    │                                                    │   Telegram API  │
│                 │                                                    │                 │
└─────────────────┘                                                    └─────────────────┘
```

## Prerequisites

- Docker and Docker Compose installed
- Nuclio CLI installed
- Python 3.7+ installed
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))
- Your Telegram Chat ID


## Quick Start

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd f1-live-timetable
   ```

2. Create a `.env` file in the project root with your configuration:
   ```
   # Telegram Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here #use token generated before
   TELEGRAM_CHAT_ID=your_chat_id_here #chat id of your telegram bot

   # Application Configuration
   CHECK_INTERVAL=90
   TEST_MODE=True
   TEST_YEAR=2024
   TEST_RACE=Italian
   SIMULATE_LIVE=True
   CURRENT_LAP=1
   ```

3. Start the entire system with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Monitor the logs:
   ```bash
   docker-compose logs -f
   ```

5. Connect to localhost:8070 and, after creating a new project, create a new function importing the function.yaml file 
Remember to update my_token and my_telegram_ID and rabbitmq url, you can check rabbitmq url by running this line:
   ```bash
   docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' f1livebot1-rabbitmq-1
   ```
6. Check host in connection settings of function and click deploy

## Configuration Options

| Environment Variable | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot API token |
| `TELEGRAM_CHAT_ID` | ID of the Telegram chat to send messages to |
| `CHECK_INTERVAL` | Time between updates in seconds |
| `TEST_MODE` | Enable test mode with historical race data |
| `TEST_YEAR` | Year of the test race to simulate |
| `TEST_RACE` | Name of the test race (e.g., "Italian") |
| `SIMULATE_LIVE` | Simulate live race progression |
| `CURRENT_LAP` | Starting lap number for simulation |

## Project Components

### 1. F1 Data Producer (`f1-producer`)
- Fetches race data from FastF1 API
- Simulates live race updates (when in test mode)
- Publishes formatted timetables to RabbitMQ
- Runs on a configurable interval

### 2. Message Broker (`rabbitmq`)
- Handles message queuing between components
- Provides MQTT protocol support
- Includes management interface at http://localhost:15672
  - Username: guest
  - Password: guest

### 3. Nuclio Dashboard (`nuclio-dashboard`)
- Serverless function platform for processing messages
- Available at http://localhost:8070
- Used to deploy and manage the Telegram notification function

## Extending the System

### Adding More Data Sources
Modify `f1_producer.py` to include additional data from the FastF1 API.

### Custom Formatting
Adjust the `create_timetable` function to change the formatting of the race updates.

### Additional Notification Channels
Create new Nuclio functions to send updates to other platforms (Slack, Discord, etc.)