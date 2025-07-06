import discord
from discord.ext import tasks
from discord import app_commands
from discord.ui import View, Button, Select
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from admin_approval_view import AdminApprovalView

# تحميل المتغيرات البيئية
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PAID_CATEGORY_ID = int(os.getenv("PAID_VIP_CATEGORY_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))

# إعداد صلاحيات الديسكورد
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

class VIPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.channel_creation_times = {}
        self.latest_shop_message = None

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot = VIPBot()

VIP_ROLES = {
    "💎「VIP Member」": (2, 1389481015751344221),
    "👑「Royal VIP」": (3.4, 1389512894856822854),
    "✨「Star VIP」": (4.8, 1389511929030250628),
    "🦅「Eagle VIP」": (7.2, 1389514183237697556),
    "🔱「Mythic VIP」": (10, 1389514017562824725)
}

async def send_log(guild, message):
    log_channel = discord.utils.get(guild.text_channels, name="logs")
    if log_channel:
        await log_channel.send(message)

class VIPSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_role = None
        self.select_menu = VIPSelect(self)
        self.add_item(self.select_menu)
        self.add_item(PurchaseButton(self))

class VIPSelect(Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=role, description=f"السعر: {VIP_ROLES[role][0]}M", value=role)
            for role in VIP_ROLES
        ]
        super().__init__(placeholder="اختر رتبة للشراء...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_role = self.values[0]
        await interaction.response.send_message(f"تم اختيار الرتبة: **{self.values[0]}**", ephemeral=True)

class PurchaseButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="✅ شراء الرتبة", style=discord.ButtonStyle.green)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.selected_role:
            await interaction.response.send_message("❌ الرجاء اختيار رتبة أولاً.", ephemeral=True)
            return
        view = ConfirmPurchaseView(self.parent_view.selected_role)
        await interaction.response.send_message(view=view, ephemeral=True)

class ConfirmPurchaseView(View):
    def __init__(self, role_name):
        super().__init__(timeout=None)
        self.role_name = role_name
        self.confirm = Button(label="🛒 تأكيد الشراء", style=discord.ButtonStyle.primary)
        self.confirm.callback = self.handle_confirmation
        self.add_item(self.confirm)

    async def handle_confirmation(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        category = guild.get_channel(PAID_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
        }
        channel = await guild.create_text_channel(name=f"طلب-{member.name}", category=category, overwrites=overwrites)
        bot.channel_creation_times[channel.id] = datetime.now(timezone.utc)
        view = AdminApprovalView(self.role_name, member.id, channel.id, VIP_ROLES, send_log)
        embed = discord.Embed(
            title="📩 طلب شراء جديد",
            description=f"🔔 المستخدم {member.mention} قام بطلب شراء الرتبة **{self.role_name}**\n\n📝 يرجى من الإدارة مراجعة الطلب واتخاذ الإجراء المناسب بالأسفل.",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="DisVIP Shop System", icon_url=guild.icon.url if guild.icon else None)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"📬 تم إرسال طلب الشراء بنجاح! يرجى الانتظار لحين موافقة الإدارة. يمكنك متابعة الحالة في: {channel.mention}",
            ephemeral=True
        )

@bot.tree.command(name="vipshop", description="عرض متجر الرتب المدفوعة")
async def vip_shop(interaction: discord.Interaction):
    desc = "\n".join([
        f"{emoji} **{name}**: `{price}M` كريدت"
        for name, (price, _) in VIP_ROLES.items()
        for emoji in [name.split("\u300c")[0]]
    ])
    embed = discord.Embed(
        title="🏆 قائمة الرتب المدفوعة",
        description=desc + "\n\nاختر رتبتك من القائمة أدناه ثم اضغط على زر الشراء لإكمال العملية.",
        color=discord.Color.blurple()
    )
    view = VIPSelectView()
    await interaction.response.send_message(embed=embed, view=view)

@tasks.loop(minutes=10)
async def auto_cleanup_channels():
    now = datetime.now(timezone.utc)
    for channel_id, created_at in list(bot.channel_creation_times.items()):
        if (now - created_at) > timedelta(hours=24):
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    await channel.send("⏳ تم تجاوز المهلة، سيتم حذف هذه القناة.")
                    await asyncio.sleep(5)
                    await channel.delete(reason="⏳ انتهت مهلة 24 ساعة دون تنفيذ.")
                except:
                    pass
            del bot.channel_creation_times[channel_id]

@bot.event
async def on_ready():
    print(f"✅ البوت يعمل الآن كـ {bot.user}")
    auto_cleanup_channels.start()

bot.run(TOKEN)


