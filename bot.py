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
# 1. AYARLAR VE YAPILANDIRMA
# ========================================================================
# Botun çalışması için gerekli temel ayarlar
TOKEN = "MTUwODE0MDU4NTQyMzMzOTU0MA.GcMJIK.fES6nLPoVg1mjz1YPYj-EDd0riK-mnT1agR4Ws"
HEDEF_KANAL_ID = 1411089853998698642

# ========================================================================
# 2. LOGLAMA SİSTEMİ (Profesyonel botlar için zorunludur)
# ========================================================================
# Hataları ve botun durumunu konsola daha okunaklı yazdırmak için
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord_bot.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# ========================================================================
# 3. BOT SINIFI (Gelişmiş Altyapı)
# ========================================================================
class ProDiscordBot(commands.Bot):
    def __init__(self):
        # Botun neleri görebileceğini (intents) ayarlıyoruz
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None # Kendi yardım komutumuzu veya slash komutlarımızı kullanacağız
        )

    async def setup_hook(self):
        # Bot başlarken slash komutlarını Discord'a senkronize eder
        logger.info("Slash komutları senkronize ediliyor...")
        try:
            await self.tree.sync()
            logger.info("Komutlar başarıyla senkronize edildi.")
        except Exception as e:
            logger.error(f"Komut senkronizasyonu sırasında hata: {e}")

    async def on_ready(self):
        logger.info(f"Bot Başarıyla Giriş Yaptı! Kullanıcı: {self.user} (ID: {self.user.id})")
        logger.info("-" * 30)
        
        # Botun oynuyor kısmını ayarlıyoruz
        activity = discord.Activity(type=discord.ActivityType.watching, name="Sunucuyu ve Komutları")
        await self.change_presence(status=discord.Status.online, activity=activity)

# Bot objesini oluşturuyoruz
bot = ProDiscordBot()

# ========================================================================
# 4. YARDIMCI FONKSİYONLAR (Embed Tasarımları)
# ========================================================================
def create_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """Hızlıca şık bir embed mesajı oluşturmak için yardımcı fonksiyon"""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
    embed.set_footer(text="Pro Bot Altyapısı")
    return embed

# ========================================================================
# 5. HATA YAKALAMA (Global Error Handler)
# ========================================================================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Slash komutlarında oluşan hataları yakalar ve bota çökme yaşatmaz."""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Lütfen yavaşla! Bu komutu tekrar kullanmak için {error.retry_after:.2f} saniye bekle.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Bu komutu kullanmak için gerekli yetkilere sahip değilsin.", ephemeral=True)
    else:
        logger.error(f"Beklenmeyen bir hata oluştu: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Komut işlenirken beklenmeyen bir hata oluştu.", ephemeral=True)

# ========================================================================
# 6. ANA KOMUTLAR (İstenilen 3 Komut + Ekstralar)
# ========================================================================

# ---------------------------------------------------------
# KOMUT 1: /send
# ---------------------------------------------------------
@bot.tree.command(name="send", description="Belirlediğiniz hedef kanala istediğiniz metni gönderir.")
@app_commands.describe(
    mesaj="Göndermek istediğiniz yazı",
    gondereni_goster="Mesajın altında adınızın görünmesini istiyor musunuz?"
)
@app_commands.choices(gondereni_goster=[
    app_commands.Choice(name="Evet, göster", value="evet"),
    app_commands.Choice(name="Hayır, gizli kalsın", value="hayir")
])
async def send_cmd(interaction: discord.Interaction, mesaj: str, gondereni_goster: str = "hayir"):
    await interaction.response.defer(ephemeral=True) # Botun düşünme süresini başlatır
    
    kanal = bot.get_channel(HEDEF_KANAL_ID)
    if not kanal:
        hata_embed = create_embed("❌ Hata", "Hedef kanal bulunamadı. Lütfen bot kodundaki `HEDEF_KANAL_ID` değerini kontrol edin.", discord.Color.red())
        await interaction.followup.send(embed=hata_embed)
        return

    # Gönderen bilgisi ekleme mantığı
    if gondereni_goster == "evet":
        gonderilecek_icerik = f"{mesaj}\n\n*👤 Gönderen: {interaction.user.mention}*"
    else:
        gonderilecek_icerik = mesaj

    try:
        await kanal.send(content=gonderilecek_icerik)
        basari_embed = create_embed("✅ Başarılı", f"Mesajınız başarıyla <#{HEDEF_KANAL_ID}> kanalına iletildi.", discord.Color.green())
        await interaction.followup.send(embed=basari_embed)
        logger.info(f"[SEND] {interaction.user} kullanıcısı bir mesaj gönderdi.")
    except discord.Forbidden:
        await interaction.followup.send("❌ Botun hedef kanala mesaj gönderme yetkisi yok!")
    except Exception as e:
        await interaction.followup.send(f"❌ Mesaj gönderilirken bir hata oluştu: {e}")

# ---------------------------------------------------------
# KOMUT 2: /txt
# ---------------------------------------------------------
@bot.tree.command(name="txt", description="Yazdığınız metni anında bir .txt belgesine çevirip size gönderir.")
@app_commands.describe(
    dosya_adi="Oluşturulacak dosyanın adı (Örn: notlarim)",
    icerik="Txt dosyasının içerisine yazılacak tam metin"
)
async def txt_cmd(interaction: discord.Interaction, dosya_adi: str, icerik: str):
    # Dosya adını güvenli hale getirme
    dosya_adi = dosya_adi.replace(" ", "_")
    if not dosya_adi.endswith(".txt"):
        dosya_adi += ".txt"
        
    # Bellek üzerinde dosya oluşturma (Sunucu diskini yormaz)
    dosya_byte = io.BytesIO(icerik.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=dosya_adi)
    
    embed = create_embed(
        title="📄 Belgeniz Hazır",
        description=f"İstediğiniz **{dosya_adi}** dosyası başarıyla oluşturuldu ve aşağıya eklendi.",
        color=discord.Color.gold()
    )
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)

    try:
        await interaction.response.send_message(embed=embed, file=discord_dosyasi)
        logger.info(f"[TXT] {interaction.user} kullanıcısı {dosya_adi} isimli bir dosya oluşturdu.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Dosya oluşturulurken hata meydana geldi: {e}", ephemeral=True)
    finally:
        dosya_byte.close() # Belleği temizle

