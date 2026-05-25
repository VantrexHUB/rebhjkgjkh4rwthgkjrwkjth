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

# PING CHOICES REUSABLE TYPE
PING_CHOICES = [
    app_commands.Choice(name="Yes, mention @everyone", value="yes"),
    app_commands.Choice(name="No, do not mention", value="no")
]

# ---------------------------------------------------------
# COMMAND 1: /send (Dynamic Channel Message Sender)
# ---------------------------------------------------------
@bot.tree.command(name="send", description="Sends the desired text to the specified target channel.")
@app_commands.describe(
    channel="The target channel where the message will be sent",
    message="The text you want to send",
    show_sender="Do you want your name to appear at the bottom of the message?",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(
    show_sender=[
        app_commands.Choice(name="Yes, show", value="yes"),
        app_commands.Choice(name="No, keep hidden", value="no")
    ],
    ping_everyone=PING_CHOICES
)
async def send_cmd(interaction: discord.Interaction, channel: discord.TextChannel, message: str, show_sender: str = "no", ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        hata_embed = create_embed(
            title="❌ Channel Not Found", 
            description="The specified channel could not be found or the bot does not have permission to view it.", 
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=hata_embed)
        return

    # Process content
    content_pieces = []
    if ping_everyone == "yes":
        content_pieces.append("@everyone")
        
    if show_sender == "yes":
        content_pieces.append(f"{message}\n\n*👤 Sender: {interaction.user.mention}*")
    else:
        content_pieces.append(message)

    gonderilecek_icerik = "\n".join(content_pieces)

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
# COMMAND 2: /txt (Personal TXT Document Creator - PRESERVES LINES)
# ---------------------------------------------------------
@bot.tree.command(name="txt", description="Converts text into a .txt document and sends it to you. (Line breaks preserved)")
@app_commands.describe(
    file_name="The name of the file to be created (e.g., notes)",
    content="The full text to be written inside the txt file",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(ping_everyone=PING_CHOICES)
async def txt_cmd(interaction: discord.Interaction, file_name: str, content: str, ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    file_name = file_name.replace(" ", "_")
    if not file_name.endswith(".txt"):
        file_name += ".txt"
        
    # Content is written directly as received (line breaks preserved)
    dosya_byte = io.BytesIO(content.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=file_name)
    
    embed = create_embed(
        title="📄 Your Document is Ready",
        description=f"The requested **{file_name}** file has been successfully created and attached below.",
        color=discord.Color.gold()
    )
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)

    mention_str = "@everyone" if ping_everyone == "yes" else None

    try:
        await interaction.followup.send(content=mention_str, embed=embed, file=discord_dosyasi)
        logger.info(f"[TXT] User {interaction.user} successfully generated the file {file_name}.")
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred while delivering the file: {e}")
    finally:
        dosya_byte.close()

# ---------------------------------------------------------
# COMMAND 3: /sendtxt (Dynamic Channel TXT Sender - PRESERVES LINES)
# ---------------------------------------------------------
@bot.tree.command(name="sendtxt", description="Converts text into a .txt document and sends it to the target channel. (Lines preserved)")
@app_commands.describe(
    channel="The target channel where the file will be sent",
    file_name="The name of the file to be created",
    content="The text to be written inside the file",
    show_sender="Do you want your name to appear at the bottom of the message?",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(
    show_sender=[
        app_commands.Choice(name="Yes, show", value="yes"),
        app_commands.Choice(name="No, keep hidden", value="no")
    ],
    ping_everyone=PING_CHOICES
)
async def sendtxt_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file_name: str, content: str, show_sender: str = "no", ping_everyone: str = "no"):
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

    # Content is written directly as received (line breaks preserved)
    dosya_byte = io.BytesIO(content.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=file_name)

    mention_str = "@everyone" if ping_everyone == "yes" else None

    try:
        await channel.send(content=mention_str, embed=kanal_embed, file=discord_dosyasi)
        await interaction.followup.send(f"✅ The document **{file_name}** has been successfully uploaded to {channel.mention}.")
        logger.info(f"[SENDTXT] {interaction.user} -> sent the file {file_name} to channel {channel.id}.")
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot's permission to send file attachments or embed messages to this channel is disabled!")
    except Exception as e:
        await interaction.followup.send(f"❌ Error during execution: {e}")
    finally:
        dosya_byte.close()

# ---------------------------------------------------------
# COMMAND 4: /modifytxt (Dynamic Channel TXT Sender - FLATTENS LINES TO SINGLE LINE)
# ---------------------------------------------------------
@bot.tree.command(name="modifytxt", description="Flattens all lines side by side in a .txt file and sends it to the channel.")
@app_commands.describe(
    channel="The target channel where the file will be sent",
    file_name="The name of the file to be created",
    content="The text to be written side by side inside the file",
    show_sender="Do you want your name to appear at the bottom of the message?",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(
    show_sender=[
        app_commands.Choice(name="Yes, show", value="yes"),
        app_commands.Choice(name="No, keep hidden", value="no")
    ],
    ping_everyone=PING_CHOICES
)
async def modifytxt_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file_name: str, content: str, show_sender: str = "no", ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        await interaction.followup.send("❌ Target channel not found!")
        return

    file_name = file_name.replace(" ", "_")
    if not file_name.endswith(".txt"):
        file_name += ".txt"

    kanal_embed = discord.Embed(
        title="📁 A Modified Document Has Been Uploaded",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    
    if show_sender == "yes":
        kanal_embed.add_field(name="Sender", value=interaction.user.mention, inline=False)
    
    kanal_embed.add_field(name="File Name", value=f"`{file_name}`", inline=False)
    kanal_embed.set_footer(text="Side-by-Side File Delivery System")

    # Modifying content to be side by side (replacing newlines with spaces and cleaning up extra spaces)
    lines = content.splitlines()
    flattened_content = " ".join([line.strip() for line in lines if line.strip()])

    dosya_byte = io.BytesIO(flattened_content.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=file_name)

    mention_str = "@everyone" if ping_everyone == "yes" else None

    try:
        await channel.send(content=mention_str, embed=kanal_embed, file=discord_dosyasi)
        await interaction.followup.send(f"✅ The flattened document **{file_name}** has been uploaded to {channel.mention}.")
        logger.info(f"[MODIFYTXT] {interaction.user} -> sent side-by-side file {file_name} to channel {channel.id}.")
    except discord.Forbidden:
        await interaction.followup.send("❌ Permission denied to send attachments or embeds in this channel!")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")
    finally:
        dosya_byte.close()

# ---------------------------------------------------------
# COMMAND 5: /sendmytxt (Upload and Forward local TXT File to Channel)
# ---------------------------------------------------------
@bot.tree.command(name="sendmytxt", description="Uploads an existing .txt file and forwards it directly to the target channel.")
@app_commands.describe(
    channel="The target channel where the uploaded file will be sent",
    file="The .txt file you want to upload from your device",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(ping_everyone=PING_CHOICES)
async def sendmytxt_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file: discord.Attachment, ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        await interaction.followup.send("❌ Target channel not found!")
        return

    # Check if the uploaded file is a valid TXT file
    if not file.filename.lower().endswith('.txt'):
        await interaction.followup.send("❌ Invalid file format! Please upload a file with a `.txt` extension.")
        return

    try:
        # Read file content from Discord attachment proxy safely into bytes memory
        file_bytes = await file.read()
        
        # Recreate a fresh Discord file instance from memory to send to another channel
        dosya_byte = io.BytesIO(file_bytes)
        discord_dosyasi = discord.File(fp=dosya_byte, filename=file.filename)
        
        kanal_embed = discord.Embed(
            title="📥 A Forwarded File Has Arrived",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        kanal_embed.add_field(name="Sender", value=interaction.user.mention, inline=True)
        kanal_embed.add_field(name="File Name", value=f"`{file.filename}`", inline=True)
        kanal_embed.set_footer(text="Direct File Forwarding Engine")

        mention_str = "@everyone" if ping_everyone == "yes" else None

        await channel.send(content=mention_str, embed=kanal_embed, file=discord_dosyasi)
        await interaction.followup.send(f"✅ Your file **{file.filename}** has been successfully forwarded to {channel.mention}.")
        logger.info(f"[SENDMYTXT] {interaction.user} forwarded file {file.filename} to channel {channel.id}.")
        dosya_byte.close()
        
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot lacks permissions to post embeds or files in the destination channel!")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to process and forward the file: {e}")

# ---------------------------------------------------------
# COMMAND 6: /sendmyfile (Upload and Forward ANY File to Channel)
# ---------------------------------------------------------
@bot.tree.command(name="sendmyfile", description="Uploads any file (e.g., .zip, .exe, .png) and forwards it to the target channel.")
@app_commands.describe(
    channel="The target channel where the uploaded file will be sent",
    file="The file you want to upload from your device",
    message="An optional text message to accompany the file",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(ping_everyone=PING_CHOICES)
async def sendmyfile_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file: discord.Attachment, message: Optional[str] = None, ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        await interaction.followup.send("❌ Target channel not found!")
        return

    try:
        # Read file content safely into memory
        file_bytes = await file.read()
        
        # Calculate file size in MB for the embed
        file_size_mb = round(file.size / (1024 * 1024), 2)
        
        # Recreate a fresh Discord file instance
        dosya_byte = io.BytesIO(file_bytes)
        discord_dosyasi = discord.File(fp=dosya_byte, filename=file.filename)
        
        kanal_embed = discord.Embed(
            title="📦 A New File Has Arrived",
            color=discord.Color.teal(),
            timestamp=discord.utils.utcnow()
        )
        kanal_embed.add_field(name="👤 Sender", value=interaction.user.mention, inline=True)
        kanal_embed.add_field(name="📄 File Name", value=f"`{file.filename}`", inline=True)
        kanal_embed.add_field(name="💾 Size", value=f"`{file_size_mb} MB`", inline=True)
        
        # If the user provided an optional message, append it as a clean field
        if message:
            kanal_embed.add_field(name="💬 Message", value=message, inline=False)
            
        kanal_embed.set_footer(text="Universal File Forwarding Engine")

        mention_str = "@everyone" if ping_everyone == "yes" else None

        await channel.send(content=mention_str, embed=kanal_embed, file=discord_dosyasi)
        await interaction.followup.send(f"✅ Your file **{file.filename}** has been successfully forwarded to {channel.mention}.")
        logger.info(f"[SENDMYFILE] {interaction.user} forwarded file {file.filename} to channel {channel.id}.")
        dosya_byte.close()
        
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot lacks permissions to post embeds or files in the destination channel!")
    except discord.HTTPException as e:
        # Code 40005 means "Request entity too large" (usually hits the 25MB standard bot limit)
        if e.code == 40005:
            await interaction.followup.send("❌ The file is too large! Discord limits bot file uploads (typically 25MB max).")
        else:
            await interaction.followup.send(f"❌ Network or API Error occurred: {e}")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to process and forward the file: {e}")

# ---------------------------------------------------------
# COMMAND 7: /paste (Text Panel Formatter)
# ---------------------------------------------------------
@bot.tree.command(name="paste", description="Converts long texts into a clean block format without cluttering the chat.")
@app_commands.describe(
    title="The title of the text", 
    content="The long text to be wrapped in a block",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(ping_everyone=PING_CHOICES)
async def paste_cmd(interaction: discord.Interaction, title: str, content: str, ping_everyone: str = "no"):
    await interaction.response.defer()
    
    gosterilecek_icerik = content[:3900] + ("\n... [Content Truncated Due to Character Limit]" if len(content) > 3900 else "")
    
    embed = discord.Embed(
        title=f"📋 {title}",
        description=f"```text\n{gosterilecek_icerik}\n```",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Requested By: {interaction.user.display_name}")
    
    mention_str = "@everyone" if ping_everyone == "yes" else None
    
    await interaction.followup.send(content=mention_str, embed=embed)

# ---------------------------------------------------------
# COMMAND 8: /botinfo (System Status Control)
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
    if gecikme > 500:
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
