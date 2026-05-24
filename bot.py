import discord
from discord.ext import commands
from discord import app_commands
import io
import os
import logging
import datetime
import asyncio
from typing import Optional

# ========================================================================
# 1. SETTINGS AND CONFIGURATION (Railway Compatible)
# ========================================================================
# Fetches the bot token from Railway Environment Variables
TOKEN = os.getenv("DISCORD_TOKEN")

# ========================================================================
# 2. LOGGING SYSTEM
# ========================================================================
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

# Handler to save errors and logs into a file
handler = logging.FileHandler(filename='discord_bot.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Console handler to view logs instantly on Railway Dashboard
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# ========================================================================
# 3. BOT CLASS AND CONNECTION INFRASTRUCTURE
# ========================================================================
class ProDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        logger.info("Synchronizing slash commands...")
        try:
            await self.tree.sync()
            logger.info("Commands synchronized successfully.")
        except Exception as e:
            logger.error(f"Critical error during command synchronization: {e}")

    async def on_ready(self):
        logger.info(f"Bot successfully logged in! User: {self.user} (ID: {self.user.id})")
        logger.info("-" * 40)
        
        activity = discord.Activity(type=discord.ActivityType.watching, name="the Server and Commands")
        await self.change_presence(status=discord.Status.online, activity=activity)

bot = ProDiscordBot()

# ========================================================================
# 4. HELPER FUNCTIONS (Interface Designs)
# ========================================================================
def create_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """Generates stylish and standard embed messages across the system."""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
    embed.set_footer(text="Sleeping Bot Infrastructure", icon_url=bot.user.display_avatar.url if bot.user and bot.user.display_avatar else None)
    return embed

# ========================================================================
# 5. GLOBAL ERROR HANDLER
# ========================================================================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Prevents crashes during command executions and informs the user."""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Please slow down! Wait {error.retry_after:.2f} seconds to use this command again.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You do not have the required permissions to use this command.", ephemeral=True)
    else:
        logger.error(f"An unexpected error occurred while triggering the command: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An unexpected network error occurred while processing the command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred during the process.", ephemeral=True)
        except Exception:
            pass

# ========================================================================
# 6. ALL ACTIVE SLASH COMMANDS
# ========================================================================

# ---------------------------------------------------------
# COMMAND 1: /send (Dynamic Channel Message Sender)
# ---------------------------------------------------------
@bot.tree.command(name="send", description="Sends the desired text to the specified target channel.")
@app_commands.describe(
    channel="The target channel where the message will be sent",
    message="The text you want to send",
    show_sender="Do you want your name to appear at the bottom of the message?"
)
@app_commands.choices(show_sender=[
    app_commands.Choice(name="Yes, show", value="yes"),
    app_commands.Choice(name="No, keep hidden", value="no")
])
async def send_cmd(interaction: discord.Interaction, channel: discord.TextChannel, message: str, show_sender: str = "no"):
    # Triggers defer to prevent 3-second timeout limits
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        hata_embed = create_embed(
            title="❌ Channel Not Found", 
            description="The specified channel could not be found or the bot does not have permission to view it.", 
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=hata_embed)
        return

    # Formatting the sender info based on choice
    if show_sender == "yes":
        gonderilecek_icerik = f"{message}\n\n*👤 Sender: {interaction.user.mention}*"
    else:
        gonderilecek_icerik = message

    try:
        await channel.send(content=gonderilecek_icerik)
        basari_embed = create_embed("✅ Success", f"Your message has been successfully delivered to {channel.mention}.", discord.Color.green())
        await interaction.followup.send(embed=basari_embed)
        logger.info(f"[SEND] User {interaction.user} sent a message to channel {channel.id}.")
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot does not have permission to send messages to the target channel!")
    except Exception as e:
        await interaction.followup.send(f"❌ A technical error occurred while sending the message: {e}")

# ---------------------------------------------------------
# COMMAND 2: /txt (Personal TXT Document Creator)
# ---------------------------------------------------------
@bot.tree.command(name="txt", description="Instantly converts your text into a .txt document and sends it to you.")
@app_commands.describe(
    file_name="The name of the file to be created (e.g., notes)",
    content="The full text to be written inside the txt file"
)
async def txt_cmd(interaction: discord.Interaction, file_name: str, content: str):
    await interaction.response.defer(ephemeral=True)
    
    # File name optimization
    file_name = file_name.replace(" ", "_")
    if not file_name.endswith(".txt"):
        file_name += ".txt"
        
    # Creating a virtual file directly over RAM memory
    dosya_byte = io.BytesIO(content.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=file_name)
    
    embed = create_embed(
        title="📄 Your Document is Ready",
        description=f"The requested **{file_name}** file has been successfully created and attached below.",
        color=discord.Color.gold()
    )
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)

    try:
        await interaction.followup.send(embed=embed, file=discord_dosyasi)
        logger.info(f"[TXT] User {interaction.user} successfully generated the file {file_name}.")
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred while delivering the file: {e}")
    finally:
        dosya_byte.close()

