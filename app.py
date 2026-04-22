import asyncio
import discord
from random import randint
from discord.ext import commands
from discord.ui import View, Button
from discord import app_commands
from media import handle_media
import storage
import autoReaction
import apiFetches

# VARIABLES
SNIPE_DATA = {}

from config import (
    GUILD_ID,
    WELCOME_CHANNEL_IDS,
    RULES_CHANNEL_ID,
    ROLES_CHANNEL_ID,
    GAME_CHANNEL_ID,
    CONFESSION_CHANNEL_ID,
    NO_BOT_USE_USER_ID,
    NO_BOT_USE_CHANNEL_ID,
    HICHAT,
    BOW,
    MINECAT,
    ALRIGHT,
    BOT_ACCESS_ROLE,
    BOT_TOKEN
)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# WORD GUESS GAME ID
CURRENT_WORD = None
CURRENT_CLUE = None
WORD_ACTIVE = False
HINT_INDEX = 0
LEADERBOARD = {}

# CONFESSIONS ID (loaded from storage)
CONFESSION_COUNT = 0
CONFESSIONS = {}  # {id: message_id} (loaded from storage)

async def has_bot_access(interaction: discord.Interaction):
    return any(role.id == BOT_ACCESS_ROLE for role in interaction.user.roles)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):

        embed = discord.Embed(
            title="⛧ ACCESS DENIED ⛧",
            description=(
                "╭───────────────╮\n"
                " You are not allowed to use this command.\n"
                "╰───────────────╯\n\n"
                "Contact an admin if you think this is a mistake."
            ),
            color=0x8B0000
        )

        embed.set_thumbnail(
            url="https://cdn-icons-png.flaticon.com/512/1828/1828843.png"
        )

        embed.set_footer(
            text="Venomshade Security System",
            icon_url=interaction.user.display_avatar.url
        )

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

# SETUP
@bot.event
async def on_ready():
    global CONFESSION_COUNT, CONFESSIONS
    
    print(f"Venomshade is online as {bot.user}")
    
    storage.init(bot)
    data = storage.get_state()
    
    CONFESSION_COUNT = data.get("confession_count", 0)
    CONFESSIONS = data.get("confessions", {})
    
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.add_command(word_group, guild=guild)
        bot.tree.add_command(confession_group, guild=guild)
        bot.tree.add_command(autoReaction.autoreact_group, guild=guild)
        bot.tree.add_command(apiFetches.fact_command, guild=guild)
        bot.tree.add_command(apiFetches.insult_command, guild=guild)
        bot.add_command(apiFetches.reply_command)
        bot.add_view(ConfessionView(0))
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)



async def handle_user_reactions(message):
    if not message.guild:
        return

    if message.reference is not None:
        return
        
    # Do not auto react/reply to bot users in exclude list
    if message.author.id in NO_BOT_USE_USER_ID or message.channel.id in NO_BOT_USE_CHANNEL_ID:
        return

    autoReaction.reload_userdata()
    user_data = autoReaction.get_userdata().get("auto_reactions", {})
    
    if not user_data:
        return

    msg_words = message.content.lower().split()

    for user_id, data in user_data.items():
        emoji_data = data["emoji"]

        if isinstance(emoji_data, str) and emoji_data.isdigit():
            emoji = message.guild.get_emoji(int(emoji_data))
            if not emoji:
                return
        elif isinstance(emoji_data, int):
            emoji = message.guild.get_emoji(emoji_data)
            if not emoji:
                return
        else:
            emoji = emoji_data  # unicode emoji

        mentioned = any(user.id == int(user_id) for user in message.mentions)
        keyword_found = any(k.lower() in msg_words for k in data["keywords"])

        if mentioned or keyword_found:
            await message.add_reaction(emoji)
            await message.reply(data["message"])
            break

