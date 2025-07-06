import discord
from discord.ui import View, Button
import asyncio
from datetime import datetime

class AdminApprovalView(View):
    def __init__(self, role_name, user_id, channel_id, VIP_ROLES, send_log):
        super().__init__(timeout=None)
        self.role_name = role_name
        self.user_id = user_id
        self.channel_id = channel_id
        self.VIP_ROLES = VIP_ROLES
        self.send_log = send_log

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        seller_role_name = "🛍️・「البائع」"
        seller_role = discord.utils.get(interaction.guild.roles, name=seller_role_name)
        if seller_role not in interaction.user.roles:
            await interaction.response.send_message("❌ هذا الزر مخصص فقط للأعضاء الحاصلين على رتبة البائع.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ الموافقة على البيع", style=discord.ButtonStyle.green, emoji="💰")
    async def approve(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        _, role_id = self.VIP_ROLES.get(self.role_name, (None, None))
        role = guild.get_role(role_id) if role_id else None

        if not member:
            await interaction.response.send_message("❌ لم يتم العثور على المستخدم داخل السيرفر (ربما خرج).", ephemeral=True)
            return

        if not role:
            await interaction.response.send_message("❌ لم يتم العثور على الرتبة. تأكد من أن ID الرتبة صحيح وموجود.", ephemeral=True)
            return

        await member.add_roles(role)

        embed = discord.Embed(
            title="🎉 تهانينا!",
            description=(
                f"👤 **العضو:** {member.mention}\n"
                f"🏅 **الرتبة:** {role.name}\n"
                "\n✅ تم إكمال عملية الشراء بنجاح.\n"
                "شكراً لدعمك! 💖"
            ),
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="تمت الموافقة بواسطة الإدارة")

        await interaction.channel.send(embed=embed)
        await self.send_log(guild, f"✅ تم بيع الرتبة {role.name} إلى {member.name}")
        await interaction.response.defer()
        await asyncio.sleep(5)
        channel = guild.get_channel(self.channel_id)
        if channel:
            await channel.delete()

    @discord.ui.button(label="❌ رفض الطلب", style=discord.ButtonStyle.red, emoji="🚫")
    async def reject(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)

        embed = discord.Embed(
            title="📋 تم رفض الطلب",
            description=(
                f"❌ تم رفض طلب شراء رتبة **{self.role_name}**.\n"
                "سيتم حذف القناة تلقائياً خلال 30 ثانية."
            ),
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        if member:
            embed.set_footer(text=f"العضو: {member.display_name}", icon_url=member.display_avatar.url)

        await interaction.channel.send(embed=embed)
        await self.send_log(guild, f"❌ تم رفض طلب {self.role_name} من المستخدم ID: {self.user_id}")
        await interaction.response.defer()
        await asyncio.sleep(30)
        channel = guild.get_channel(self.channel_id)
        if channel:
            await channel.delete()

    async def send_request_message(self, channel, member):
        color = discord.Color.gold() if "VIP" in self.role_name else discord.Color.blue()
        overwrite = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        await channel.set_permissions(member, overwrite=overwrite)

        embed = discord.Embed(
            title="📬 طلب جديد لشراء رتبة",
            description=(
                f"👤 **العضو:** {member.mention}\n"
                f"🔖 **الرتبة المطلوبة:** {self.role_name}\n\n"
                "يرجى من الإدارة استخدام الأزرار أدناه للموافقة أو الرفض."
            ),
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="تاريخ الطلب • ستُغلق القناة تلقائيًا بعد المعالجة")

        await channel.send(embed=embed, view=self)



