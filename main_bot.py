import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio
import json
import os
import logging
from datetime import datetime
import openai
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration class with error checking
class Config:
    def __init__(self):
        # Check if .env file exists
        if not os.path.exists('.env'):
            logger.error("❌ .env file not found!")
            logger.error("Please make sure .env file is in the same folder as this script")
            input("Press Enter to exit...")
            exit(1)
        
        # Get Discord token
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        if not self.DISCORD_TOKEN:
            logger.error("❌ DISCORD_TOKEN not found in .env file!")
            logger.error("Please add your Discord bot token to the .env file")
            input("Press Enter to exit...")
            exit(1)
        
        # Get and validate guild IDs
        try:
            main_guild_str = os.getenv('MAIN_GUILD_ID')
            if not main_guild_str:
                raise ValueError("MAIN_GUILD_ID is empty")
            self.MAIN_GUILD_ID = int(main_guild_str)
            
            support_guild_str = os.getenv('SUPPORT_GUILD_ID')
            if not support_guild_str:
                raise ValueError("SUPPORT_GUILD_ID is empty")
            self.SUPPORT_GUILD_ID = int(support_guild_str)
            
            staff_role_str = os.getenv('STAFF_ROLE_ID')
            if not staff_role_str:
                raise ValueError("STAFF_ROLE_ID is empty")
            self.STAFF_ROLE_ID = int(staff_role_str)
            
            category_str = os.getenv('TICKET_CATEGORY_ID')
            if not category_str:
                raise ValueError("TICKET_CATEGORY_ID is empty")
            self.TICKET_CATEGORY_ID = int(category_str)
            
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Error with Discord IDs in .env file: {e}")
            logger.error("Please make sure all Discord IDs are valid numbers in your .env file")
            input("Press Enter to exit...")
            exit(1)
        
        # Optional OpenAI API key
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        if self.OPENAI_API_KEY:
            try:
                openai.api_key = self.OPENAI_API_KEY
                logger.info("✅ OpenAI API key found - AI assistance enabled")
            except Exception as e:
                logger.warning(f"⚠️ OpenAI setup error: {e}")
        else:
            logger.info("ℹ️ OpenAI API key not found - AI assistance disabled")
        
        # Validation successful
        logger.info("✅ Configuration loaded successfully")
        logger.info(f"✅ Main Guild ID: {self.MAIN_GUILD_ID}")
        logger.info(f"✅ Support Guild ID: {self.SUPPORT_GUILD_ID}")
        logger.info(f"✅ Staff Role ID: {self.STAFF_ROLE_ID}")
        logger.info(f"✅ Ticket Category ID: {self.TICKET_CATEGORY_ID}")

config = Config()

