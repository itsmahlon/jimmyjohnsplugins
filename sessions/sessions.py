import discord
from discord.ext import commands
import aiohttp
from datetime import datetime
import pytz

class SessionScheduler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channels = {}

        # HARDCODED TRELLO CREDENTIALS
        self.trello_key = "YOUR_TRELLO_KEY"
        self.trello_token = "YOUR_TRELLO_TOKEN"
        self.list_id = "YOUR_TRELLO_LIST_ID"

        if not self.trello_key or not self.trello_token or not self.list_id:
            raise RuntimeError("Trello credentials are missing")

        self.http = aiohttp.ClientSession()
        self._board_id = None

    async def cog_unload(self):
        await self.http.close()

    # -------------------- ROBLOX --------------------

    async def get_roblox_user_id(self, username: str):
        url = "https://users.roblox.com/v1/usernames/users"
        payload = {
            "usernames": [username],
            "excludeBannedUsers": True
        }

        async with self.http.post(url, json=payload) as resp:
            if resp.status != 200:
                return None, None

            data = await resp.json()
            if not data["data"]:
                return None, None

            user = data["data"][0]
            return user["id"], user["name"]

    # -------------------- TRELLO --------------------

    async def get_board_id(self):
        if self._board_id:
            return self._board_id

        url = f"https://api.trello.com/1/lists/{self.list_id}"
        params = {"key": self.trello_key, "token": self.trello_token}

        async with self.http.get(url, params=params) as resp:
            if resp.status != 200:
                return None

            data = await resp.json()
            self._board_id = data["idBoard"]
            return self._board_id

    async def get_label_id(self, label_name: str):
        board_id = await self.get_board_id()
        if not board_id:
            return None

        url = f"https://api.trello.com/1/boards/{board_id}/labels"
        params = {"key": self.trello_key, "token": self.trello_token}

        async with self.http.get(url, params=params) as resp:
            if resp.status != 200:
                return None

            labels = await resp.json()
            for label in labels:
                if label["name"] == label_name:
                    return label["id"]

        return None

    async def create_trello_card(self, name, desc, label_name, due_iso):
        url = "https://api.trello.com/1/cards"
        params = {
            "key": self.trello_key,
            "token": self.trello_token,
            "idList": self.list_id,
            "name": name,
            "desc": desc,
            "due": due_iso
        }

        async with self.http.post(url, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                print("Trello error:", text)
                return None

            card = await resp.json()

        label_id = await self.get_label_id(label_name)
        if label_id:
            label_url = f"https://api.trello.com/1/cards/{card['id']}/idLabels"
            await self.http.post(
                label_url,
                params={
                    "key": self.trello_key,
                    "token": self.trello_token,
                    "value": label_id
                }
            )

        return card["id"]

    async def get_all_cards(self):
        url = f"https://api.trello.com/1/lists/{self.list_id}/cards"
        params = {"key": self.trello_key, "token": self.trello_token}

        async with self.http.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            return await resp.json()

    async def add_label_to_card(self, card_id, label_name):
        label_id = await self.get_label_id(label_name)
        if not label_id:
            return False

        url = f"https://api.trello.com/1/cards/{card_id}/idLabels"
        params = {
            "key": self.trello_key,
            "token": self.trello_token,
            "value": label_id
        }

        async with self.http.post(url, params=params) as resp:
            return resp.status == 200

    # -------------------- COMMANDS --------------------

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlogs(self, ctx, channel: discord.TextChannel):
        self.log_channels[ctx.guild.id] = channel.id
        await ctx.send(f"Log channel set to {channel.mention}")

    @commands.command()
    async def schedulesession(self, ctx, session_type: str):
        session_map = {
            "shift": "Shift",
            "training": "Training Session",
            "largeshift": "LARGE SHIFT"
        }

        if session_type.lower() not in session_map:
            await ctx.send("Invalid type: shift / training / largeshift")
            return

        cog = self

        class SessionModal(discord.ui.Modal, title="Schedule Session"):
            host = discord.ui.TextInput(label="Host Roblox Username")
            cohost = discord.ui.TextInput(label="Cohost Roblox Username", required=False)
            description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph)
            date = discord.ui.TextInput(label="Date (MM/DD/YYYY)")
            time = discord.ui.TextInput(label="Time (HH:MM AM/PM GMT)")

            async def on_submit(self, interaction: discord.Interaction):
                host_id, host_name = await cog.get_roblox_user_id(self.host.value)
                if not host_id:
                    await interaction.response.send_message("Invalid host username.", ephemeral=True)
                    return

                cohost_text = ""
                if self.cohost.value:
                    _, cohost_name = await cog.get_roblox_user_id(self.cohost.value)
                    if cohost_name:
                        cohost_text = f"\nCohost: {cohost_name}"

                try:
                    date_obj = datetime.strptime(self.date.value, "%m/%d/%Y")
                    time_obj = datetime.strptime(self.time.value.upper(), "%I:%M %p")
                    combined = datetime.combine(date_obj.date(), time_obj.time())
                    gmt = pytz.timezone("GMT").localize(combined)
                except ValueError:
                    await interaction.response.send_message("Invalid date or time format.", ephemeral=True)
                    return

                desc = (
                    f"Host: {host_name}"
                    f"{cohost_text}\n"
                    f"Description: {self.description.value}\n"
                    f"Date: {self.date.value}\n"
                    f"Time: {self.time.value} GMT"
                )

                card_id = await cog.create_trello_card(
                    session_map[session_type.lower()],
                    desc,
                    "Scheduled",
                    gmt.isoformat()
                )

                if not card_id:
                    await interaction.response.send_message("Failed to create Trello card.", ephemeral=True)
                    return

                await interaction.response.send_message("Session scheduled.", ephemeral=True)

        await ctx.send(
            "Click to schedule:",
            view=discord.ui.View().add_item(
                discord.ui.Button(
                    label="Schedule Session",
                    style=discord.ButtonStyle.primary,
                    custom_id="open_modal"
                )
            )
        )

        async def interaction_handler(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Not for you.", ephemeral=True)
                return
            await interaction.response.send_modal(SessionModal())

        self.bot.add_listener(interaction_handler, "on_interaction")

    @commands.command()
    async def cancelsession(self, ctx, *, session_name: str):
        cards = await self.get_all_cards()

        card = next(
            (c for c in cards if session_name.lower() in c["name"].lower()),
            None
        )

        if not card:
            await ctx.send("Session not found.")
            return

        if await self.add_label_to_card(card["id"], "Cancelled"):
            await ctx.send(f"Session '{card['name']}' cancelled.")
        else:
            await ctx.send("Failed to cancel session.")

async def setup(bot):
    await bot.add_cog(SessionScheduler(bot))
