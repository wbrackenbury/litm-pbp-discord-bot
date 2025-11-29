import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from database import Database, Tag

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True  # Required for prefix commands

bot = commands.Bot(command_prefix="!", intents=intents)
db = Database("bot_data.db")


@bot.event
async def on_ready():
    """Called when bot connects to Discord."""
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Connected to {len(bot.guilds)} guild(s)")

    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# --- Helper Functions ---

def format_tag(tag: Tag) -> str:
    """Format a tag for display on a single line (without NPC, shown in subheading)."""
    parts = [f"**{tag.name}**"]
    if tag.level is not None:
        parts.append(f"[Level: {tag.level}]")
    parts.append(f"(ID: {tag.id})")
    return " ".join(parts)


def format_tags_by_scene(tags: list[Tag], channel_name: str) -> str:
    """Format tags grouped by scene, then by NPC."""
    from collections import defaultdict

    # Group by scene, then by NPC
    by_scene = defaultdict(lambda: defaultdict(list))
    for tag in tags:
        scene_name = tag.scene or channel_name
        npc_name = tag.npc or "Story Tags"
        by_scene[scene_name][npc_name].append(tag)

    sections = []
    for scene_name, npcs in by_scene.items():
        scene_header = f"__**{scene_name}**__"
        npc_sections = []
        # Sort NPC names so "Story Tags" appears first
        sorted_npcs = sorted(npcs.keys(), key=lambda x: (x != "Story Tags", x))
        for npc_name in sorted_npcs:
            npc_tags = npcs[npc_name]
            npc_header = f"\t**{npc_name}**"
            tag_lines = [f"\t\t{format_tag(tag)}" for tag in npc_tags]
            npc_sections.append(npc_header + "\n" + "\n".join(tag_lines))
        sections.append(scene_header + "\n" + "\n".join(npc_sections))

    return "\n\n".join(sections)


# --- Prefix Commands (!) ---

@bot.command(name="ping")
async def ping(ctx: commands.Context):
    """Check bot latency."""
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latency: {latency_ms}ms")


@bot.command(name="addtag")
async def add_tag(ctx: commands.Context, name: str, scene: str = None, npc: str = None, level: int = None):
    """Create a tag. Usage: !addtag <name> [scene] [npc] [level]"""
    channel_name = ctx.channel.name if hasattr(ctx.channel, 'name') else str(ctx.channel.id)
    tag = db.create_tag(name=name, channel=channel_name, scene=scene, npc=npc, level=level)
    await ctx.send(f"Created tag:\n{format_tag(tag)}")


@bot.command(name="tags")
async def list_tags(ctx: commands.Context):
    """List all tags in this channel, grouped by scene and NPC."""
    channel_name = ctx.channel.name if hasattr(ctx.channel, 'name') else str(ctx.channel.id)
    tags = db.get_tags_by_channel(channel_name)
    if not tags:
        await ctx.send("No tags in this channel.")
        return
    await ctx.send(format_tags_by_scene(tags, channel_name))


@bot.command(name="tag")
async def get_tag(ctx: commands.Context, tag_id: int):
    """Get a specific tag by ID. Usage: !tag <id>"""
    tag = db.get_tag(tag_id)
    if tag:
        await ctx.send(format_tag(tag))
    else:
        await ctx.send(f"No tag found with ID {tag_id}.")


@bot.command(name="deltag")
async def delete_tag(ctx: commands.Context, tag_id: int):
    """Delete a tag by ID. Usage: !deltag <id>"""
    if db.delete_tag(tag_id):
        await ctx.send(f"Deleted tag {tag_id}.")
    else:
        await ctx.send(f"No tag found with ID {tag_id}.")


@bot.command(name="modstatuslevel")
async def mod_status_level(ctx: commands.Context, tag_id: int, level: int):
    """Update a tag's level. Usage: !modstatuslevel <id> <level>"""
    tag = db.update_tag(tag_id, level=level)
    if tag:
        await ctx.send(f"Updated tag:\n{format_tag(tag)}")
    else:
        await ctx.send(f"No tag found with ID {tag_id}.")


@bot.command(name="modtagname")
async def mod_tag_name(ctx: commands.Context, tag_id: int, *, name: str):
    """Update a tag's name. Usage: !modtagname <id> <name>"""
    tag = db.update_tag(tag_id, name=name)
    if tag:
        await ctx.send(f"Updated tag:\n{format_tag(tag)}")
    else:
        await ctx.send(f"No tag found with ID {tag_id}.")


