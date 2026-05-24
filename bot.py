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
# 1. AYARLAR VE YAPILANDIRMA (Railway Uyumlu)
# ========================================================================
# Bot tokenini Railway Variables (Çevre Değişkenleri) üzerinden çeker.
TOKEN = os.getenv("DISCORD_TOKEN")

# Kanal ID'si yeni verdiğin ID olarak koda gömüldü. 
# Eğer Railway'e HEDEF_KANAL değişkeni eklersen oradan okur, eklemezsen bu sabit ID'yi kullanır.
HEDEF_KANAL_ENV = os.getenv("HEDEF_KANAL")
HEDEF_KANAL_ID = int(HEDEF_KANAL_ENV) if HEDEF_KANAL_ENV else 1411100865787596820

# ========================================================================
# 2. LOGLAMA SİSTEMİ (Gelişmiş Takip)
# ========================================================================
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

# Hataları ve logları dosyaya kaydetmek için handler
handler = logging.FileHandler(filename='discord_bot.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Aynı logları Railway konsolunda (Deploy Logs) anlık görebilmek için console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# ========================================================================
# 3. BOT SINIFI VE BAĞLANTI ALT YAPISI
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
        logger.info("Slash komutları senkronize ediliyor...")
        try:
            await self.tree.sync()
            logger.info("Komutlar başarıyla senkronize edildi.")
        except Exception as e:
            logger.error(f"Komut senkronizasyonu sırasında kritik hata: {e}")

    async def on_ready(self):
        logger.info(f"Bot Başarıyla Giriş Yaptı! Kullanıcı: {self.user} (ID: {self.user.id})")
        logger.info(f"Aktif Hedef Kanal ID: {HEDEF_KANAL_ID}")
        logger.info("-" * 40)
        
        activity = discord.Activity(type=discord.ActivityType.watching, name="Sunucuyu ve Komutları")
        await self.change_presence(status=discord.Status.online, activity=activity)

bot = ProDiscordBot()

# ========================================================================
# 4. YARDIMCI FONKSİYONLAR (Gelişmiş Arayüz Tasarımları)
# ========================================================================
def create_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """Sistem genelinde şık ve standart embed mesajları üretir."""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
    embed.set_footer(text="Sleeping Bot Altyapısı", icon_url=bot.user.display_avatar.url if bot.user and bot.user.display_avatar else None)
    return embed

# ========================================================================
# 5. KÜRESEL HATA YAKALAYICI (Global Error Handler)
# ========================================================================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Komutlar çalışırken oluşabilecek tüm çökmeleri engeller ve kullanıcıyı bilgilendirir."""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Lütfen yavaşla! Bu komutu tekrar kullanmak için {error.retry_after:.2f} saniye bekle.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Bu komutu kullanmak için gerekli yetkilere sahip değilsin.", ephemeral=True)
    else:
        logger.error(f"Komut tetiklenirken beklenmeyen hata oluştu: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Komut işlenirken beklenmeyen bir ağ hatası oluştu.", ephemeral=True)
            else:
                await interaction.followup.send("❌ İşlem sırasında bir hata meydana geldi.", ephemeral=True)
        except Exception:
            pass

# ========================================================================
# 6. TÜM AKTİF SLASH KOMUTLARI
# ========================================================================

# ---------------------------------------------------------
# KOMUT 1: /send (Mesaj Gönderme)
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
    # 3 saniye zaman aşımını engellemek için düşünme süresi başlatıyoruz
    await interaction.response.defer(ephemeral=True)
    
    # Cache (get_channel) ve API (fetch_channel) protokolünü bir arada kullanarak kanalı kesin olarak arıyoruz
    kanal = None
    try:
        kanal = bot.get_channel(HEDEF_KANAL_ID)
        if not kanal:
            kanal = await bot.fetch_channel(HEDEF_KANAL_ID)
    except Exception as e:
        logger.error(f"Kanal çekilirken hata oluştu: {e}")

    if not kanal:
        hata_embed = create_embed(
            title="❌ Kanal Bulunamadı", 
            description=f"Hedeflenen `{HEDEF_KANAL_ID}` ID'li kanal bulunamadı veya botun bu kanalı görme yetkisi yok.", 
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=hata_embed)
        return

    # Gönderen bilgisini biçimlendirme
    if gondereni_goster == "evet":
        gonderilecek_icerik = f"{mesaj}\n\n*👤 Gönderen: {interaction.user.mention}*"
    else:
        gonderilecek_icerik = mesaj

    try:
        await kanal.send(content=gonderilecek_icerik)
        basari_embed = create_embed("✅ Başarılı", f"Mesajınız başarıyla <#{HEDEF_KANAL_ID}> kanalına iletildi.", discord.Color.green())
        await interaction.followup.send(embed=basari_embed)
        logger.info(f"[SEND] {interaction.user} kullanıcısı hedef kanala mesaj gönderdi.")
    except discord.Forbidden:
        await interaction.followup.send("❌ Botun hedef kanala mesaj gönderme yetkisi (Mesaj Gönder izni) bulunmuyor!")
    except Exception as e:
        await interaction.followup.send(f"❌ Mesaj gönderilirken teknik bir hata oluştu: {e}")

# ---------------------------------------------------------
# KOMUT 2: /txt (Kişisel TXT Oluşturucu)
# ---------------------------------------------------------
@bot.tree.command(name="txt", description="Yazdığınız metni anında bir .txt belgesine çevirip size gönderir.")
@app_commands.describe(
    dosya_adi="Oluşturulacak dosyanın adı (Örn: notlarim)",
    icerik="Txt dosyasının içerisine yazılacak tam metin"
)
async def txt_cmd(interaction: discord.Interaction, dosya_adi: str, icerik: str):
    await interaction.response.defer(ephemeral=True)
    
    # Dosya ismi optimizasyonu
    dosya_adi = dosya_adi.replace(" ", "_")
    if not dosya_adi.endswith(".txt"):
        dosya_adi += ".txt"
        
    # Bellek üzerinden geçici sanal dosya oluşturma
    dosya_byte = io.BytesIO(icerik.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=dosya_adi)
    
    embed = create_embed(
        title="📄 Belgeniz Hazır",
        description=f"İstediğiniz **{dosya_adi}** dosyası başarıyla oluşturuldu ve aşağıya eklendi.",
        color=discord.Color.gold()
    )
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)

    try:
        await interaction.followup.send(embed=embed, file=discord_dosyasi)
        logger.info(f"[TXT] {interaction.user} kullanıcısı {dosya_adi} dosyasını başarıyla üretti.")
    except Exception as e:
        await interaction.followup.send(f"❌ Dosya iletilirken hata meydana geldi: {e}")
    finally:
        dosya_byte.close()

