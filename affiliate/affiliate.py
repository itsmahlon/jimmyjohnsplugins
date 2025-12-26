import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel

AFFILIATE_MANAGER_ROLE = 1437485568287314022

LIST_VIEW_ROLES = {
    1437485568656281821,
    1437485568656281820,
}

LIST_ADD_ROLE = 1437485568287314021

CHAT_CATEGORY_ID = 1437485569062994057

CHAT_ALLOWED_ROLES = {
    1437615286474899506,
    1437618361147068647,
    1437618654677303428,
    1437618635937153144,
    1437618634624340019,
    1437485568656281821,
    1437485568656281820,
    1437485568287314022,
    1437485568287314021,
    1437616556669665341,
}

AFFILIATE_LIST = []


def has_role(ctx, role_ids):
    return any(r.id in role_ids for r in ctx.author.roles)


class Affiliate(commands.Cog):
    """Affiliate management system"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="affiliate", invoke_without_command=True)
    async def affiliate(self, ctx):
        return

    # ---------------- ROLE ----------------

    @affiliate.command(name="role")
    async def affiliate_role(self, ctx, member: discord.Member, role: discord.Role):
        if not has_role(ctx, {AFFILIATE_MANAGER_ROLE}):
            return await ctx.send("Missing permissions.")

        if "[REP]" not in role.name:
            return await ctx.send("Please add a Repersentative Role")

        await member.add_roles(role)
        await ctx.send(f"{member.mention} has been assigned {role.name}")

    # ---------------- CHAT ----------------

    @affiliate.command(name="chat")
    async def affiliate_chat(self, ctx, channel_name: str, role: discord.Role):
        if not has_role(ctx, {AFFILIATE_MANAGER_ROLE}):
            return await ctx.send("Missing permissions.")

        if "[REP]" not in role.name:
            return await ctx.send("Please add a Repersentative Role")

        category = ctx.guild.get_channel(CHAT_CATEGORY_ID)
        if not category:
            return await ctx.send("Category not found.")

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }

        for role_id in CHAT_ALLOWED_ROLES:
            r = ctx.guild.get_role(role_id)
            if r:
                overwrites[r] = discord.PermissionOverwrite(view_channel=True)

        overwrites[role] = discord.PermissionOverwrite(view_channel=True)

        channel = await ctx.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
        )

        await ctx.send(f"Channel created: {channel.mention}")

    # ---------------- ADD ROLE ----------------

    @affiliate.command(name="addrole")
    async def affiliate_addrole(self, ctx, *, name: str):
        if not has_role(ctx, {AFFILIATE_MANAGER_ROLE}):
            return await ctx.send("Missing permissions.")

        role = await ctx.guild.create_role(name=name)
        await ctx.send(f"Role created: {role.name}")

    # ---------------- LIST ----------------

    @affiliate.group(name="list", invoke_without_command=True)
    async def affiliate_list(self, ctx, channel: discord.TextChannel):
        if not has_role(ctx, LIST_VIEW_ROLES):
            return await ctx.send("Missing permissions.")

        embed = discord.Embed(
            description="\n".join(f"*{x}*" for x in AFFILIATE_LIST) or "*No affiliates*",
            color=0xFF0000,
        )
        embed.set_author(name="Partners")
        embed.set_footer(text="This list *only* includes the groups that request partnership to us")

        await channel.send(embed=embed)
        await ctx.send("Affiliate list sent.")

    @affiliate_list.command(name="add")
    async def affiliate_list_add(self, ctx, *, name: str):
        if not has_role(ctx, {LIST_ADD_ROLE}):
            return await ctx.send("Missing permissions.")

        if name not in AFFILIATE_LIST:
            AFFILIATE_LIST.append(name)

        await ctx.send(f"Added **{name}** to affiliate list.")

    @affiliate_list.command(name="remove")
    async def affiliate_list_remove(self, ctx, *, name: str):
        if not has_role(ctx, LIST_VIEW_ROLES):
            return await ctx.send("Missing permissions.")

        if name in AFFILIATE_LIST:
            AFFILIATE_LIST.remove(name)
            await ctx.send(f"Removed **{name}** from affiliate list.")
        else:
            await ctx.send("Affiliate not found.")


def setup(bot):
    bot.add_cog(Affiliate(bot))
