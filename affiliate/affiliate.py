from discord.ext import commands
import discord

AFFILIATE_LIST_ROLES = [
    1437485568656281821,
    1437485568656281820
]

AFFILIATE_ADD_ROLE = 1437485568287314022
AFFILIATE_REP_BASE_ROLE = 1437485568287314018

AFFILIATE_CATEGORY = 1437485569062994057

CHANNEL_PERMISSIONS = [
    1437615286474899506,
    1437618361147068647,
    1437618654677303428,
    1437618635937153144,
    1437618634624340019,
    1437485568656281821,
    1437485568656281820,
    1437485568287314022,
    1437485568287314021,
    1437616556669665341
]


class AffiliateManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Stores Affiliate message info
        self.affiliate_msg_id = None
        self.affiliate_channel_id = None
        self.affiliates = []   # stored list only (no database needed)

    # ----------------------------------------
    # Utility
    # ----------------------------------------

    def has_any_role(self, user, role_ids):
        return any(r.id in role_ids for r in user.roles)

    async def update_affiliate_embed(self, channel):
        """Update the main affiliate embed."""
        desc = "\n".join(self.affiliates) if self.affiliates else "No affiliates added."

        embed = discord.Embed(
            title="Affiliates",
            description=desc,
            color=discord.Color.from_str("#cf0a2b")
        )

        msg = None
        if self.affiliate_msg_id:
            try:
                msg = await channel.fetch_message(self.affiliate_msg_id)
                await msg.edit(embed=embed)
                return
            except:
                pass

        msg = await channel.send(embed=embed)
        self.affiliate_msg_id = msg.id
        self.affiliate_channel_id = channel.id

    # ----------------------------------------
    # Main Affiliate Command
    # ----------------------------------------

    @commands.group(name="affiliate", invoke_without_command=True)
    async def affiliate(self, ctx):
        if not self.has_any_role(ctx.author, AFFILIATE_LIST_ROLES):
            return await ctx.reply("You do not have permission to run this command.")

        await self.update_affiliate_embed(ctx.channel)

    # ----------------------------------------
    # ADD AFFILIATE
    # ----------------------------------------

    @affiliate.command(name="add")
    async def affiliate_add(self, ctx, *, affiliate_name: str):
        if not ctx.author.get_role(AFFILIATE_ADD_ROLE):
            return await ctx.reply("You do not have permission to add affiliates.")

        if affiliate_name in self.affiliates:
            return await ctx.reply("This affiliate is already in the list.")

        # Add to internal list
        self.affiliates.append(affiliate_name)

        # Create REP role
        rep_role_name = f"{affiliate_name} [REP]"
        rep_role = await ctx.guild.create_role(name=rep_role_name)

        # Create private channel
        category = ctx.guild.get_channel(AFFILIATE_CATEGORY)

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }

        for role_id in CHANNEL_PERMISSIONS:
            role_obj = ctx.guild.get_role(role_id)
            if role_obj:
                overwrites[role_obj] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                )

        channel = await ctx.guild.create_text_channel(
            affiliate_name,
            category=category,
            overwrites=overwrites
        )

        # Update the embed
        await self.update_affiliate_embed(ctx.channel)

        await ctx.reply(f"Affiliate **{affiliate_name}** added successfully.")

    # ----------------------------------------
    # REMOVE AFFILIATE
    # ----------------------------------------

    @affiliate.command(name="remove")
    async def affiliate_remove(self, ctx, *, affiliate_name: str):
        if not self.has_any_role(ctx.author, AFFILIATE_LIST_ROLES):
            return await ctx.reply("You do not have permission to remove affiliates.")

        if affiliate_name not in self.affiliates:
            return await ctx.reply("This affiliate is not in the list.")

        self.affiliates.remove(affiliate_name)

        # Update embed only (channel/role not deleted)
        await self.update_affiliate_embed(ctx.channel)

        await ctx.reply(f"Affiliate **{affiliate_name}** removed from the list.")

    # ----------------------------------------
    # REPRESENTATIVE ASSIGNMENT
    # ----------------------------------------

    @affiliate.command(name="rep")
    async def affiliate_rep(self, ctx, member: discord.Member, *, role_input: str):
        # Validate role contains [REP]
        if "[REP]" not in role_input:
            return await ctx.reply("This is not a representative role, please try again.")

        # Find the role
        role = discord.utils.find(
            lambda r: role_input.lower() in r.name.lower(),
            ctx.guild.roles
        )
        if not role:
            return await ctx.reply("Representative role not found.")

        # Apply base rep role
        base_role = ctx.guild.get_role(AFFILIATE_REP_BASE_ROLE)
        if base_role:
            await member.add_roles(base_role)

        # Apply specific affiliate rep role
        await member.add_roles(role)

        await ctx.reply(f"{member.display_name} has been assigned to **{role.name}**.")


async def setup(bot):
    await bot.add_cog(AffiliateManager(bot))