# ---------------------------------------------------------
# KOMUT 3: /sendtxt
# ---------------------------------------------------------
@bot.tree.command(name="sendtxt", description="Metni .txt belgesi yapıp direkt olarak hedef kanala gönderir.")
@app_commands.describe(
    dosya_adi="Oluşturulacak dosyanın adı",
    icerik="Dosyanın içerisine yazılacak metin",
    gondereni_goster="Mesajın altında adınızın görünmesini istiyor musunuz?"
)
@app_commands.choices(gondereni_goster=[
    app_commands.Choice(name="Evet, göster", value="evet"),
    app_commands.Choice(name="Hayır, gizli kalsın", value="hayir")
])
async def sendtxt_cmd(interaction: discord.Interaction, dosya_adi: str, icerik: str, gondereni_goster: str = "hayir"):
    await interaction.response.defer(ephemeral=True)
    
    kanal = bot.get_channel(HEDEF_KANAL_ID)
    if not kanal:
        await interaction.followup.send("❌ Hedef kanal bulunamadı! Bot ayarlarını kontrol edin.")
        return

    dosya_adi = dosya_adi.replace(" ", "_")
    if not dosya_adi.endswith(".txt"):
        dosya_adi += ".txt"

    # Kanala gidecek olan embed mesajı
    kanal_embed = discord.Embed(
        title="📁 Yeni Bir Belge Yüklendi",
        color=discord.Color.dark_theme()
    )
    
    if gondereni_goster == "evet":
        kanal_embed.add_field(name="Yükleyen", value=interaction.user.mention, inline=False)
    
    kanal_embed.add_field(name="Dosya Adı", value=dosya_adi, inline=False)
    kanal_embed.set_footer(text="Otomatik Belge Sistemi", icon_url=bot.user.display_avatar.url)

    # Dosyayı oluştur ve gönder
    dosya_byte = io.BytesIO(icerik.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=dosya_adi)

    try:
        await kanal.send(embed=kanal_embed, file=discord_dosyasi)
        await interaction.followup.send(f"✅ **{dosya_adi}** başarıyla <#{HEDEF_KANAL_ID}> kanalına gönderildi.")
        logger.info(f"[SENDTXT] {interaction.user} -> {dosya_adi} dosyası kanala iletildi.")
    except discord.Forbidden:
        await interaction.followup.send("❌ Botun o kanala dosya veya embed gönderme yetkisi yok!")
    except Exception as e:
        await interaction.followup.send(f"❌ İşlem sırasında hata: {e}")
    finally:
        dosya_byte.close()

# ---------------------------------------------------------
# KOMUT 4: /paste (Belge Linki Otomasyonu)
# ---------------------------------------------------------
@bot.tree.command(name="paste", description="Uzun metinleri sohbeti kirletmeden bir paste/belge formatına dönüştürür.")
@app_commands.describe(baslik="Metnin başlığı", icerik="Linke dönüştürülecek uzun metin")
async def paste_cmd(interaction: discord.Interaction, baslik: str, icerik: str):
    """
    Discord üzerinden uzun kodları veya metinleri paste servislerine benzer şekilde
    okunabilir bir formatta sunar. Belge linki oluşturma API'leri eklenebilir.
    """
    # İçerik çok uzunsa Discord mesaj sınırını aşmamak için kırpıyoruz
    gosterilecek_icerik = icerik[:3900] + ("\n... [Devamı Kesildi]" if len(icerik) > 3900 else "")
    
    embed = discord.Embed(
        title=f"📋 {baslik}",
        description=f"```text\n{gosterilecek_icerik}\n```",
        color=discord.Color.dark_embed()
    )
    embed.set_footer(text=f"Talep eden: {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

# ---------------------------------------------------------
# KOMUT 5: /botinfo (Genel Durum Kontrolü)
# ---------------------------------------------------------
@bot.tree.command(name="botinfo", description="Botun anlık durumunu ve gecikmesini gösterir.")
async def botinfo_cmd(interaction: discord.Interaction):
    gecikme = round(bot.latency * 1000)
    
    embed = discord.Embed(title="🤖 Bot İstatistikleri", color=discord.Color.brand_green())
    embed.add_field(name="Gecikme (Ping)", value=f"{gecikme}ms", inline=True)
    embed.add_field(name="Sunucu Sayısı", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="Geliştirici", value="Pro Altyapı", inline=False)
    
    # Ping durumuna göre renk değiştirme
    if gecikme > 150:
        embed.color = discord.Color.orange()
    if gecikme > 500:
        embed.color = discord.Color.red()
        
    await interaction.response.send_message(embed=embed)

# ========================================================================
# 7. BOTU ÇALIŞTIRMA
# ========================================================================
if __name__ == "__main__":
    if TOKEN == "BURAYA_BOT_TOKENINI_YAZ":
        logger.critical("LÜTFEN BOT TOKENİNİ KODA EKLEYİN!")
    else:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            logger.critical("Geçersiz Token! Lütfen tokeni doğru girdiğinizden emin olun.")
        except Exception as e:
            logger.critical(f"Bot başlatılamadı: {e}")