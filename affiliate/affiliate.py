from discord.ext import commands
import discord

CATEGORY_ID = 1437485569062994057

MANAGER_ROLE_ID = 1437485568287314022

AFFILIATE_LIST_VIEW_ROLES = {
    1437485568656281821,
    1437485568656281820,
}

AFFILIATE_LIST_ADD_ROLE = 1437485568287314021

CHAT_ALLOWED_ROLES = [
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
]

affiliate_storage = []  # simple in-memory storage


def has_role(member, role_ids):
    return any(r.id in role_ids for r in member.roles)


def is_rep_role(role: discord.Role):
    return "[REP]" in role.name


class Affiliate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def affiliate(self, ctx):
        return  # does nothing

    # ---------------- ROLE ---------------- #

    @affiliate.command()
    async def role(self, ctx, member: discord.Member = None, role: discord.Role = None):
        if not has_role(ctx.author, {MANAGER_ROLE_ID}):
            return

        if not member:
            await ctx.send("No such user found, please check if you've typed correctly.")
            return

        if not role or not is_rep_role(role):
            await ctx.send("Please add a Representative Role")
            return

        await member.add_roles(role)
        await ctx.send(f"{member.mention} has been assigned {role.name}")

    # ---------------- CHAT ---------------- #

    @affiliate.command()
    async def chat(self, ctx, channel_name: str = None, role: discord.Role = None):
        if not has_role(ctx.author, {MANAGER_ROLE_ID}):
            return

        if not channel_name or not role or not is_rep_role(role):
            await ctx.send("Please add a Representative Role")
            return

        category = ctx.guild.get_channel(CATEGORY_ID)
        if not category:
            return

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }

        for role_id in CHAT_ALLOWED_ROLES:
            r = ctx.guild.get_role(role_id)
            if r:
                overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await ctx.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        await ctx.send(f"Affiliate channel created: {channel.mention}")

    # ---------------- ADD ROLE ---------------- #

    @affiliate.command()
    async def addrole(self, ctx, *, name: str):
        if not has_role(ctx.author, {MANAGER_ROLE_ID}):
            return

        role = await ctx.guild.create_role(name=name)
        await ctx.send(f"Role created: {role.name}")

    # ---------------- LIST ---------------- #

    @affiliate.command()
    async def list(self, ctx, channel: discord.TextChannel = None):
        if not has_role(ctx.author, AFFILIATE_LIST_VIEW_ROLES):
            return

        if not channel:
            return

        description = "\n".join(f"*{name}*" for name in affiliate_storage) or "*No affiliates*"

        embed = discord.Embed(
            description=description,
            color=0xff0000
        )
        embed.set_author(name="Partners")
        embed.set_footer(text="This list *only* includes the groups that request partnership to us")

        await channel.send(embed=embed)

    # ---------- LIST ADD ---------- #

    @list.command(name="add")
    async def list_add(self, ctx, *, name: str):
        if not has_role(ctx.author, {AFFILIATE_LIST_ADD_ROLE}):
            return

        affiliate_storage.append(name)
        await ctx.send(f"Affiliate **{name}** added.")

    # ---------- LIST REMOVE ---------- #

    @list.command(name="remove")
    async def list_remove(self, ctx, *, name: str):
        if not has_role(ctx.author, AFFILIATE_LIST_VIEW_ROLES):
            return

        try:
            affiliate_storage.remove(name)
            await ctx.send(f"Affiliate **{name}** removed.")
        except ValueError:
            await ctx.send("Affiliate not found.")


def setup(bot):
    bot.add_cog(Affiliate(bot))
