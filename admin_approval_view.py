import discord
from discord.ui import View, Button
import asyncio

class AdminApprovalView(View):
    def __init__(self, role_name, user_id, channel_id, vip_roles, send_log_func):
        super().__init__(timeout=None)
        self.role_name = role_name
        self.user_id = user_id
        self.channel_id = channel_id
        self.VIP_ROLES = vip_roles
        self.send_log = send_log_func

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ فقط من يملكون صلاحيات الإدارة يمكنهم تنفيذ ذلك.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ بيع الرتبة", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        _, role_id = self.VIP_ROLES.get(self.role_name, (None, None))
        role = guild.get_role(role_id) if role_id else None

        if not member:
            await interaction.response.send_message("❌ لم يتم العثور على المستخدم داخل السيرفر.", ephemeral=True)
            return

        if not role:
            await interaction.response.send_message("❌ لم يتم العثور على الرتبة المطلوبة.", ephemeral=True)
            return

        await member.add_roles(role)
        await interaction.channel.send(embed=discord.Embed(
            title="🎉 تم منح الرتبة",
            description=f"✅ تم منح **{role.name}** إلى {member.mention}. شكراً لدعمك!",
            color=discord.Color.green()
        ))
        await self.send_log(guild, f"✅ تم بيع الرتبة {role.name} إلى {member.name}")
        await interaction.response.defer()
        await asyncio.sleep(5)
        channel = guild.get_channel(self.channel_id)
        if channel:
            await channel.delete()

    @discord.ui.button(label="❌ رفض الطلب", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id)
        await interaction.channel.send(
            embed=discord.Embed(
                title="🚫 تم رفض الطلب",
                description=f"❌ تم رفض الطلب من قبل الإدارة لـ <@{self.user_id}>.\nسيتم حذف القناة خلال 30 ثانية.",
                color=discord.Color.red()
            )
        )
        await self.send_log(guild, f"❌ تم رفض طلب {self.role_name} من المستخدم ID: {self.user_id}")
        await interaction.response.defer()
        await asyncio.sleep(30)
        channel = guild.get_channel(self.channel_id)
        if channel:
            await channel.delete()