# ---------------------------------------------------------
# KOMUT 3: /sendtxt (Hedef Kanala TXT Gönderme)
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
    
    kanal = None
    try:
        kanal = bot.get_channel(HEDEF_KANAL_ID)
        if not kanal:
            kanal = await bot.fetch_channel(HEDEF_KANAL_ID)
    except Exception as e:
        logger.error(f"Sendtxt komutunda kanal bulunamadı: {e}")

    if not kanal:
        await interaction.followup.send("❌ Hedef kanal bulunamadı! Lütfen yetkileri ve kanal ID'sini kontrol edin.")
        return

    dosya_adi = dosya_adi.replace(" ", "_")
    if not dosya_adi.endswith(".txt"):
        dosya_adi += ".txt"

    kanal_embed = discord.Embed(
        title="📁 Yeni Bir Belge Yüklendi",
        color=discord.Color.dark_theme(),
        timestamp=discord.utils.utcnow()
    )
    
    if gondereni_goster == "evet":
        kanal_embed.add_field(name="Yükleyen Kullanıcı", value=interaction.user.mention, inline=False)
    
    kanal_embed.add_field(name="Dosya İsmi", value=f"`{dosya_adi}`", inline=False)
    kanal_embed.set_footer(text="Otomatik Dosya Gönderim Sistemi")

    dosya_byte = io.BytesIO(icerik.encode("utf-8"))
    discord_dosyasi = discord.File(fp=dosya_byte, filename=dosya_adi)

    try:
        await kanal.send(embed=kanal_embed, file=discord_dosyasi)
        await interaction.followup.send(f"✅ **{dosya_adi}** belgesi başarıyla <#{HEDEF_KANAL_ID}> kanalına yüklendi.")
        logger.info(f"[SENDTXT] {interaction.user} -> {dosya_adi} dosyasını kanala gönderdi.")
    except discord.Forbidden:
        await interaction.followup.send("❌ Botun bu kanala dosya eki veya embed mesaj gönderme izni kapalı!")
    except Exception as e:
        await interaction.followup.send(f"❌ İşlem yürütülürken hata: {e}")
    finally:
        dosya_byte.close()

# ---------------------------------------------------------
# KOMUT 4: /paste (Yazı Paneli Formatlayıcı)
# ---------------------------------------------------------
@bot.tree.command(name="paste", description="Uzun metinleri sohbeti kirletmeden temiz bir blok formatına dönüştürür.")
@app_commands.describe(baslik="Metnin başlığı", icerik="Blok içine alınacak uzun metin")
async def paste_cmd(interaction: discord.Interaction, baslik: str, icerik: str):
    await interaction.response.defer()
    
    # Karakter sınırını aşmamak için güvenli kırpma yapısı
    gosterilecek_icerik = icerik[:3900] + ("\n... [İçerik Sınırı Nedeniyle Devamı Kesildi]" if len(icerik) > 3900 else "")
    
    embed = discord.Embed(
        title=f"📋 {baslik}",
        description=f"```text\n{gosterilecek_icerik}\n```",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Talep Eden: {interaction.user.display_name}")
    
    await interaction.followup.send(embed=embed)

# ---------------------------------------------------------
# KOMUT 5: /botinfo (Sistem Durumu Kontrolü)
# ---------------------------------------------------------
@bot.tree.command(name="botinfo", description="Botun anlık gecikme süresini ve sunucu istatistiklerini raporlar.")
async def botinfo_cmd(interaction: discord.Interaction):
    gecikme = round(bot.latency * 1000)
    
    embed = discord.Embed(title="🤖 Bot Anlık Durum Raporu", color=discord.Color.brand_green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Gecikme (Ping)", value=f"`{gecikme}ms`", inline=True)
    embed.add_field(name="Bağlı Sunucu", value=f"`{len(bot.guilds)}` sunucu", inline=True)
    embed.add_field(name="Hizmet Durumu", value="`Aktif / Sorunsuz`", inline=False)
    
    if gecikme > 150:
        embed.color = discord.Color.orange()
    if gecikme > 500:
        embed.color = discord.Color.red()
        
    await interaction.response.send_message(embed=embed)

# ========================================================================
# 7. SUNUCU ÇALIŞTIRMA TETİKLEYİCİSİ
# ========================================================================
if __name__ == "__main__":
    if not TOKEN:
        logger.critical("Kritik Hata: DISCORD_TOKEN çevre değişkeni Railway panelinde tanımlı değil!")
    else:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            logger.critical("Giriş Başarısız: Railway Variables alanına girilen token geçersiz veya Discord tarafından sıfırlanmış!")
        except Exception as e:
            logger.critical(f"Bot başlatılırken beklenmedik sistem hatası: {e}")
