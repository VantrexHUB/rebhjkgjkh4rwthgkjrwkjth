import discord
from discord.ext import commands
from discord import app_commands
import io
import os
import logging
import datetime
import asyncio
import requests  # Pastebin API istekleri için eklendi
from typing import Optional

# ========================================================================
# 1. SETTINGS AND CONFIGURATION (Railway Compatible)
# ========================================================================
# Fetches the bot token from Railway Environment Variables
TOKEN = os.getenv("DISCORD_TOKEN")
PASTEBIN_API_KEY = os.getenv("PASTEBIN_API_KEY", "SNxRUbS82pBG5qmSW6AeCkmG7nhJhFB1")
PASTEBIN_URL = "https://pastebin.com/api/api_post.php"

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
# 4. HELPER CLASSES AND FUNCTIONS (Interface Designs)
# ========================================================================
def create_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """Generates stylish and standard embed messages across the system."""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
    embed.set_footer(text="Sleeping Bot Infrastructure", icon_url=bot.user.display_avatar.url if bot.user and bot.user.display_avatar else None)
    return embed

class PasteLinkView(discord.ui.View):
    """Generates a stylish button directly linking to the proxy URL."""
    def __init__(self, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label="🌐 Engelsiz Linki Aç (Proxy)", url=url, style=discord.ButtonStyle.link))

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

# REUSABLE CHOICES TYPES
PING_CHOICES = [
    app_commands.Choice(name="Yes, mention @everyone", value="yes"),
    app_commands.Choice(name="No, do not mention", value="no")
]

EXPIRATION_CHOICES = [
    app_commands.Choice(name="10 Dakika (10M)", value="10M"),
    app_commands.Choice(name="1 Saat (1H)", value="1H"),
    app_commands.Choice(name="1 Gün (1D)", value="1D"),
    app_commands.Choice(name="1 Hafta (1W)", value="1W"),
    app_commands.Choice(name="1 Ay (1M)", value="1M"),
    app_commands.Choice(name="1 Yıl (1Y)", value="1Y"),
    app_commands.Choice(name="Asla (Never)", value="N")
]

# ---------------------------------------------------------
# COMMAND 1: /send (Dynamic Channel Message Sender)
# ---------------------------------------------------------
@bot.tree.command(name="send", description="Sends the desired text to the specified target channel.")
@app_commands.describe(
    channel="The target channel where the message will be sent",
    message="The text you want to send",
    picture="An optional image (.png, .jpg, .gif) to attach",
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
async def send_cmd(interaction: discord.Interaction, channel: discord.TextChannel, message: str, picture: Optional[discord.Attachment] = None, show_sender: str = "no", ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        hata_embed = create_embed(
            title="❌ Channel Not Found", 
            description="The specified channel could not be found or the bot does not have permission to view it.", 
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=hata_embed)
        return

    content_pieces = []
    if ping_everyone == "yes":
        content_pieces.append("@everyone")
        
    if show_sender == "yes":
        content_pieces.append(f"{message}\n\n*👤 Sender: {interaction.user.mention}*")
    else:
        content_pieces.append(message)

    gonderilecek_icerik = "\n".join(content_pieces)

    files_to_send = []
    if picture:
        files_to_send.append(await picture.to_file())

    try:
        if len(files_to_send) > 0:
            await channel.send(content=gonderilecek_icerik, files=files_to_send)
        else:
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
    message="An optional text message to accompany the file",
    picture="An optional image (.png, .jpg, .gif) to display",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(ping_everyone=PING_CHOICES)
async def txt_cmd(interaction: discord.Interaction, file_name: str, content: str, message: Optional[str] = None, picture: Optional[discord.Attachment] = None, ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    file_name = file_name.replace(" ", "_")
    if not file_name.endswith(".txt"):
        file_name += ".txt"
        
    dosya_byte = io.BytesIO(content.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=file_name)
    
    embed = create_embed(
        title="📄 Your Document is Ready",
        description=f"The requested **{file_name}** file has been successfully created and attached below.",
        color=discord.Color.gold()
    )
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)

    if message:
        embed.add_field(name="💬 Message", value=message, inline=False)
        
    if picture:
        embed.set_image(url=picture.url)

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
    message="An optional text message to accompany the file",
    picture="An optional image (.png, .jpg, .gif) to display",
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
async def sendtxt_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file_name: str, content: str, message: Optional[str] = None, picture: Optional[discord.Attachment] = None, show_sender: str = "no", ping_everyone: str = "no"):
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
    
    if message:
        kanal_embed.add_field(name="💬 Message", value=message, inline=False)
        
    if picture:
        kanal_embed.set_image(url=picture.url)
        
    kanal_embed.set_footer(text="Automatic File Delivery System")

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
    message="An optional text message to accompany the file",
    picture="An optional image (.png, .jpg, .gif) to display",
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
async def modifytxt_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file_name: str, content: str, message: Optional[str] = None, picture: Optional[discord.Attachment] = None, show_sender: str = "no", ping_everyone: str = "no"):
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
    
    if message:
        kanal_embed.add_field(name="💬 Message", value=message, inline=False)
        
    if picture:
        kanal_embed.set_image(url=picture.url)
        
    kanal_embed.set_footer(text="Side-by-Side File Delivery System")

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
    message="An optional text message to accompany the file",
    picture="An optional image (.png, .jpg, .gif) to display",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(ping_everyone=PING_CHOICES)