# ---------------------------------------------------------
# COMMAND 3: /sendtxt (Dynamic Channel TXT Sender)
# ---------------------------------------------------------
@bot.tree.command(name="sendtxt", description="Converts the text into a .txt document and sends it directly to the target channel.")
@app_commands.describe(
    channel="The target channel where the file will be sent",
    file_name="The name of the file to be created",
    content="The text to be written inside the file",
    show_sender="Do you want your name to appear at the bottom of the message?"
)
@app_commands.choices(show_sender=[
    app_commands.Choice(name="Yes, show", value="yes"),
    app_commands.Choice(name="No, keep hidden", value="no")
])
async def sendtxt_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file_name: str, content: str, show_sender: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        await interaction.followup.send("❌ Target channel not found! Please check the permissions.")
        return

    file_name = file_name.replace(" ", "_")
    if not file_name.endswith(".txt"):
        file_name += ".txt"

    kanal_embed = discord.Embed(
        title="📁 A New Document Has Been Uploaded",
        color=discord.Color.dark_theme(),
        timestamp=discord.utils.utcnow()
    )
    
    if show_sender == "yes":
        kanal_embed.add_field(name="Sender", value=interaction.user.mention, inline=False)
    
    kanal_embed.add_field(name="File Name", value=f"`{file_name}`", inline=False)
    kanal_embed.set_footer(text="Automatic File Delivery System")

    dosya_byte = io.BytesIO(content.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=file_name)

    try:
        await channel.send(embed=kanal_embed, file=discord_dosyasi)
        await interaction.followup.send(f"✅ The document **{file_name}** has been successfully uploaded to {channel.mention}.")
        logger.info(f"[SENDTXT] {interaction.user} -> sent the file {file_name} to channel {channel.id}.")
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot's permission to send file attachments or embed messages to this channel is disabled!")
    except Exception as e:
        await interaction.followup.send(f"❌ Error during execution: {e}")
    finally:
        dosya_byte.close()

# ---------------------------------------------------------
# COMMAND 4: /paste (Text Panel Formatter)
# ---------------------------------------------------------
@bot.tree.command(name="paste", description="Converts long texts into a clean block format without cluttering the chat.")
@app_commands.describe(title="The title of the text", content="The long text to be wrapped in a block")
async def paste_cmd(interaction: discord.Interaction, title: str, content: str):
    await interaction.response.defer()
    
    # Safe trimming structure to prevent character limit overloads
    gosterilecek_icerik = content[:3900] + ("\n... [Content Truncated Due to Character Limit]" if len(content) > 3900 else "")
    
    embed = discord.Embed(
        title=f"📋 {title}",
        description=f"```text\n{gosterilecek_icerik}\n```",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Requested By: {interaction.user.display_name}")
    
    await interaction.followup.send(embed=embed)

# ---------------------------------------------------------
# COMMAND 5: /botinfo (System Status Control)
# ---------------------------------------------------------
@bot.tree.command(name="botinfo", description="Reports the bot's instant latency and server statistics.")
async def botinfo_cmd(interaction: discord.Interaction):
    gecikme = round(bot.latency * 1000)
    
    embed = discord.Embed(title="🤖 Bot Instant Status Report", color=discord.Color.brand_green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Latency (Ping)", value=f"`{gecikme}ms`", inline=True)
    embed.add_field(name="Connected Server", value=f"`{len(bot.guilds)}` servers", inline=True)
    embed.add_field(name="Service Status", value="`Active / Smooth`", inline=False)
    
    if gecikme > 150:
        embed.color = discord.Color.orange()
    if gecicme > 500:
        embed.color = discord.Color.red()
        
    await interaction.response.send_message(embed=embed)

# ========================================================================
# 7. SERVER RUN TRIGGER
# ========================================================================
if __name__ == "__main__":
    if not TOKEN:
        logger.critical("Critical Error: DISCORD_TOKEN environment variable is not defined in the Railway panel!")
    else:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            logger.critical("Login Failed: The token entered in Railway Variables is invalid or has been reset by Discord!")
        except Exception as e:
            logger.critical(f"Unexpected system error while starting the bot: {e}")