# Database setup
class Database:
    def __init__(self, db_name="tickets.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create tickets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP NULL,
                support_channel_id INTEGER,
                category TEXT DEFAULT 'general'
            )
        """)
        
        # Create messages table for ticket history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                message_content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
    
    def create_ticket(self, ticket_id, user_id, username, support_channel_id, category='general'):
        """Create a new ticket in the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO tickets (ticket_id, user_id, username, support_channel_id, category)
                VALUES (?, ?, ?, ?, ?)
            """, (ticket_id, user_id, username, support_channel_id, category))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def close_ticket(self, ticket_id):
        """Close a ticket"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
        """, (ticket_id,))
        
        conn.commit()
        conn.close()
    
    def get_ticket(self, ticket_id):
        """Get ticket information"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tickets WHERE ticket_id = ?
        """, (ticket_id,))
        
        ticket = cursor.fetchone()
        conn.close()
        return ticket
    
    def get_user_open_ticket(self, user_id):
        """Get user's open ticket if any"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tickets WHERE user_id = ? AND status = 'open'
        """, (user_id,))
        
        ticket = cursor.fetchone()
        conn.close()
        return ticket
    
    def add_message(self, ticket_id, author_id, author_name, message_content):
        """Add a message to ticket history"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ticket_messages (ticket_id, author_id, author_name, message_content)
            VALUES (?, ?, ?, ?)
        """, (ticket_id, author_id, author_name, message_content))
        
        conn.commit()
        conn.close()

# Initialize database
db = Database()

# FIXED: Bot setup with correct intents
intents = discord.Intents.default()
intents.message_content = True  # For reading message content
intents.guilds = True           # For guild operations
intents.guild_messages = True   # For guild messages
intents.members = True          # For member operations (privileged)

bot = commands.Bot(command_prefix='!', intents=intents)

# Utility functions
def generate_ticket_id(user_id):
    """Generate a unique ticket ID"""
    return f"ticket-{user_id}-{int(datetime.now().timestamp())}"

async def get_ai_response(question):
    """Get AI response for general queries"""
    if not config.OPENAI_API_KEY:
        return "AI assistance is not configured. Please contact a staff member for help."
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful support assistant. Provide brief, helpful responses to user questions."},
                {"role": "user", "content": question}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "I'm having trouble accessing AI assistance right now. Please contact a staff member for help."

# Ticket creation view with buttons
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='📝 Create Ticket', style=discord.ButtonStyle.primary, custom_id='create_ticket')
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_ticket_creation(interaction)
    
    async def handle_ticket_creation(self, interaction: discord.Interaction):
        """Handle ticket creation from button or command"""
        user = interaction.user
        
        # Check if user already has an open ticket
        existing_ticket = db.get_user_open_ticket(user.id)
        if existing_ticket:
            await interaction.response.send_message(
                f"You already have an open ticket: {existing_ticket[1]}", 
                ephemeral=True
            )
            return
        
        # Generate ticket ID
        ticket_id = generate_ticket_id(user.id)
        
        try:
            # Get support guild
            support_guild = bot.get_guild(config.SUPPORT_GUILD_ID)
            if not support_guild:
                await interaction.response.send_message(
                    "❌ Support server not found. Please contact an administrator.", 
                    ephemeral=True
                )
                logger.error(f"Support guild {config.SUPPORT_GUILD_ID} not found")
                return
            
            # Create support channel
            category = discord.utils.get(support_guild.categories, id=config.TICKET_CATEGORY_ID)
            if not category:
                await interaction.response.send_message(
                    "❌ Ticket category not found. Please contact an administrator.", 
                    ephemeral=True
                )
                logger.error(f"Ticket category {config.TICKET_CATEGORY_ID} not found")
                return
            
            # Set permissions for the channel
            staff_role = support_guild.get_role(config.STAFF_ROLE_ID)
            if not staff_role:
                await interaction.response.send_message(
                    "❌ Staff role not found. Please contact an administrator.", 
                    ephemeral=True
                )
                logger.error(f"Staff role {config.STAFF_ROLE_ID} not found")
                return
            
            overwrites = {
                support_guild.default_role: discord.PermissionOverwrite(read_messages=False),
                staff_role: discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True,
                    manage_messages=True
                )
            }
            
            # Create the support channel
            support_channel = await support_guild.create_text_channel(
                name=f"ticket-{user.name}",
                category=category,
                overwrites=overwrites
            )
            
            # Store ticket in database
            db.create_ticket(ticket_id, user.id, str(user), support_channel.id)
            
            # Create initial embed for support channel
            embed = discord.Embed(
                title=f"🎫 Ticket: {ticket_id}",
                description=f"**User:** {user.mention} ({user})\n**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Status", value="🟢 Open", inline=False)
            embed.add_field(name="Instructions", value="User will send their query via DM. Staff can respond here.", inline=False)
            
            # Add close button for staff
            close_view = TicketCloseView(ticket_id)
            await support_channel.send(f"<@&{config.STAFF_ROLE_ID}>", embed=embed, view=close_view)
            
            # Send DM to user
            dm_embed = discord.Embed(
                title="🎫 Ticket Created Successfully!",
                description=f"Your ticket `{ticket_id}` has been created.",
                color=discord.Color.green()
            )
            dm_embed.add_field(
                name="What's Next?",
                value="Please describe your issue or question in detail. Our support team will respond as soon as possible.",
                inline=False
            )
            dm_embed.add_field(
                name="Need Quick Help?",
                value="Type your question starting with `ai:` for instant AI assistance (e.g., `ai: How do I reset my password?`)",
                inline=False
            )
            
            try:
                await user.send(embed=dm_embed)
                await interaction.response.send_message(
                    f"✅ Ticket created successfully! Check your DMs for details. Ticket ID: `{ticket_id}`",
                    ephemeral=True
                )
                logger.info(f"✅ Ticket {ticket_id} created for user {user}")
            except discord.Forbidden:
                await interaction.response.send_message(
                    f"✅ Ticket created! However, I couldn't send you a DM. Please check your privacy settings.\nTicket ID: `{ticket_id}`",
                    ephemeral=True
                )
                logger.warning(f"Could not DM user {user} for ticket {ticket_id}")
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while creating your ticket. Please contact an administrator.",
                ephemeral=True
            )

# Ticket close view for staff
class TicketCloseView(discord.ui.View):
    def __init__(self, ticket_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
    
    @discord.ui.button(label='🔒 Close Ticket', style=discord.ButtonStyle.danger, custom_id='close_ticket')
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has staff role
        if config.STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ Only staff members can close tickets.", ephemeral=True)
            return
        
        # Close ticket in database
        db.close_ticket(self.ticket_id)
        
        # Update embed
        embed = discord.Embed(
            title=f"🎫 Ticket: {self.ticket_id}",
            description=f"**Closed by:** {interaction.user.mention}\n**Closed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color=discord.Color.red()
        )
        embed.add_field(name="Status", value="🔴 Closed", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Get ticket info
        ticket_info = db.get_ticket(self.ticket_id)
        if ticket_info:
            user_id = ticket_info[2]  # user_id is at index 2
            user = bot.get_user(user_id)
            
            if user:
                try:
                    close_embed = discord.Embed(
                        title="🎫 Ticket Closed",
                        description=f"Your ticket `{self.ticket_id}` has been closed by our support team.",
                        color=discord.Color.orange()
                    )
                    close_embed.add_field(
                        name="Need More Help?",
                        value="Feel free to create a new ticket if you need further assistance.",
                        inline=False
                    )
                    await user.send(embed=close_embed)
                    logger.info(f"✅ Ticket {self.ticket_id} closed by {interaction.user}")
                except discord.Forbidden:
                    logger.warning(f"Could not DM user {user_id} about ticket closure")

# Bot Events
@bot.event
async def on_ready():
    logger.info(f'✅ {bot.user} has connected to Discord!')
    
    # Verify guild access
    main_guild = bot.get_guild(config.MAIN_GUILD_ID)
    support_guild = bot.get_guild(config.SUPPORT_GUILD_ID)
    
    if not main_guild:
        logger.error(f"❌ Cannot access main guild {config.MAIN_GUILD_ID}. Make sure bot is invited!")
        return
    else:
        logger.info(f"✅ Connected to main guild: {main_guild.name}")
    
    if not support_guild:
        logger.error(f"❌ Cannot access support guild {config.SUPPORT_GUILD_ID}. Make sure bot is invited!")
        return
    else:
        logger.info(f"✅ Connected to support guild: {support_guild.name}")
    
    # Add persistent views
    bot.add_view(TicketView())
    bot.add_view(TicketCloseView(""))  # Empty ticket_id for persistent view
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    logger.info("🎫 Discord Ticket Bot is ready!")

@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Handle DM messages
    if isinstance(message.channel, discord.DMChannel):
        await handle_dm_message(message)
    
    # Handle support channel messages
    elif message.guild and message.guild.id == config.SUPPORT_GUILD_ID:
        await handle_support_message(message)
    
    # Process commands
    await bot.process_commands(message)

async def handle_dm_message(message):
    """Handle messages in DMs"""
    user = message.author
    content = message.content
    
    # Check if user has an open ticket
    ticket_info = db.get_user_open_ticket(user.id)
    
    if not ticket_info:
        # No open ticket - offer to create one or provide AI assistance
        if content.lower().startswith('ai:'):
            # AI assistance
            question = content[3:].strip()
            ai_response = await get_ai_response(question)
            
            embed = discord.Embed(
                title="🤖 AI Assistant",
                description=ai_response,
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Need More Help?",
                value="If this doesn't solve your issue, you can create a ticket for human support.",
                inline=False
            )
            
            await message.channel.send(embed=embed)
        else:
            # Suggest creating a ticket
            embed = discord.Embed(
                title="💬 Message Received",
                description="I see you'd like some help! You don't currently have an open support ticket.",
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="Create a Ticket",
                value="To get help from our support team, please create a ticket in the main server or use the button below.",
                inline=False
            )
            embed.add_field(
                name="Quick AI Help",
                value="For instant assistance, start your message with `ai:` (e.g., `ai: How do I reset my password?`)",
                inline=False
            )
            
            # Add create ticket button
            view = TicketView()
            await message.channel.send(embed=embed, view=view)
    else:
        # User has an open ticket - forward message to support channel
        ticket_id = ticket_info[1]
        support_channel_id = ticket_info[7]  # support_channel_id is at index 7
        
        # Get support channel
        support_channel = bot.get_channel(support_channel_id)
        if support_channel:
            # Add message to database
            db.add_message(ticket_id, user.id, str(user), content)
            
            # Forward message to support channel
            embed = discord.Embed(
                title=f"💬 Message from {user}",
                description=content,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            await support_channel.send(embed=embed)
            
            # Confirm receipt to user
            await message.add_reaction('✅')

async def handle_support_message(message):
    """Handle messages in support channels"""
    if message.author.bot:
        return
    
    # Check if this is a ticket channel
    channel_name = message.channel.name
    if channel_name.startswith('ticket-'):
        # Find the ticket in database
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE support_channel_id = ? AND status = 'open'", 
                      (message.channel.id,))
        ticket_info = cursor.fetchone()
        conn.close()
        
        if ticket_info:
            ticket_id = ticket_info[1]
            user_id = ticket_info[2]
            
            # Add message to database
            db.add_message(ticket_id, message.author.id, str(message.author), message.content)
            
            # Forward message to user DM
            user = bot.get_user(user_id)
            if user:
                try:
                    embed = discord.Embed(
                        title=f"💬 Support Response",
                        description=message.content,
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
                    
                    await user.send(embed=embed)
                    await message.add_reaction('✅')
                except discord.Forbidden:
                    await message.channel.send("⚠️ Could not send DM to user (DMs disabled)")

# Slash Commands
@bot.tree.command(name="setup", description="Setup the ticket system panel")
@app_commands.describe(channel="Channel to send the ticket panel to")
@app_commands.default_permissions(manage_guild=True)
async def setup_tickets(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    """Setup ticket system panel"""
    if not channel:
        channel = interaction.channel
    
    embed = discord.Embed(
        title="🎫 Support Ticket System",
        description="Need help? Create a support ticket and our team will assist you!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="How it works:",
        value="1️⃣ Click the button below to create a ticket\n2️⃣ You'll receive a DM to describe your issue\n3️⃣ Our support team will respond via the ticket\n4️⃣ Your conversation happens through DMs",
        inline=False
    )
    embed.add_field(
        name="Quick AI Help",
        value="For instant assistance, DM the bot with your question starting with `ai:`",
        inline=False
    )
    
    view = TicketView()
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Ticket panel set up in {channel.mention}!", ephemeral=True)

@bot.tree.command(name="close", description="Close a ticket (Staff only)")
@app_commands.describe(ticket_id="The ticket ID to close")
async def close_ticket_command(interaction: discord.Interaction, ticket_id: str):
    """Close a ticket via command"""
    # Check if user has staff role
    if config.STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ Only staff members can close tickets.", ephemeral=True)
        return
    
    ticket_info = db.get_ticket(ticket_id)
    if not ticket_info:
        await interaction.response.send_message("❌ Ticket not found.", ephemeral=True)
        return
    
    if ticket_info[4] == 'closed':  # status is at index 4
        await interaction.response.send_message("❌ Ticket is already closed.", ephemeral=True)
        return
    
    # Close ticket
    db.close_ticket(ticket_id)
    
    # Notify user
    user = bot.get_user(ticket_info[2])  # user_id is at index 2
    if user:
        try:
            embed = discord.Embed(
                title="🎫 Ticket Closed",
                description=f"Your ticket `{ticket_id}` has been closed by {interaction.user.mention}.",
                color=discord.Color.orange()
            )
            await user.send(embed=embed)
        except discord.Forbidden:
            pass
    
    await interaction.response.send_message(f"✅ Ticket `{ticket_id}` has been closed.", ephemeral=True)

@bot.tree.command(name="ticket_info", description="Get information about a ticket")
@app_commands.describe(ticket_id="The ticket ID to check")
async def ticket_info(interaction: discord.Interaction, ticket_id: str):
    """Get ticket information"""
    # Check if user has staff role
    if config.STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ Only staff members can view ticket information.", ephemeral=True)
        return
    
    ticket_info = db.get_ticket(ticket_id)
    if not ticket_info:
        await interaction.response.send_message("❌ Ticket not found.", ephemeral=True)
        return
    
    user = bot.get_user(ticket_info[2])
    status_emoji = "🟢" if ticket_info[4] == 'open' else "🔴"
    
    embed = discord.Embed(
        title=f"🎫 Ticket Information: {ticket_id}",
        color=discord.Color.blue() if ticket_info[4] == 'open' else discord.Color.red()
    )
    embed.add_field(name="User", value=f"{user.mention if user else 'Unknown'} ({ticket_info[3]})", inline=True)
    embed.add_field(name="Status", value=f"{status_emoji} {ticket_info[4].title()}", inline=True)
    embed.add_field(name="Created", value=ticket_info[5], inline=True)
    if ticket_info[6]:  # closed_at
        embed.add_field(name="Closed", value=ticket_info[6], inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore command not found errors
    else:
        logger.error(f"Command error: {error}")

# Run the bot
if __name__ == "__main__":
    try:
        logger.info("🚀 Starting Discord Ticket Bot...")
        bot.run(config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        input("Press Enter to exit...")