import json
import discord
from discord import app_commands
from pathlib import Path
from config import BOT_ACCESS_ROLE

DATA_FILE = Path(__file__).parent / "userdata.json"

_user_data = {}
_data_loaded = False


def load_userdata():
    global _user_data, _data_loaded
    
    if _data_loaded:
        return _user_data
    
    file_path = Path(DATA_FILE)
    
    if not file_path.exists():
        _user_data = {"auto_reactions": {}}
        save_userdata()
        _data_loaded = True
        return _user_data
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        _user_data = loaded
    except (json.JSONDecodeError, IOError) as e:
        print(f"[AutoReaction] Error loading data: {e}. Using defaults.")
        _user_data = {"auto_reactions": {}}
        save_userdata()
    
    _data_loaded = True
    return _user_data


def save_userdata():
    file_path = Path(DATA_FILE)
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(_user_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[AutoReaction] Error saving data: {e}")


def get_userdata():
    if not _data_loaded:
        load_userdata()
    return _user_data


def reload_userdata():
    global _data_loaded
    _data_loaded = False
    return load_userdata()


def update_userdata(data):
    global _user_data
    if not _data_loaded:
        load_userdata()
    _user_data = data
    save_userdata()


async def has_bot_access(interaction: discord.Interaction):
    try:
        has_access = any(role.id == BOT_ACCESS_ROLE for role in interaction.user.roles)
        return has_access
    except Exception as e:
        print(f"[AutoReaction] has_bot_access error: {e}")
        return False


async def handle_user_reactions(message):
    if not message.guild:
        return

    if message.reference is not None:
        return

    data = get_userdata()
    user_data = data.get("auto_reactions", {})

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
            emoji = emoji_data

        mentioned = any(user.id == int(user_id) for user in message.mentions)
        keyword_found = any(k.lower() in msg_words for k in data["keywords"])

        if mentioned or keyword_found:
            await message.add_reaction(emoji)
            await message.reply(data["message"])
            break


autoreact_group = app_commands.Group(
    name="autoreact",
    description="Auto reaction management"
)


@autoreact_group.command(name="add", description="Add auto reaction")
@app_commands.check(has_bot_access)
@app_commands.describe(
    user="User to react for",
    keywords="Keywords to trigger (comma separated)",
    emoji="Emoji to react with",
    message="Reply message"
)
async def add_autoreact(
    interaction: discord.Interaction,
    user: str,
    keywords: str,
    emoji: str,
    message: str
):
    data = get_userdata()
    
    try:
        user_id = int(user.strip("<@!>"))
    except ValueError:
        return await interaction.response.send_message(
            "Invalid user mention. Use format: <@user_id>",
            ephemeral=True
        )

    keyword_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]

    auto_reactions = data.get("auto_reactions", {})
    
    if str(user_id) in auto_reactions:
        return await interaction.response.send_message(
            "Auto reaction already exists for this user. Use /autoreact update to modify.",
            ephemeral=True
        )

    auto_reactions[str(user_id)] = {
        "keywords": keyword_list,
        "emoji": emoji,
        "message": message
    }
    
    data["auto_reactions"] = auto_reactions
    update_userdata(data)

    await interaction.response.send_message(
        f"Auto reaction added for <@{user_id}>",
        ephemeral=True
    )


@autoreact_group.command(name="update", description="Update auto reaction")
@app_commands.check(has_bot_access)
@app_commands.describe(
    user="User to update",
    keywords="Keywords to trigger (comma separated, leave empty to keep current)",
    emoji="Emoji to react with (leave empty to keep current)",
    message="Reply message (leave empty to keep current)"
)
async def update_autoreact(
    interaction: discord.Interaction,
    user: str,
    keywords: str = None,
    emoji: str = None,
    message: str = None
):
    data = get_userdata()
    
    try:
        user_id = str(int(user.strip("<@!>")))
    except ValueError:
        return await interaction.response.send_message(
            "Invalid user mention. Use format: <@user_id>",
            ephemeral=True
        )

    auto_reactions = data.get("auto_reactions", {})
    
    if user_id not in auto_reactions:
        return await interaction.response.send_message(
            "Auto reaction not found for this user. Use /autoreact add first.",
            ephemeral=True
        )

    existing = auto_reactions[user_id]

    if keywords:
        keyword_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        existing["keywords"] = keyword_list
    
    if emoji:
        existing["emoji"] = emoji
    
    if message:
        existing["message"] = message

    auto_reactions[user_id] = existing
    data["auto_reactions"] = auto_reactions
    update_userdata(data)

    await interaction.response.send_message(
        f"Auto reaction updated for <@{user_id}>",
        ephemeral=True
    )


@autoreact_group.command(name="remove", description="Remove auto reaction")
@app_commands.check(has_bot_access)
@app_commands.describe(user="User to remove auto reaction for")
async def remove_autoreact(interaction: discord.Interaction, user: str):
    data = get_userdata()
    
    try:
        user_id = str(int(user.strip("<@!>")))
    except ValueError:
        return await interaction.response.send_message(
            "Invalid user mention. Use format: <@user_id>",
            ephemeral=True
        )

    auto_reactions = data.get("auto_reactions", {})
    
    if user_id not in auto_reactions:
        return await interaction.response.send_message(
            "Auto reaction not found for this user.",
            ephemeral=True
        )

    del auto_reactions[user_id]
    data["auto_reactions"] = auto_reactions
    update_userdata(data)

    await interaction.response.send_message(
        f"Auto reaction removed for <@{user_id}>",
        ephemeral=True
    )


@autoreact_group.command(name="list", description="List all auto reactions")
@app_commands.check(has_bot_access)
async def list_autoreact(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # ✅ prevent timeout

    try:
        data = get_userdata()
        auto_reactions = data.get("auto_reactions", {})
        guild = interaction.guild

        if not auto_reactions:
            return await interaction.followup.send(
                "No auto reactions configured.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="Auto Reactions",
            color=discord.Color.blurple()
        )

        for user_id, config in auto_reactions.items():
            member = guild.get_member(int(user_id))  # ✅ fast (no API)

            if member:
                user_mention = member.display_name
            else:
                user_mention = f"<@{user_id}>"

            emoji_data = config["emoji"]

            if isinstance(emoji_data, str) and emoji_data.isdigit():
                emoji = guild.get_emoji(int(emoji_data))
                emoji_display = str(emoji) if emoji else emoji_data
            elif isinstance(emoji_data, int):
                emoji = guild.get_emoji(emoji_data)
                emoji_display = str(emoji) if emoji else str(emoji_data)
            else:
                emoji_display = emoji_data

            keywords = ", ".join(config["keywords"]) if config["keywords"] else "No keywords"

            embed.add_field(
                name=f"User: {user_mention}",
                value=f"Keywords: {keywords}\nEmoji: {emoji_display}\nMessage: {config['message']}",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        try:
            await interaction.followup.send(
                "An error occurred while loading auto reactions.",
                ephemeral=True
            )
        except Exception:
            pass

def setup(bot):
    load_userdata()
    return autoreact_group