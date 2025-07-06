import discord
from discord.ext import tasks
from discord import app_commands
from discord.ui import View, Button, Select
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from admin_approval_view import AdminApprovalView
from flask import Flask, send_from_directory
import threading

# =======================
# إعداد Flask لصفحة keep‑alive
# =======================
app = Flask(__name__, static_folder='public')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

def run_flask():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_flask, daemon=True).start()

# =======================
# تحميل المتغيرات البيئية
# =======================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PAID_CATEGORY_ID = int(os.getenv("PAID_VIP_CATEGORY_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))

# =======================
# إعداد صلاحيات الديسكورد
# =======================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

class VIPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.channel_creation_times: dict[int, datetime] = {}

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot = VIPBot()

# =======================
# بيانات الرتب
# =======================
VIP_ROLES = {
    "💎「VIP Member」": (4, 1389481015751344221),
    "👑「Royal VIP」": (5.5, 1389512894856822854),
    "✨「Star VIP」": (7, 1389511929030250628),
    "🦅「Eagle VIP」": (10, 1389514183237697556),
    "🔱「Mythic VIP」": (16, 1389514017562824725)
}

async def send_log(guild: discord.Guild, message: str):
    log_channel = discord.utils.get(guild.text_channels, name="logs")
    if log_channel:
        await log_channel.send(message)

# =======================
# عناصر الواجهة التفاعلية
# =======================
class VIPSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_role: str | None = None
        self.add_item(VIPSelect(self))
        self.add_item(PurchaseButton(self))

class VIPSelect(Select):
    def __init__(self, parent_view: 'VIPSelectView'):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=role, description=f"السعر: {VIP_ROLES[role][0]}M", value=role)
            for role in VIP_ROLES
        ]
        super().__init__(placeholder="اختر رتبة للشراء...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_role = self.values[0]
        await interaction.response.send_message(f"✅ تم اختيار الرتبة: **{self.values[0]}**", ephemeral=True)

class PurchaseButton(Button):
    def __init__(self, parent_view: 'VIPSelectView'):
        super().__init__(label="🛒 متابعة الشراء", style=discord.ButtonStyle.green)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.selected_role:
            await interaction.response.send_message("❌ الرجاء اختيار رتبة أولاً.", ephemeral=True)
            return
        view = ConfirmPurchaseView(self.parent_view.selected_role)
        await interaction.response.send_message(view=view, ephemeral=True)

class ConfirmPurchaseView(View):
    def __init__(self, role_name: str):
        super().__init__(timeout=None)
        self.role_name = role_name
        confirm_btn = Button(label="✅ تأكيد الشراء", style=discord.ButtonStyle.primary, emoji="💳")
        confirm_btn.callback = self.handle_confirmation
        self.add_item(confirm_btn)

    async def handle_confirmation(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        # إنشاء قناة الطلب تحت التصنيف المدفوع
        category = guild.get_channel(PAID_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
        }
        channel = await guild.create_text_channel(name=f"طلب-{member.name}", category=category, overwrites=overwrites)
        bot.channel_creation_times[channel.id] = datetime.now(timezone.utc)

        # إنشاء View للموافقة/الرفض
        view = AdminApprovalView(self.role_name, member.id, channel.id, VIP_ROLES, send_log)

        # ===== Embed مُحسَّن وحديث =====
        price = VIP_ROLES[self.role_name][0]
        embed = discord.Embed(
            title="🛒 طلب شراء رتبة جديدة",
            description=(
                f"👤 **العضو:** {member.mention}\n"
                f"💎 **الرتبة المطلوبة:** {self.role_name}\n"
                f"💰 **السعر:** `{price}M` كريدت\n\n"
                "يرجى من الإدارة استخدام الأزرار أدناه للموافقة أو الرفض."
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="رقم الطلب • سيتم حذف القناة تلقائيًا بعد المعالجة")

        await channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"📨 تم إنشاء قناة خاصة لمتابعة طلبك: {channel.mention}",
            ephemeral=True
        )

# =======================
# أمر عرض المتجر
# =======================
@bot.tree.command(name="vipshop", description="عرض متجر الرتب المدفوعة")
async def vip_shop(interaction: discord.Interaction):
    desc_lines = []
    for name, (price, _) in VIP_ROLES.items():
        emoji = name.split("「")[0]
        desc_lines.append(f"{emoji} **{name}**: `{price}M` كريدت")
    embed = discord.Embed(
        title="🏆 قائمة الرتب المدفوعة",
        description="\n".join(desc_lines) + "\n\nاختر رتبتك من القائمة ثم اضغط على ‘متابعة الشراء’.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=VIPSelectView())

# =======================
# تنظيف القنوات منتهية الصلاحية
# =======================
@tasks.loop(minutes=10)
async def auto_cleanup_channels():
    now = datetime.now(timezone.utc)
    expired = [cid for cid, created in bot.channel_creation_times.items() if (now - created) > timedelta(hours=24)]
    for cid in expired:
        ch = bot.get_channel(cid)
        if ch:
            try:
                await ch.send("⏳ انتهت مهلة الطلب، سيتم حذف هذه القناة.")
                await asyncio.sleep(5)
                await ch.delete(reason="مهلة 24 ساعة")
            except Exception:
                pass
        bot.channel_creation_times.pop(cid, None)

# =======================
# جاهزية البوت
# =======================
@bot.event
async def on_ready():
    print(f"✅ البوت متصل كـ {bot.user}")
    auto_cleanup_channels.start()

# =======================
# تشغيل البوت
# =======================
if TOKEN:
    bot.run(TOKEN)
else:
    raise RuntimeError("DISCORD_TOKEN غير موجود في المتغيرات البيئية")


