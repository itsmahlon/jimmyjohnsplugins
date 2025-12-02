import json
import os
import discord
from discord.ext import commands

AFFILIATES_FILE = "affiliates.json"

# Config / constants (IDs from your spec)
CATEGORY_ID = 1437485569062994057
CHANNEL_PERMIT_ROLE_IDS = [
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
ADMIN_ROLE_IDS = {1437485568656281821, 1437485568656281820}
ADD_PERMISSION_ROLE_ID = 1437485568287314022
REP_BASE_ROLE_ID = 1437485568287314018  # role to also add on rep


def load_affiliates():
    if not os.path.exists(AFFILIATES_FILE):
        return []
    try:
        with open(AFFILIATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_affiliates(affiliates):
    with open(AFFILIATES_FILE, "w", encoding="utf-8") as f:
        json.dump(affiliates, f, indent=2, ensure_ascii=False)


def sanitize_channel_name(name: str) -> str:
    # simple sanitize: lowercase, spaces -> hyphens, remove invalid chars
    cleaned = name.strip().lower().replace(" ", "-")
    # keep letters, numbers, hyphen and underscore
    cleaned = "".join(c for c in cleaned if c.isalnum() or c in "-_")
    return cleaned[:90] or "affiliate"


class Affiliate(commands.Cog):
    """Manage affiliates: list, add, remove, and assign rep."""

    def __init__(self, bot):
        self.bot = bot
        self.affiliates = load_affiliates()

    # ---------- Helper permission checks ----------
    def has_any_admin_role(self, member: discord.Member) -> bool:
        return any(r.id in ADMIN_ROLE_IDS for r in member.roles)

    def has_add_permission_role(self, member: discord.Member) -> bool:
        return any(r.id == ADD_PERMISSION_ROLE_ID for r in member.roles)

    # ---------- Utility ----------
    def affiliate_role_name(self, affiliate_name: str) -> str:
        return f"{affiliate_name} [REP]"

    def find_affiliate_by_name_case_insensitive(self, name: str):
        lower = name.strip().lower()
        for a in self.affiliates:
            if a.strip().lower() == lower:
                return a
        return None

    # ---------- Commands ----------
    @commands.group(name="affiliate", invoke_without_command=True)
    async def affiliate(self, ctx):
        """Show affiliates as an embed."""
        embed = discord.Embed(
            title="Affiliates",
            description="\n".join(self.affiliates) if self.affiliates else "No affiliates.",
            color=discord.Color(int("cf0a2b".lstrip("#"), 16)),
        )
        await ctx.send(embed=embed)

    @affiliate.command(name="add")
    async def affiliate_add(self, ctx, *, name: str):
        """Add an affiliate: update list, create private text channel, create [REP] role.
        Requires role 1437485568287314022."""
        author: discord.Member = ctx.author
        guild: discord.Guild = ctx.guild

        if not self.has_add_permission_role(author):
            return await ctx.send("You do not have permission to add affiliates.")

        name = name.strip()
        if not name:
            return await ctx.send("Affiliate name cannot be empty.")

        if self.find_affiliate_by_name_case_insensitive(name):
            return await ctx.send("Affiliate already exists in the list.")

        # 1) Add to list and save
        self.affiliates.append(name)
        save_affiliates(self.affiliates)

        # 2) Create role: "affiliate_name [REP]" if not exists
        role_name = self.affiliate_role_name(name)
        existing_role = discord.utils.find(lambda r: r.name == role_name, guild.roles)
        if not existing_role:
            try:
                new_role = await guild.create_role(name=role_name, reason=f"Affiliate role for {name}")
            except discord.Forbidden:
                new_role = None
            except Exception:
                new_role = None
        else:
            new_role = existing_role

        # 3) Create text channel under category and set overwrites
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)
        overwrites = {}

        # Deny @everyone default send/read if category exists
        if category:
            # build overwrites to grant VIEW_CHANNEL and SEND_MESSAGES for listed roles
            for rid in CHANNEL_PERMIT_ROLE_IDS:
                role = guild.get_role(rid)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            # also ensure default denies
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            channel_name = sanitize_channel_name(name)
            try:
                await guild.create_text_channel(channel_name, category=category, overwrites=overwrites, reason=f"Affiliate channel for {name}")
            except discord.Forbidden:
                # cannot create channel
                pass
            except Exception:
                pass
        else:
            # Category not found: attempt to create channel at guild root with overwrites
            for rid in CHANNEL_PERMIT_ROLE_IDS:
                role = guild.get_role(rid)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            channel_name = sanitize_channel_name(name)
            try:
                await guild.create_text_channel(channel_name, overwrites=overwrites, reason=f"Affiliate channel for {name}")
            except Exception:
                pass

        await ctx.send(f"Affiliate **{name}** added.")

    @affiliate.command(name="remove")
    async def affiliate_remove(self, ctx, *, name: str):
        """Remove affiliate from list only. Requires admin role IDs."""
        author: discord.Member = ctx.author

        if not self.has_any_admin_role(author):
            return await ctx.send("Only users with the admin roles can remove affiliates.")

        target = self.find_affiliate_by_name_case_insensitive(name)
        if not target:
            return await ctx.send("Affiliate not found in the list.")

        self.affiliates = [a for a in self.affiliates if a.strip().lower() != target.strip().lower()]
        save_affiliates(self.affiliates)
        await ctx.send(f"Affiliate **{target}** removed from the list.")

    @affiliate.command(name="rep")
    async def affiliate_rep(self, ctx, member_identifier: str, *, role_identifier: str):
        """Add REP to a member.
        Usage: ?affiliate rep <member> <affiliate_role_name_or_mention_or_id>
        Requires role 1437485568287314022 to run."""
        author: discord.Member = ctx.author
        guild: discord.Guild = ctx.guild

        if not self.has_add_permission_role(author):
            return await ctx.send("You do not have permission to assign reps.")

        # Resolve member (ID, mention, name)
        member = None
        # try ID
        if member_identifier.isdigit():
            member = guild.get_member(int(member_identifier))
        # mention
        if not member and member_identifier.startswith("<@") and member_identifier.endswith(">"):
            try:
                mid = int(''.join(c for c in member_identifier if c.isdigit()))
                member = guild.get_member(mid)
            except Exception:
                member = None
        # name lookup
        if not member:
            member = discord.utils.find(lambda m: m.name == member_identifier or (m.display_name == member_identifier), guild.members)

        if not member:
            return await ctx.send("Member not found. Provide ID, mention, or exact name/display name.")

        # Resolve affiliate role from identifier (can be id, mention, or name)
        target_role = None
        if role_identifier.isdigit():
            target_role = guild.get_role(int(role_identifier))
        if not target_role and role_identifier.startswith("<@&") and role_identifier.endswith(">"):
            try:
                rid = int(''.join(c for c in role_identifier if c.isdigit()))
                target_role = guild.get_role(rid)
            except Exception:
                target_role = None
        if not target_role:
            # Try direct name match (case-insensitive)
            lowered = role_identifier.strip().lower()
            for r in guild.roles:
                if r.name.lower() == lowered:
                    target_role = r
                    break

        if not target_role:
            # Try matching affiliate naming convention: "AffiliateName [REP]"
            # If user passed affiliate base name e.g. "CookiesBlox [REP]" or "CookiesBlox"
            name_try = role_identifier.strip()
            # if they passed with [REP], try exact
            possible_names = [name_try, f"{name_try} [REP]"]
            for p in possible_names:
                for r in guild.roles:
                    if r.name.lower() == p.lower():
                        target_role = r
                        break
                if target_role:
                    break

        if not target_role:
            return await ctx.send("Affiliate role not found. Provide role id/mention/exact role name or affiliate name (the cog will try `affiliate_name [REP]`).")

        # Add the REP base role (1437485568287314018)
        rep_base_role = guild.get_role(REP_BASE_ROLE_ID)
        roles_to_add = []
        if rep_base_role and rep_base_role not in member.roles:
            roles_to_add.append(rep_base_role)
        if target_role and target_role not in member.roles:
            roles_to_add.append(target_role)

        if not roles_to_add:
            return await ctx.send("Member already has the REP roles.")

        try:
            await member.add_roles(*roles_to_add, reason=f"Assigned by {author} via affiliate rep command")
        except discord.Forbidden:
            return await ctx.send("Bot lacks permissions to assign roles.")
        except Exception:
            return await ctx.send("Failed to assign roles due to an error.")

        await ctx.send(f"Assigned roles to {member.mention}: {', '.join(r.name for r in roles_to_add)}")


async def setup(bot):
    await bot.add_cog(Affiliate(bot))
