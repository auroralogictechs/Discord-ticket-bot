# Discord Ticket Bot

A Discord bot designed to manage support tickets efficiently through Discord servers. This bot allows users to create tickets via interactive buttons or commands, manages conversations between users and support staff in dedicated channels and DMs, and supports AI-powered instant assistance using OpenAI's GPT model.

---

## Features

- Users can create support tickets through a button or slash command.
- Each ticket opens a dedicated private support channel visible only to staff.
- Users communicate with support staff through Discord DMs linked to their tickets.
- Staff can respond, manage, and close tickets with ease.
- AI-powered quick assistance for users via OpenAI GPT integration.
- Persistent and searchable ticket and message history stored in SQLite database.
- Slash commands for setup, ticket closure, and ticket information retrieval.
- Permission checks to restrict critical commands to staff roles.
- Supports detailed logging for monitoring bot activity and errors.

---

## Prerequisites

- Python 3.8 or later installed and added to system PATH.
- Discord Bot Token with privileged intents enabled:
  - Message Content Intent
  - Server Members Intent
- OpenAI API key (optional) for AI assistance.
- Discord server and role IDs used for configuration.

---

## Setup Instructions

### 1. Clone or Download the Bot Files

Place all bot files in a dedicated folder.

### 2. Configure Environment Variables

Create a `.env` file in the bot folder with the following keys:

DISCORD_TOKEN=your_discord_bot_token
MAIN_GUILD_ID=your_main_guild_id
SUPPORT_GUILD_ID=your_support_guild_id
STAFF_ROLE_ID=your_staff_role_id
TICKET_CATEGORY_ID=your_ticket_category_id
OPENAI_API_KEY=your_openai_api_key (optional)


Alternatively, use the `setup_bot_folder.bat` script to generate this `.env` file automatically with placeholder values.

### 3. Install Dependencies

Run the `setup_bot.bat` Windows batch script to:

- Verify Python installation
- Install required packages:
  - discord.py (>=2.3.2)
  - python-dotenv (>=1.0.0)
  - openai (>=0.28.0)
- Check that `.env` file exists

Or manually install via:

pip install "discord.py>=2.3.2" "python-dotenv>=1.0.0" "openai>=0.28.0"

### 4. Start the Bot

Run the bot with:
python main_bot.py

Or use the `start_bot.bat` script on Windows.

---

## Usage

### Slash Commands

- `/setup [channel]`  
  Sets up the ticket system panel with a "Create Ticket" button in the specified text channel or current channel if none provided. Requires `Manage Guild` permission.

- `/close <ticket_id>`  
  (Staff only) Closes an open ticket by ticket ID.

- `/ticket_info <ticket_id>`  
  (Staff only) Retrieves detailed information about a ticket.

### Ticket Workflow

- Users click the "Create Ticket" button or send a DM to the bot.
- A ticket is created if the user has no open ticket, including a private support channel.
- Messages from users in DM are forwarded to support channels.
- Staff replies in support channels are forwarded to users via DM.
- Staff can close tickets via button or command.
- Users may request instant AI help by sending a DM starting with `ai:` (e.g., `ai: How to reset my password?`).

---

## Configuration

Key environment variables in `.env`:

| Variable           | Description                              |
|--------------------|----------------------------------------|
| `DISCORD_TOKEN`    | Discord bot token                       |
| `MAIN_GUILD_ID`    | Primary guild/server ID                 |
| `SUPPORT_GUILD_ID` | Support guild/server ID                 |
| `STAFF_ROLE_ID`    | Role ID for support staff               |
| `TICKET_CATEGORY_ID`| Category ID under which tickets are created |
| `OPENAI_API_KEY`   | OpenAI API key for AI assistance (optional) |

---

## Database

- Uses SQLite database named `tickets.db`.
- Tables:
  - `tickets` - stores ticket metadata (id, user, status, channel id, timestamps).
  - `ticket_messages` - stores message history for tickets.

---

## Permissions & Roles

- Only users with the configured `STAFF_ROLE_ID` can close tickets or view ticket details.
- Ticket support channels are created with permissions set for staff and hidden from everyone else.
- Make sure your bot has the necessary permissions to manage channels and read/send messages.

---

## Troubleshooting

- If Python is not detected, install Python 3.8+ and add it to PATH.
- Check `.env` file is correctly populated and placed in the bot directory.
- In the Discord Developer Portal, ensure privileged gateway intents are enabled.
- Ensure the bot has appropriate role permissions on your servers.
- If users cannot receive DMs, advise them to check privacy settings allowing DMs from server members.

---

## Included Scripts

- `main_bot.py`: Main bot program.
- `setup_bot.bat`: Installs dependencies and verifies environment.
- `setup_bot_folder.bat`: Quick `.env` file generation.
- `start_bot.bat`: Launches the bot.

---

## License

MIT License — free to use and modify.

---

## Acknowledgements

- Built with [discord.py](https://discordpy.readthedocs.io/)
- AI assistance powered by OpenAI

---

For questions or improvements, modify the code in `main_bot.py` or contact your Discord bot administrator.
