# Venomshade Discord Bot

⛧ A feature-rich Discord bot for community management, built with discord.py.

## Features

◆ **Welcome System** — Auto-welcome messages with embeds and emojis on member join. Pings new members in rules and roles channels (auto-deleted after 5 minutes).

◆ **Word Guessing Game** — Slash commands for setting words, hints, leaderboards, and winners.

◆ **Confessions** — Anonymous confession system with thread-based replies.

◆ **Auto-Reactions** — Keyword and mention triggered reactions with custom messages.

◆ **Snipe** — View deleted messages in channels.

◆ **Media Handler** — Auto-detects and formats Instagram/TikTok links.

◆ **Fun Commands** — Random facts, insults, and auto-reactions to greetings.

## Requirements

```
discord.py
aiohttp
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Setup

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure `config.py`:

```python
BOT_TOKEN = "your-bot-token"
GUILD_ID = your-server-id
WELCOME_CHANNEL_IDS = [channel_ids...]
RULES_CHANNEL_ID = rules-channel-id
ROLES_CHANNEL_ID = roles-channel-id
GAME_CHANNEL_ID = word-game-channel-id
CONFESSION_CHANNEL_ID = confession-channel-id
SOCIAL_CHANNEL_ID = instagram-tiktok-channel-id
BOT_ACCESS_ROLE = role-id-for-bot-access
NO_BOT_USE_USER_ID = [bot-user-ids...]
NO_BOT_USE_CHANNEL_ID = [channel-ids...]
HICHAT = "<:emoji:id>"
BOW = "<:emoji:id>"
MINECAT = "<:emoji:id>"
ALRIGHT = "<:emoji:id>"
HEARTX = "<:emoji:id>"
```

4. Run the bot:

```bash
python app.py
```

## Commands

### General

| Command | Description | Access |
|---------|-------------|-------|
| `/testwelcome` | Test the welcome message | Bot Access |
| `/snipe` | Show the last deleted message | Bot Access |
| `/fact` | Get a random fact | Everyone |
| `/insult` | Insult someone | Everyone |

### Word Game

| Command | Description | Access |
|---------|-------------|-------|
| `/word set <word>` | Set a new word for guessing | Bot Access |
| `/word reset` | Reset the leaderboard | Bot Access |
| `/word clear` | Skip the current word | Bot Access |
| `/word clue <clue>` | Give a clue | Bot Access |
| `/word hint` | Reveal a letter hint | Everyone |
| `/word leaderboard` | View the top 10 scores | Everyone |
| `/word winner` | End the game and show winners | Everyone |

### Confessions

| Command | Description | Access |
|---------|-------------|-------|
| `/confession confess <text>` | Submit an anonymous confession | Everyone |
| `/confession delete <id>` | Delete a confession | Bot Access |

### Auto-Reactions

| Command | Description | Access |
|---------|-------------|-------|
| `/autoreact add <user> <keywords> <emoji> <message>` | Add an auto reaction | Bot Access |
| `/autoreact update <user> <keywords> <emoji> <message>` | Update an auto reaction | Bot Access |
| `/autoreact remove <user>` | Remove an auto reaction | Bot Access |
| `/autoreact list` | List all auto reactions | Bot Access |

## Project Structure

```
VENOMSHADE/
├── app.py           # Main bot file with all commands and events
├── config.py        # Configuration (IDs, tokens, emojis)
├── storage.py       # JSON data persistence
├── autoReaction.py  # Auto-reaction system
├── apiFetches.py    # External API calls (facts, insults)
├── media.py         # Instagram/TikTok media handler
├── data.json        # Persistent bot data (confessions, counters)
├── userdata.json    # Auto-reaction user settings
└── requirements.txt
```

## Bot Access Role

Commands marked "Bot Access" require the role set in `config.py` (`BOT_ACCESS_ROLE`). Users without this role will see an "ACCESS DENIED" embed when attempting to use these commands.

## Data Persistence

- **data.json** — Stores confession count, confessions mapping, and media post counter
- **userdata.json** — Stores auto-reaction configurations

Both files auto-save every 60 seconds and on shutdown.

## Auto-Reactions

When someone mentions a tracked user or uses a keyword, the bot will:
1. Add a reaction emoji
2. Reply with a configured message

Auto-reactions are checked on every message in non-excluded channels.

## Media Handler

The bot monitors the `SOCIAL_CHANNEL_ID` for Instagram/TikTok links:
- **Instagram reels/posts** — Reformats links, auto-reacts, and deletes the original message
- **TikTok links** — Auto-reacts and deletes the original message
- **Other messages** — Auto-deleted (except mentions)

## Message Auto-Reactions

The bot automatically reacts to these messages:
- `hi`, `hlo`, `hy`, `hello`, `hey`, `oi`, `hai` — React with hi emoji
- `ok` — Reply with alright emoji
- `fact` — Reply with a random fact embed