@bot.command(name="wipescene")
async def clear_scene(ctx: commands.Context, *, scene: str = None):
    """Clear all tags for a scene in this channel. Usage: !clearscene [scene]

    If no scene is provided, clears tags in the default scene.
    """
    channel_name = ctx.channel.name if hasattr(ctx.channel, 'name') else str(ctx.channel.id)
    count = db.delete_tags_by_scene(channel_name, scene)
    scene_display = scene or "Default Scene"
    await ctx.send(f"Cleared {count} tag(s) from **{scene_display}**.")


# --- Slash Commands (/) ---

@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    """Slash command version of ping."""
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! Latency: {latency_ms}ms")


@bot.tree.command(name="addtag", description="Create a new tag")
@app_commands.describe(
    name="Tag name",
    scene="Scene name (optional)",
    npc="NPC name (optional)",
    level="Level (optional)"
)
async def slash_add_tag(
    interaction: discord.Interaction,
    name: str,
    scene: str = None,
    npc: str = None,
    level: int = None
):
    """Create a new tag in the current channel."""
    channel_name = interaction.channel.name if hasattr(interaction.channel, 'name') else str(interaction.channel.id)
    tag = db.create_tag(name=name, channel=channel_name, scene=scene, npc=npc, level=level)
    await interaction.response.send_message(f"Created tag:\n{format_tag(tag)}")


@bot.tree.command(name="tags", description="List all tags in this channel")
async def slash_list_tags(interaction: discord.Interaction):
    """List all tags in the current channel, grouped by scene and NPC."""
    channel_name = interaction.channel.name if hasattr(interaction.channel, 'name') else str(interaction.channel.id)
    tags = db.get_tags_by_channel(channel_name)
    if not tags:
        await interaction.response.send_message("No tags in this channel.")
        return
    await interaction.response.send_message(format_tags_by_scene(tags, channel_name))


@bot.tree.command(name="tag", description="Get a specific tag by ID")
@app_commands.describe(tag_id="The tag ID to retrieve")
async def slash_get_tag(interaction: discord.Interaction, tag_id: int):
    """Get a specific tag by ID."""
    tag = db.get_tag(tag_id)
    if tag:
        await interaction.response.send_message(format_tag(tag))
    else:
        await interaction.response.send_message(f"No tag found with ID {tag_id}.")


@bot.tree.command(name="deltag", description="Delete a tag by ID")
@app_commands.describe(tag_id="The tag ID to delete")
async def slash_delete_tag(interaction: discord.Interaction, tag_id: int):
    """Delete a tag by ID."""
    if db.delete_tag(tag_id):
        await interaction.response.send_message(f"Deleted tag {tag_id}.")
    else:
        await interaction.response.send_message(f"No tag found with ID {tag_id}.")


@bot.tree.command(name="modstatuslevel", description="Update a tag's level")
@app_commands.describe(tag_id="The tag ID to update", level="New level value")
async def slash_mod_status_level(interaction: discord.Interaction, tag_id: int, level: int):
    """Update a tag's level."""
    tag = db.update_tag(tag_id, level=level)
    if tag:
        await interaction.response.send_message(f"Updated tag:\n{format_tag(tag)}")
    else:
        await interaction.response.send_message(f"No tag found with ID {tag_id}.")


@bot.tree.command(name="modtagname", description="Update a tag's name")
@app_commands.describe(tag_id="The tag ID to update", name="New name")
async def slash_mod_tag_name(interaction: discord.Interaction, tag_id: int, name: str):
    """Update a tag's name."""
    tag = db.update_tag(tag_id, name=name)
    if tag:
        await interaction.response.send_message(f"Updated tag:\n{format_tag(tag)}")
    else:
        await interaction.response.send_message(f"No tag found with ID {tag_id}.")


@bot.tree.command(name="clearscene", description="Clear all tags for a scene in this channel")
@app_commands.describe(scene="Scene name (leave empty for default scene)")
async def slash_clear_scene(interaction: discord.Interaction, scene: str = None):
    """Clear all tags for a scene in the current channel."""
    channel_name = interaction.channel.name if hasattr(interaction.channel, 'name') else str(interaction.channel.id)
    count = db.delete_tags_by_scene(channel_name, scene)
    scene_display = scene or "Default Scene"
    await interaction.response.send_message(f"Cleared {count} tag(s) from **{scene_display}**.")


# --- Error Handling ---

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Handle prefix command errors."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        await ctx.send(f"Error: {error}")


# Run the bot
if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables")
        print("Create a .env file with: DISCORD_BOT_TOKEN=your_token_here")
        exit(1)

    bot.run(token)
