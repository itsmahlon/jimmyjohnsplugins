import discord
from discord.ext import commands

# ================== ROLE IDS ==================

AFFILIATE_MANAGER_ROLE = 1437485568287314022
AFFILIATE_REP_ROLE = 1437485568287314018

ROLE_ASSIGN_ROLES = {
    1437618361147068647,
    1437485568656281821,
    1437485568656281820,
    1437485568287314021,
}

LIST_VIEW_ROLES = {
    1437485568656281821,
    1437485568656281820,
}

LIST_MODIFY_ROLES = {
    1437618361147068647,
    1437485568656281821,
    1437485568656281820,
    1437485568287314021,
}

# ================== CHAT CONFIG ==================

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

REP_COLOR = 0xcc000a

# ================== DATA ==================

AFFILIATE_LIST = []
AFFILIATE_LIST_MESSAGE_ID = None
AFFILIATE_LIST_CHANNEL_ID = None

# ================== HELPERS ==================

def has_role(ctx, role_ids):
    return any(role.id in role_ids for role in ctx.author.roles)

def build_affiliate_embed():
    embed = discord.Embed(
        description="\n".join(f"*{x}*" for x in AFFILIATE_LIST) or "*No affiliates*",
        color=0xFF0000
    )
    embed.set_author(name="Partners")
    embed.set_footer(
        text="This list only includes the groups that requested partnership, other groups can be found in the thread below!"
    )
    return embed

# ================== COG ==================

class Affiliate(commands.Cog):
    """Affiliate management system"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="affiliate", invoke_without_command=True)
    async def affiliate(self, ctx):
        pass

    # ---------- ROLE ASSIGN ----------
    @affiliate.command(name="role")
    async def affiliate_role(self, ctx, member: discord.Member, role: discord.Role):
        if not has_role(ctx, ROLE_ASSIGN_ROLES):
            return await ctx.send("Missing permissions.", ephemeral=True)

        # Enforce [REP] in role name
        if "[REP]" not in role.name:
            return await ctx.send("Role must contain [REP].", ephemeral=True)

        await member.add_roles(role)
        await ctx.send(f"{member.mention} assigned {role.name}", ephemeral=True)

    # ---------- QUICK REP ----------
    @affiliate.command(name="rep")
    async def affiliate_rep(self, ctx, member: discord.Member):
        if not has_role(ctx, ROLE_ASSIGN_ROLES):
            return await ctx.send("Missing permissions.", ephemeral=True)

        role = ctx.guild.get_role(AFFILIATE_REP_ROLE)
        if role is None:
            return await ctx.send("Affiliate REP role not found.", ephemeral=True)

        await member.add_roles(role)
        await ctx.send(
            f"{member.mention} added as affiliate representative.",
            ephemeral=True
        )

    # ---------- ADD ROLE ----------
    @affiliate.command(name="addrole")
    async def affiliate_addrole(self, ctx, *, name: str):
        if not has_role(ctx, {AFFILIATE_MANAGER_ROLE}):
            return await ctx.send("Missing permissions.", ephemeral=True)

        # Append [REP] if not present
        if not name.endswith("[REP]"):
            name += " [REP]"

        role = await ctx.guild.create_role(name=name, color=REP_COLOR)
        await ctx.send(f"Role created: {role.name}", ephemeral=True)

    # ---------- CHAT ----------
    @affiliate.command(name="chat")
    async def affiliate_chat(self, ctx, channel_name: str, role: discord.Role):
        if not has_role(ctx, {AFFILIATE_MANAGER_ROLE}):
            return await ctx.send("Missing permissions.", ephemeral=True)

        if "[REP]" not in role.name:
            return await ctx.send("Role must contain [REP].", ephemeral=True)

        category = ctx.guild.get_channel(CHAT_CATEGORY_ID)
        if category is None:
            return await ctx.send("Category not found.", ephemeral=True)

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
            overwrites=overwrites
        )

        await ctx.send(f"Channel created: {channel.mention}", ephemeral=True)

    # ---------- LIST ----------
    @affiliate.group(name="list", invoke_without_command=True)
    async def affiliate_list(self, ctx, channel: discord.TextChannel):
        if not has_role(ctx, LIST_VIEW_ROLES):
            return await ctx.send("Missing permissions.", ephemeral=True)

        global AFFILIATE_LIST_MESSAGE_ID, AFFILIATE_LIST_CHANNEL_ID

        embed = build_affiliate_embed()

        # Edit existing message if it exists
        if AFFILIATE_LIST_MESSAGE_ID and AFFILIATE_LIST_CHANNEL_ID == channel.id:
            try:
                msg = await channel.fetch_message(AFFILIATE_LIST_MESSAGE_ID)
                await msg.edit(embed=embed)
                return await ctx.send("Affiliate list updated.", ephemeral=True)
            except discord.NotFound:
                AFFILIATE_LIST_MESSAGE_ID = None
                AFFILIATE_LIST_CHANNEL_ID = None

        # Send new message
        msg = await channel.send(embed=embed)
        AFFILIATE_LIST_MESSAGE_ID = msg.id
        AFFILIATE_LIST_CHANNEL_ID = channel.id

        await ctx.send("Affiliate list created.", ephemeral=True)

    @affiliate_list.command(name="add")
    async def affiliate_list_add(self, ctx, *, name: str):
        if not has_role(ctx, {AFFILIATE_MANAGER_ROLE}):
            return await ctx.send("Missing permissions.", ephemeral=True)

        if name not in AFFILIATE_LIST:
            AFFILIATE_LIST.append(name)

        await self._update_affiliate_message(ctx.guild)
        await ctx.send(f"Added **{name}**.", ephemeral=True)

    @affiliate_list.command(name="remove")
    async def affiliate_list_remove(self, ctx, *, name: str):
        if not has_role(ctx, LIST_MODIFY_ROLES):
            return await ctx.send("Missing permissions.", ephemeral=True)

        if name not in AFFILIATE_LIST:
            return await ctx.send("Affiliate not found.", ephemeral=True)

        AFFILIATE_LIST.remove(name)
        await self._update_affiliate_message(ctx.guild)
        await ctx.send(f"Removed **{name}**.", ephemeral=True)

    # ---------- INTERNAL HELPER ----------
    async def _update_affiliate_message(self, guild):
        global AFFILIATE_LIST_MESSAGE_ID, AFFILIATE_LIST_CHANNEL_ID

        if not AFFILIATE_LIST_MESSAGE_ID or not AFFILIATE_LIST_CHANNEL_ID:
            return

        channel = guild.get_channel(AFFILIATE_LIST_CHANNEL_ID)
        if not channel:
            return

        try:
            msg = await channel.fetch_message(AFFILIATE_LIST_MESSAGE_ID)
        except discord.NotFound:
            AFFILIATE_LIST_MESSAGE_ID = None
            AFFILIATE_LIST_CHANNEL_ID = None
            return

        await msg.edit(embed=build_affiliate_embed())

# ================== SETUP ==================

async def setup(bot):
    await bot.add_cog(Affiliate(bot))