async def sendmytxt_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file: discord.Attachment, message: Optional[str] = None, picture: Optional[discord.Attachment] = None, ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        await interaction.followup.send("❌ Target channel not found!")
        return

    if not file.filename.lower().endswith('.txt'):
        await interaction.followup.send("❌ Invalid file format! Please upload a file with a `.txt` extension.")
        return

    try:
        file_bytes = await file.read()
        dosya_byte = io.BytesIO(file_bytes)
        discord_dosyasi = discord.File(fp=dosya_byte, filename=file.filename)
        
        kanal_embed = discord.Embed(
            title="📥 A Forwarded File Has Arrived",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        kanal_embed.add_field(name="Sender", value=interaction.user.mention, inline=True)
        kanal_embed.add_field(name="File Name", value=f"`{file.filename}`", inline=True)
        
        if message:
            kanal_embed.add_field(name="💬 Message", value=message, inline=False)
            
        if picture:
            kanal_embed.set_image(url=picture.url)
            
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
    picture="An optional image (.png, .jpg, .gif) to display",
    ping_everyone="Do you want to mention @everyone?"
)
@app_commands.choices(ping_everyone=PING_CHOICES)
async def sendmyfile_cmd(interaction: discord.Interaction, channel: discord.TextChannel, file: discord.Attachment, message: Optional[str] = None, picture: Optional[discord.Attachment] = None, ping_everyone: str = "no"):
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        await interaction.followup.send("❌ Target channel not found!")
        return

    try:
        file_bytes = await file.read()
        file_size_mb = round(file.size / (1024 * 1024), 2)
        
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
        
        if message:
            kanal_embed.add_field(name="💬 Message", value=message, inline=False)
            
        if picture:
            kanal_embed.set_image(url=picture.url)
            
        kanal_embed.set_footer(text="Universal File Forwarding Engine")

        mention_str = "@everyone" if ping_everyone == "yes" else None

        await channel.send(content=mention_str, embed=kanal_embed, file=discord_dosyasi)
        await interaction.followup.send(f"✅ Your file **{file.filename}** has been successfully forwarded to {channel.mention}.")
        logger.info(f"[SENDMYFILE] {interaction.user} forwarded file {file.filename} to channel {channel.id}.")
        dosya_byte.close()
        
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot lacks permissions to post embeds or files in the destination channel!")
    except discord.HTTPException as e:
        if e.code == 40005:
            await interaction.followup.send("❌ The file is too large! Discord limits bot file uploads (typically 25MB max).")
        else:
            await interaction.followup.send(f"❌ Network or API Error occurred: {e}")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to process and forward the file: {e}")

