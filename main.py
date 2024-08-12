import discord
from discord.ext import commands
from discord import app_commands

# Your Discord Bot Token
DISCORD_TOKEN = 'YOUR Token'

# Setting up intents and creating the bot object
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store the welcome channel and message for each guild
guild_settings = {}
welcome_message = {}
guild_ticket_settings = {}

# Event: When the bot is ready
@bot.event
async def on_ready():
    await bot.tree.sync()  # Syncs slash commands with Discord
    print(f'Bot is ready! Logged in as {bot.user}')

# Slash Command: /help
@bot.tree.command(name="help", description="Displays all available commands.")
async def show_help(interaction: discord.Interaction):
    help_embed = discord.Embed(
        title="Help - Available Commands",
        description="Here is a list of all available commands:",
        color=discord.Color.blue()
    )

    # List of commands with descriptions
    commands_list = {
        "/help": "Displays this help message.",
        "/welcome": ("Configures the channel and message for welcome messages.\n"
                     "Usage: `/welcome channel:#channel_name message:Welcome {member.mention} to our server!`"),
        "/welcomestart": "Sends the welcome message in the configured channel.",
        "/poll": "Creates a poll.\nUsage: `/poll question:Your Question options:Option1,Option2,... NOT AVIABLE`",
        "/embed": ("Sends an embedded message.\n"
                   "Usage: `/embed title:Your Title description:Your Description footer:Your Footer`"),
        "/ticket": "Creates a ticket button for your ticket channel..\nUsage: `/ticket`",
        "/ticketclose": "Closes the ticket channel (gives you a button to delte it).\nUsage: `/ticketclose`",
        "/purge": "Deletes a specified number of messages, or messages from a specific user.\nUsage: `/purge amount:10 user:@username`"
        "Tickets: A High Team Staff Member has to decide which roles have acces to this Channel, give permission to roles. Otherwise every role with the permission *administrator* has acces to the ticket."
    }

    # Add fields to the embed for each command
    for command, description in commands_list.items():
        help_embed.add_field(name=command, value=description, inline=False)
    
    await interaction.response.send_message(embed=help_embed, ephemeral=True)

# Slash Command: Sends an embedded message
@bot.tree.command(name="embed", description="Sends an embedded message.")
@app_commands.describe(
    title="The title of the embed",
    description="The description of the embed",
    footer="The footer of the embed"
)
async def embed(interaction: discord.Interaction, title: str, description: str, footer: str = None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    
    if footer:
        embed.set_footer(text=footer)
    
    await interaction.response.send_message(embed=embed)

# Slash Command: Purge command
@bot.tree.command(name="purge", description="Deletes messages in the channel.")
@app_commands.describe(
    user="The user whose messages should be deleted.",
    amount="The number of messages to delete.",
    all="Deletes all messages in the channel."
)
async def purge(interaction: discord.Interaction, user: discord.Member = None, amount: int = None, all: bool = False):
    if all:
        await interaction.response.defer()
        deleted = await interaction.channel.purge()
        await interaction.followup.send(f"All {len(deleted)} messages have been deleted.", ephemeral=True)
        return

    if user and amount:
        def check(msg):
            return msg.author == user

        deleted = await interaction.channel.purge(limit=amount, check=check)
        await interaction.response.send_message(f"{len(deleted)} messages from {user.display_name} have been deleted.", ephemeral=True)
    elif amount:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"{len(deleted)} messages have been deleted.", ephemeral=True)
    else:
        await interaction.response.send_message("Please specify either a number of messages or a user.", ephemeral=True)

# Prefix Command: Purge command
@bot.command(name="purge", help="Deletes messages in the channel. Usage: !purge <amount> | [user]")
async def purge_prefix(ctx, amount: int, user: discord.Member = None):
    if user:
        def check(msg):
            return msg.author == user

        deleted = await ctx.channel.purge(limit=amount, check=check)
        await ctx.send(f"{len(deleted)} messages from {user.display_name} have been deleted.", delete_after=5)
    else:
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(f"{len(deleted)} messages have been deleted.", delete_after=5)