# MESSAGE HANDLER
@bot.event
async def on_message(message):
    global WORD_ACTIVE, CURRENT_WORD, CURRENT_CLUE

    handled = await handle_media(bot, message)
    if handled:
        return

    if message.author == bot.user:
        return
        
    # Do not auto react/reply to bot users in exclude list
    if message.author.id in NO_BOT_USE_USER_ID or message.channel.id in NO_BOT_USE_CHANNEL_ID:
        return

    msg = message.content.strip().lower()

    if msg in ["hi", "hlo", "hy", "hello", "hey", "oi", "hai"]:
        await message.add_reaction(HICHAT)

    elif msg == "ok":
        await message.reply(f"Ok {ALRIGHT}")

    elif msg == "fact":
        fact = await apiFetches.fetch_random_fact()
        if fact:
            embed = discord.Embed(
                description=f"## DO YOU KNOW THAT\n> ### {fact}\n## Isn't that concerning???",
                color=discord.Color(randint(0, 0xFFFFFF)),
            )

            embed.set_footer(
                text="Venomshade Facts System",
                icon_url=message.author.display_avatar.url
            )
            await message.reply(embed=embed)
        return

    # WORD GAME LOGIC
    if message.channel.id == GAME_CHANNEL_ID and WORD_ACTIVE:
        guess = message.content.strip().lower()

        if guess == CURRENT_WORD:
            await message.add_reaction("✅")

            # give point
            LEADERBOARD[message.author.id] = LEADERBOARD.get(message.author.id, 0) + 1

            # leaderboard display
            sorted_lb = sorted(LEADERBOARD.items(), key=lambda x: x[1], reverse=True)

            lb_text = ""
            for user_id, points in sorted_lb[:10]:
                user = message.guild.get_member(user_id)
                if user:
                    lb_text += f"**{user.name}** — {points} pts\n"

            embed = discord.Embed(
                description=f"# 🏆 Correct Guess!\n\n{message.author.mention} guessed the word!\n\n**Leaderboard:**\n{lb_text}",
                color=discord.Color.green()
            )

            await message.reply(embed=embed)

            # reset round
            WORD_ACTIVE = False
            CURRENT_WORD = None
            CURRENT_CLUE = None

        else:
            await message.add_reaction("❌")

    await handle_user_reactions(message)
    await bot.process_commands(message)