# ---------------------------------------------------------
# COMMAND 7: /paste (Text Panel Formatter with Pastebin API Support)
# ---------------------------------------------------------
@bot.tree.command(name="paste", description="Uzun metinleri Pastebin'e yükler ve Türkiye engelsiz (Proxy) linkini hedef kanala gönderir.")
@app_commands.describe(
    channel="Paste linkinin ve embed mesajının gönderileceği hedef kanal",
    content="Pastebin altyapısına yüklenecek olan kod veya metin (Zorunlu)",
    title="Doküman için isteğe bağlı başlık (Varsayılan: Untitled Paste)",
    expiration="İçeriğin ne kadar süre yayında kalacağını belirler (Varsayılan: Asla)",
    message="Dosya gönderilirken eklenecek isteğe bağlı ek mesaj",
    picture="Görsel olarak eklenecek isteğe bağlı ek resim (.png, .jpg, .gif)",
    ping_everyone="Mesaj gönderilirken @everyone etiketlensin mi?"
)
@app_commands.choices(
    expiration=EXPIRATION_CHOICES,
    ping_everyone=PING_CHOICES
)
async def paste_cmd(
    interaction: discord.Interaction, 
    channel: discord.TextChannel, 
    content: str, 
    title: Optional[str] = "Untitled Paste", 
    expiration: str = "N", 
    message: Optional[str] = None, 
    picture: Optional[discord.Attachment] = None, 
    ping_everyone: str = "no"
):
    # Kullanıcıya gizli (ephemeral) yükleme ekranı gösteriyoruz bot donmasın diye
    await interaction.response.defer(ephemeral=True)
    
    if not channel:
        await interaction.followup.send("❌ Target channel not found!")
        return

    # Pastebin API parametre yükü hazırlanıyor
    payload = {
        "api_dev_key": PASTEBIN_API_KEY,
        "api_option": "paste",
        "api_paste_code": content,
        "api_paste_name": title if title else "Untitled Paste",
        "api_paste_expire_date": expiration,
        "api_paste_private": "0"  # Public olarak yükle
    }

    try:
        # requests.post senkron bir kütüphane olduğu için discord döngüsünü tıkamasın diye thread içinde çalıştırıyoruz
        response = await asyncio.to_thread(requests.post, PASTEBIN_URL, data=payload, timeout=10)
        response_text = response.text

        if response.status_code == 200 and "pastebin.com" in response_text:
            original_url = response_text.strip()
            
            # SİHİRLİ DOKUNUŞ: Türkiye engeline takılmaması için proxy linkine çeviriyoruz
            proxy_url = original_url.replace("pastebin.com", "pastebinp.com")

            # Kanalda görünecek şık embed arayüzümüz
            kanal_embed = discord.Embed(
                title="🎉 Metin Başarıyla Paste Edildi!",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            kanal_embed.add_field(name="📋 Başlık", value=f"`{payload['api_paste_name']}`", inline=True)
            kanal_embed.add_field(name="⏱ Süre Kısıtı", value=f"`{expiration}`", inline=True)
            
            if message:
                kanal_embed.add_field(name="💬 Mesaj", value=message, inline=False)
                
            if picture:
                kanal_embed.set_image(url=picture.url)
                
            kanal_embed.set_footer(text=f"Talep Eden: {interaction.user.display_name}")

            # Şık UI Link Butonu ekleme adımı
            view = PasteLinkView(url=proxy_url)
            mention_str = "@everyone" if ping_everyone == "yes" else None

            # Hedef kanala iletimi yapıyoruz
            await channel.send(content=mention_str, embed=kanal_embed, view=view)
            
            # Komutu tetikleyen yöneticiye gizli özet bildirimi geçiyoruz
            await interaction.followup.send(f"✅ Paste başarıyla oluşturuldu ve {channel.mention} kanalına iletildi!\n🌐 **Sansürsüz Link:** {proxy_url}")
            logger.info(f"[PASTE] {interaction.user} successfully pasted code inside {channel.id}.")
        else:
            await interaction.followup.send(f"❌ *Pastebin API Hatası!*\n\nSunucu Yanıtı: `{response_text}`")
            logger.error(f"[PASTE Error] API responded with: {response_text}")
            
    except Exception as e:
        await interaction.followup.send("❌ *Bağlantı Hatası!*\n\nPastebin sunucularına şu anda erişilemiyor.")
        logger.error(f"[PASTE Critical] Connection error: {e}")

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