# Slash Command: /ticketconfig to configure ticket settings
@bot.tree.command(name="ticketconfig", description="Configures the ticket system settings.")
@app_commands.describe(
    category="The category under which ticket channels will be created.",
    roles="Roles to be tagged when a ticket is created (comma-separated)."
)
async def ticket_config(interaction: discord.Interaction, category: discord.CategoryChannel = None, roles: str = None):
    guild_id = interaction.guild.id
    settings = guild_ticket_settings.setdefault(guild_id, {})

    if category:
        settings['category_id'] = category.id
        response_message = f"Ticket channels will be created under the category: {category.name}"
    else:
        response_message = "No category set for ticket channels."

    if roles:
        # Process roles input
        role_names = [role.strip() for role in roles.split(',')]
        role_ids = []
        for role_name in role_names:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                role_ids.append(role.id)
        settings['role_ids'] = role_ids
        response_message += f"\nRoles to be tagged: {', '.join(role_names)}"
    else:
        response_message += "\nNo roles set to be tagged."

    await interaction.response.send_message(response_message, ephemeral=True)

# Slash Command: /ticket to create a ticket with a button
@bot.tree.command(name="ticket", description="Creates a ticket button in the specified public channel.")
@app_commands.describe(channel="The channel where the ticket button will be posted.")
async def create_ticket(interaction: discord.Interaction, channel: discord.TextChannel):
    guild = interaction.guild
    settings = guild_ticket_settings.get(guild.id, {})

    # Create an embed for the ticket
    ticket_embed = discord.Embed(
        title="Support Ticket",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )
    
    # Create a button for the ticket
    button = discord.ui.Button(label="Create Ticket", style=discord.ButtonStyle.primary)

    # Callback function when the button is clicked
    async def button_callback(interaction: discord.Interaction):
        guild = interaction.guild
        category_id = settings.get('category_id')
        role_ids = settings.get('role_ids', [])
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        # Create the category if it doesn't exist
        category = discord.utils.get(guild.categories, id=category_id)
        if not category:
            category = await guild.create_category(name="Tickets")

        # Create a private ticket channel under the category
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites,
            category=category,
            topic=f"Ticket for {interaction.user.display_name}"
        )
        
        # Tag roles in the ticket channel
        if role_ids:
            roles_mentions = [guild.get_role(role_id).mention for role_id in role_ids]
            await ticket_channel.send(f"Roles tagged: {', '.join(roles_mentions)}")

        # Create and send the close button
        close_button = discord.ui.Button(label="Close Ticket", style=discord.ButtonStyle.danger)

        async def close_button_callback(interaction: discord.Interaction):
            await interaction.channel.delete()

        close_button.callback = close_button_callback

        view = discord.ui.View()
        view.add_item(close_button)
        
        await ticket_channel.send(f"{interaction.user.mention} Your ticket has been created.", view=view)
        await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)
    
    # Assign the callback to the button
    button.callback = button_callback

    # Create a view and add the button to the view
    view = discord.ui.View()
    view.add_item(button)
    
    # Send the embed with the button to the specified channel
    await channel.send(embed=ticket_embed, view=view)


    # Event: When a member joins the server
@bot.event
async def on_member_join(member):
    await send_welcome_message(member)

# Function to send the welcome message
async def send_welcome_message(member):
    guild = member.guild
    settings = guild_settings.get(guild.id)
    if settings:
        channel_id = settings.get('channel_id')
        welcome_message = settings.get('welcome_message', "Welcome to the server, {member.mention}!")
        
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.send(welcome_message.format(member=member))

# Slash Command: /welcome to set the welcome channel and message
@bot.tree.command(name="welcome", description="Configures the channel and message for welcome messages.")
@app_commands.describe(channel="Select the channel for welcome messages.", 
                       message="(Optional) Customize the welcome message.")
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel, message: str = None):
    guild_id = interaction.guild.id
    
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {}

    guild_settings[guild_id]['channel_id'] = channel.id
    if message:
        guild_settings[guild_id]['welcome_message'] = message

    response_message = f"Welcome messages will now be sent in {channel.mention}."
    if message:
        response_message += f" The custom welcome message has been set."

    await interaction.response.send_message(response_message, ephemeral=True)

# Slash Command: /welcomestart to manually trigger the welcome message
@bot.tree.command(name="welcomestart", description="Sends the welcome message in the configured channel.")
async def welcome_start(interaction: discord.Interaction):
    member = interaction.user  # Use the command invoker as the test member
    await send_welcome_message(member)
    await interaction.response.send_message("The welcome message has been sent.", ephemeral=True)


# Run the bot
bot.run("YOUR Token")