# WELCOME VIEW
class WelcomeView(View):
    def __init__(self, member):
        super().__init__(timeout=None)

        self.add_item(Button(
            label=f"Identity: {member.name}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        ))

        self.add_item(Button(
            label=f"Joined: {member.created_at.strftime('%d %b %Y')}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        ))


# WELCOME MESSAGE
@bot.event
async def on_member_join(member):
    for channel_id in WELCOME_CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if not channel:
            continue

        embed = discord.Embed(
            description=f"# ⋆｡‧dᥱᥲdᥣy ᥒιgһtsһᥲdᥱ‧｡⋆\n\n{MINECAT} {member.mention} 𝖍𝖆𝖘 𝖊𝖓𝖙𝖊𝖗𝖊𝖉 𝖙𝖍𝖊 𝖗𝖊𝖆𝖑𝖒.\n\n𝕰𝖓𝖙𝖊𝖗 𝖜𝖎𝖙𝖍 𝖐𝖎𝖓𝖉𝖓𝖊𝖘𝖘, 𝖑𝖊𝖆𝖛𝖊 𝖜𝖎𝖙𝖍 𝖒𝖊𝖒𝖔𝖗𝖎𝖊𝖘 𝖜𝖔𝖗𝖙𝖍 𝖐𝖊𝖊𝖕𝖎𝖓𝖌",
            color=discord.Color.dark_purple()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Venomshade Welcomes You 🤍", icon_url=member.display_avatar.url)

        view = WelcomeView(member)
        msg = await channel.send(embed=embed, view=view)

        await msg.add_reaction(BOW)

    # Ping user in rules channel and auto delete after 5 minutes
    rules_channel = bot.get_channel(RULES_CHANNEL_ID)
    if rules_channel:
        rules_ping = await rules_channel.send(f"{member.mention} Please read the server rules above 👆")
        
        # Auto delete function
        async def delete_rules_ping():
            await asyncio.sleep(300)
            try:
                await rules_ping.delete()
            except:
                pass
        
        bot.loop.create_task(delete_rules_ping())

    # Ping user in roles channel and auto delete after 5 minutes
    roles_channel = bot.get_channel(ROLES_CHANNEL_ID)
    if roles_channel:
        roles_ping = await roles_channel.send(f"{member.mention} Please pick up your roles above 👆")
        
        # Auto delete function
        async def delete_roles_ping():
            await asyncio.sleep(300)
            try:
                await roles_ping.delete()
            except:
                pass
        
        bot.loop.create_task(delete_roles_ping())


# SLASH COMMAND
@bot.tree.command(
    name="testwelcome",
    description="Test welcome message",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.check(has_bot_access)
async def testwelcome(interaction: discord.Interaction):
    member = interaction.user

    for channel_id in WELCOME_CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if not channel:
            continue

        embed = discord.Embed(
            description=f"# ⋆｡‧dᥱᥲdᥣy ᥒιgһtsһᥲdᥱ‧｡⋆\n\n{MINECAT} {member.mention} 𝖍𝖆𝖘 𝖊𝖓𝖙𝖊𝖗𝖊𝖉 𝖙𝖍𝖊 𝖗𝖊𝖆𝖑𝖒.\n\n𝕰𝖓𝖙𝖊𝖗 𝖜𝖎𝖙𝖍 𝖐𝖎𝖓𝖉𝖓𝖊𝖘𝖘, 𝖑𝖊𝖆𝖛𝖊 𝖜𝖎𝖙𝖍 𝖒𝖊𝖒𝖔𝖗𝖎𝖊𝖘 𝖜𝖔𝖗𝖙𝖍 𝖐𝖊𝖊𝖕𝖎𝖓𝖌",
            color=discord.Color.dark_purple()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Venomshade Welcomes You 🤍", icon_url=member.display_avatar.url)

        view = WelcomeView(member)
        msg = await channel.send(embed=embed, view=view)

        await msg.add_reaction(BOW)

    # Ping user in rules channel and auto delete after 5 minutes
    rules_channel = bot.get_channel(RULES_CHANNEL_ID)
    if rules_channel:
        rules_ping = await rules_channel.send(f"{member.mention} Please read the server rules above 👆")
        
        # Auto delete function
        async def delete_rules_ping():
            await asyncio.sleep(300) # 5 minutes = 300 seconds
            try:
                await rules_ping.delete()
            except:
                pass # Ignore if message was already deleted
        
        bot.loop.create_task(delete_rules_ping())

    # Ping user in roles channel and auto delete after 5 minutes
    roles_channel = bot.get_channel(ROLES_CHANNEL_ID)
    if roles_channel:
        roles_ping = await roles_channel.send(f"{member.mention} Please pick up your roles above 👆")
        
        # Auto delete function
        async def delete_roles_ping():
            await asyncio.sleep(300) # 5 minutes = 300 seconds
            try:
                await roles_ping.delete()
            except:
                pass # Ignore if message was already deleted
        
        bot.loop.create_task(delete_roles_ping())

    await interaction.response.send_message("Welcome message sent", ephemeral=True)

# SNIPE MESSAGE DELETION
class SnipeView(View):
    def __init__(self, author, time):
        super().__init__(timeout=None)

        self.add_item(Button(
            label=f"User: {author.name}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        ))

        self.add_item(Button(
            label=f"Time: {time}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        ))


@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    channel_id = message.channel.id

    SNIPE_DATA[channel_id] = {
        "author": message.author,
        "content": message.content,
        "attachments": message.attachments,
        "created_at": message.created_at
    }

    # auto delete after 1 hour (3600 sec)
    async def clear_snipe():
        await asyncio.sleep(3600)

        # only delete if it's still the same message
        if channel_id in SNIPE_DATA and SNIPE_DATA[channel_id]["created_at"] == message.created_at:
            del SNIPE_DATA[channel_id]

    bot.loop.create_task(clear_snipe())

@app_commands.check(has_bot_access)
@bot.tree.command(
    name="snipe",
    description="Show last deleted message",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(user="Filter by user (optional)")
async def snipe(interaction: discord.Interaction, user: discord.Member = None):

    data = SNIPE_DATA.get(interaction.channel.id)

    if not data:
        return await interaction.response.send_message(
            "Nothing to snipe here.",
            ephemeral=True
        )

    author = data["author"]

    if user and author.id != user.id:
        return await interaction.response.send_message(
            "No deleted message from that user.",
            ephemeral=True
        )

    content = data["content"] or "*No text content*"
    time = data["created_at"].strftime("%d %b %Y • %H:%M")

    embed = discord.Embed(
        title="⛧ MESSAGE SNIPED ⛧",
        description=f"```{content}```",
        color=discord.Color.dark_magenta()
    )

    embed.set_thumbnail(url=author.display_avatar.url)

    embed.add_field(
        name="User",
        value=f"{author.mention}",
    )

    # attachment support
    if data["attachments"]:
        file = data["attachments"][0]

        if file.content_type and "image" in file.content_type:
            embed.set_image(url=file.url)
        else:
            embed.add_field(
                name="Attachment",
                value=f"[File]({file.url})",
                inline=False
            )

    embed.set_footer(
        text="Venomshade Snipe System",
        icon_url=interaction.user.display_avatar.url
    )

    view = SnipeView(author, time)
    await interaction.response.send_message(embed=embed, view=view)

# WORD GUESS GAME
word_group = app_commands.Group(name="word", description="Word game commands")

# End Button for winner command
class EndGameView(View):
    def __init__(self, winners, leaderboard_text):
        super().__init__(timeout=60)
        self.winners = winners
        self.leaderboard_text = leaderboard_text

    @discord.ui.button(label="END", style=discord.ButtonStyle.danger)
    async def end_game(self, interaction: discord.Interaction, button: Button):
        global LEADERBOARD, CURRENT_WORD, WORD_ACTIVE, CURRENT_CLUE

        mentions = " ".join([w.mention for w in self.winners])

        embed = discord.Embed(
            title="",
            description=(
                f"# 🏆 Game Ended\n\n# 👑 **Winners:** {mentions}\n\n"
                f"{self.leaderboard_text}"
            ),
            color=discord.Color.gold()
        )

        # reset everything
        LEADERBOARD.clear()
        CURRENT_WORD = None
        CURRENT_CLUE = None
        WORD_ACTIVE = False

        await interaction.response.edit_message(embed=embed, view=None)

@word_group.command(name="set", description="Set the word")
@app_commands.check(has_bot_access)
async def set_word(
    interaction: discord.Interaction,
    word: str,
    round_name: str = None
):
    global CURRENT_WORD, WORD_ACTIVE, HINT_INDEX
    HINT_INDEX = 0

    if interaction.channel.id != GAME_CHANNEL_ID:
        return await interaction.response.send_message(
            "Use this in the game channel only.",
            ephemeral=True
        )

    CURRENT_WORD = word.lower()
    WORD_ACTIVE = True

    # Decide title
    if round_name:
        title_line = f"# 🎯 Round {round_name}"
    else:
        title_line = "# 🎯 New Round Started"

    embed = discord.Embed(
        description=(
            f"{title_line}\n\n"
            f"**Game started. Start Guessing Now!!!**"
        ),
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)

@word_group.command(name="reset", description="Reset leaderboard")
@app_commands.check(has_bot_access)
async def reset_leaderboard(interaction: discord.Interaction):
    global LEADERBOARD

    LEADERBOARD.clear()

    await interaction.response.send_message(
        "♻️ Leaderboard has been reset.",
        ephemeral=True
    )

@word_group.command(name="leaderboard", description="Show leaderboard")
async def show_leaderboard(interaction: discord.Interaction):

    if not LEADERBOARD:
        return await interaction.response.send_message(
            "No scores yet.",
            ephemeral=True
        )

    sorted_lb = sorted(LEADERBOARD.items(), key=lambda x: x[1], reverse=True)

    lb_text = ""
    for user_id, points in sorted_lb[:10]:
        user = interaction.guild.get_member(user_id)
        if user:
            lb_text += f"**{user.name}** — {points} pts\n"

    embed = discord.Embed(
        description=(f"# 🏆 Leaderboard\n\n{lb_text}"),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)

@word_group.command(name="clear", description="Skip current word")
@app_commands.check(has_bot_access)
async def clear_word(interaction: discord.Interaction):
    global CURRENT_WORD, WORD_ACTIVE, CURRENT_CLUE

    if not WORD_ACTIVE or not CURRENT_WORD:
        return await interaction.response.send_message(
            "No active round.",
            ephemeral=True
        )

    answer = CURRENT_WORD

    CURRENT_WORD = None
    CURRENT_CLUE = None
    WORD_ACTIVE = False

    embed = discord.Embed(
        description=f"# ⏭️ Round Skipped\n\n**Nobody guessed it correct.**\n\n# 💡 Word was: ||{answer}||",
        color=discord.Color.red()
    )

    await interaction.response.send_message(embed=embed)

@word_group.command(name="clue", description="Give a clue")
@app_commands.check(has_bot_access)
async def word_clue(interaction: discord.Interaction, clue: str):

    global CURRENT_CLUE

    if interaction.channel.id != GAME_CHANNEL_ID:
        return await interaction.response.send_message(
            "Use this in the game channel only.",
            ephemeral=True
        )

    if not WORD_ACTIVE:
        return await interaction.response.send_message(
            "No active word set.",
            ephemeral=True
        )

    CURRENT_CLUE = clue

    embed = discord.Embed(
        description=f"# 🧩 Guessing Game\n\n💡 **Clue:** {clue}",
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed)

@word_group.command(name="hint", description="Show hint for the word")
async def word_hint(interaction: discord.Interaction):

    global CURRENT_WORD, HINT_INDEX

    if not CURRENT_WORD:
        return await interaction.response.send_message(
            "No active word.",
            ephemeral=True
        )

    display = ""
    revealed_count = 0

    for char in CURRENT_WORD:
        if char == " ":
            display += "  "
        elif revealed_count < HINT_INDEX:
            display += char + " "
            revealed_count += 1
        else:
            display += "_ "

    HINT_INDEX += 1  # reveal more next time

    embed = discord.Embed(
        title="💡 Hint",
        description=f"# `{display.strip()}`",
        color=discord.Color.orange()
    )

    await interaction.response.send_message(embed=embed)

@word_group.command(name="winner", description="Show winner and leaderboard")
async def word_winner(interaction: discord.Interaction):

    global LEADERBOARD, CURRENT_WORD, WORD_ACTIVE, CURRENT_CLUE

    # ❌ No players
    if not LEADERBOARD:
        CURRENT_WORD = None
        CURRENT_CLUE = None
        WORD_ACTIVE = False

        return await interaction.response.send_message(
            "# No winner. Game ended.",
        )

    sorted_lb = sorted(LEADERBOARD.items(), key=lambda x: x[1], reverse=True)

    # leaderboard text
    lb_text = ""
    users = []

    for user_id, points in sorted_lb:
        user = interaction.guild.get_member(user_id)
        if user:
            lb_text += f"**{user.name}** — {points} pts\n"
            users.append((user, points))

    top_score = sorted_lb[0][1]
    winners = [u for u, p in users if p == top_score]

    # 🔥 CASE 1: MULTIPLE WINNERS (TIE)
    if len(winners) > 1:
        mentions = " ".join([w.mention for w in winners])

        embed = discord.Embed(
            description=(
                f"# ⚖️ Tie Detected\n\nTop players: {mentions}\n\n"
                f"Click **END** to declare them winners.\n\n"
                f"**Leaderboard:**\n{lb_text}"
            ),
            color=discord.Color.orange()
        )

        view = EndGameView(winners, lb_text)
        return await interaction.response.send_message(embed=embed, view=view)

    # 🏆 CASE 2: SINGLE WINNER
    winner_user = winners[0]

    embed = discord.Embed(
        description=(
            f"# 🏆 Game Results\n\n# 👑 **Winner:** {winner_user.mention}\n\n"
            f"**🎉 Congratulations! Please open a ticket to claim your reward.\n\n**"
            f"**Leaderboard:**\n{lb_text}"
        ),
        color=discord.Color.gold()
    )

    # reset everything
    LEADERBOARD.clear()
    CURRENT_WORD = None
    CURRENT_CLUE = None
    WORD_ACTIVE = False

    await interaction.response.send_message(embed=embed)

# CONFESSIONS SECTION
class ConfessionView(View):
    def __init__(self, confession_id):
        super().__init__(timeout=None)
        self.confession_id = confession_id

    @discord.ui.button(label="Submit a Confession!", style=discord.ButtonStyle.primary, custom_id="confession_reply")
    async def submit_confession(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ConfessionModal())

    @discord.ui.button(label="Reply", style=discord.ButtonStyle.secondary, custom_id="confession_submit")
    async def reply_confession(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ReplyModal(self.confession_id))

class ConfessionModal(discord.ui.Modal, title="Submit Confession"):

    text = discord.ui.TextInput(
        label="Your Confession",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await send_confession(interaction, self.text.value, None)

class ReplyModal(discord.ui.Modal):

    def __init__(self, confession_id):
        super().__init__(title="Reply to Confession")
        self.confession_id = confession_id

    reply = discord.ui.TextInput(
        label="Your Reply",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        data = CONFESSIONS.get(self.confession_id)
        if not data:
            return await interaction.followup.send(
                "Confession not found.",
                ephemeral=True
            )

        channel = interaction.guild.get_channel(CONFESSION_CHANNEL_ID)
        msg = await channel.fetch_message(data)

        if msg.thread:
            thread = msg.thread
        else:
            thread = await msg.create_thread(
                name=f"Replies • Confession #{self.confession_id:04d}"
            )

        await thread.send(self.reply.value)

        await interaction.followup.send(
            "Reply posted!",
            ephemeral=True
        )

async def send_confession(interaction, text, attachment):

    global CONFESSION_COUNT, CONFESSIONS

    await interaction.response.defer(ephemeral=True)

    CONFESSION_COUNT += 1
    cid = CONFESSION_COUNT
    formatted_id = f"{cid:04d}"

    channel = interaction.guild.get_channel(CONFESSION_CHANNEL_ID)

    embed = discord.Embed(
        description=(
            "# Anonymous Confession\n"
            "ㅤㅤㅤㅤ──────୨ৎ──────\n\n"
            f"# > {text}\n\n"
            "ㅤㅤㅤㅤㅤㅤ˗ˏˋ ꒰ ✉︎ ꒱ ˎˊ˗"
        ),
        color=discord.Color(randint(0, 0xFFFFFF)),
    )

    embed.set_footer(
        text=f"Confession ID: {formatted_id} • {discord.utils.utcnow().strftime('%d %b %Y %H:%M')}"
    )

    if attachment:
        embed.set_image(url=attachment.url)

    view = ConfessionView(cid)

    msg = await channel.send(embed=embed, view=view)

    CONFESSIONS[cid] = msg.id

    storage.update_state("confession_count", CONFESSION_COUNT)
    storage.update_state("confessions", CONFESSIONS)

    await msg.add_reaction("❤️")
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

    await interaction.followup.send(
        "Confession sent anonymously.",
        ephemeral=True
    )

confession_group = app_commands.Group(
    name="confession",
    description="Confession system",
)

@confession_group.command(name="confess", description="Send a confession")
async def confess(
    interaction: discord.Interaction,
    text: str,
    image: discord.Attachment = None
):
    await send_confession(interaction, text, image)

@confession_group.command(name="delete", description="Delete confession")
@app_commands.check(has_bot_access)
async def delete_confession(interaction: discord.Interaction, confession_id: int):

    global CONFESSIONS

    msg_id = CONFESSIONS.get(confession_id)

    if not msg_id:
        return await interaction.response.send_message(
            "Invalid confession ID.",
            ephemeral=True
        )

    channel = interaction.guild.get_channel(CONFESSION_CHANNEL_ID)

    try:
        msg = await channel.fetch_message(msg_id)
        await msg.delete()

        del CONFESSIONS[confession_id]

        storage.update_state("confessions", CONFESSIONS)

        await interaction.response.send_message(
            f"Confession #{confession_id} deleted.",
            ephemeral=True
        )

    except:
        await interaction.response.send_message(
            "Failed to delete.",
            ephemeral=True
        )

bot.run(BOT_TOKEN)