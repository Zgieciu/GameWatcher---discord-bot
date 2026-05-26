import discord
from discord import app_commands
from discord.ext import commands
import requests
from dotenv import load_dotenv
import os
import sqlite3

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

def database_init():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS games_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                name TEXT,
                UNIQUE(server_id, name)
            )
    """)

    conn.commit()
    conn.close()
    print("Baza danych została zainicjowana.")

def get_game_data(game_title):
    steam_game_id = None

    response = requests.get(f"https://store.steampowered.com/api/storesearch/?term={game_title}&l=polish&cc=PL")
    data = response.json()

    for item in data['items']:
        if game_title.upper() in item['name'].strip().upper():
            steam_game_id = str(item['id'])
            break

    if not steam_game_id:
        raise Exception('Nie znaleziono podanej gry')         
    
    response = requests.get(f"https://store.steampowered.com/api/appdetails?appids={steam_game_id}&cc=pl")
    data = response.json()
    data = data[steam_game_id]['data']

    return steam_game_id, data

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user.name}!")
    try:
        synced = await bot.tree.sync()
        print(f"Liczba zsynchronizowanych komend: {len(synced)}")
    except Exception as e:
        print(f"Błąd poczas synchonizacji komend: {e}")
    
    database_init()

@bot.tree.command(name='check_price', description='Sprawdza cenę gry na Steam')
@app_commands.describe(game_title='Wpisz nazwę gry')
async def check_price(interaction: discord.Interaction, game_title: str):
    await interaction.response.defer()

    try:    
        steam_game_id, data = get_game_data(game_title)
        price_overview = data.get('price_overview')

        embed = discord.Embed(
            title=data['name'],
            description='Aktualne informacje pobrane z API Steam',
            color=discord.Color.green(),
            url=f"https://store.steampowered.com/app/{steam_game_id}/{data['name'].replace(' ', '_')}/",
        )

        embed.set_image(url=data['header_image'])

        if price_overview: 
            if price_overview['discount_percent'] > 0:
                embed.add_field(name='Wykryto promocję', value=f"{price_overview['discount_percent']}%", inline=True)
                embed.add_field(name='Cena aktualna', value=price_overview['final_formatted'], inline=True)
                embed.add_field(name='Cena przed obniżką', value=price_overview['initial_formatted'], inline=True)
            else:
                embed.add_field(name='Cena aktualna', value=price_overview['final_formatted'])
        else:
            embed.add_field(name='Premiera gry nastąpi', value=data['release_date']['date'])
        
        embed.set_footer(text=f"Developer: {data['developers'][0]}")
        await interaction.followup.send(embed=embed)

    except Exception as e: 
        await interaction.followup.send(f"Wystąpił błąd poczas pobierania danych: {e}")

@bot.tree.command(name='games_list', description='Wyświetla listę zapisanych gier')
async def games_list(interaction: discord.Interaction):
    await interaction.response.defer()
    
    server_id = interaction.guild_id

    embed = discord.Embed(
        title='Lista zapisanych gier',
        color=discord.Color.green(),
    )

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM games_list WHERE server_id = ?", (server_id,))
        rows = cursor.fetchall()

    if not rows:
        embed.add_field(name='', value='Lista zapisanych gier jest pusta.')
        await interaction.followup.send(embed=embed)
        return
    
    for row in rows:
        embed.add_field(name='', value=f"• {row[0]}", inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name='add_game', description='Dodaj grę to listy zapisanych gier')
@app_commands.describe(game_title='Wpisz nazwę gry którą chcesz dodać')
async def add_game(interaction: discord.Interaction, game_title: str):
    await interaction.response.defer()

    server_id = interaction.guild_id

    embed = discord.Embed(
        title='Dodawanie gry do listy',
        color=discord.Color.green(),
    )

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM games_list WHERE name = ? AND server_id = ?", (game_title, server_id,))
        game_found = cursor.fetchone()

        if game_found:
            embed.add_field(name='', value=f"Gra {game_title} znajduje się już na liście.")
            await interaction.followup.send(embed=embed)
            return
        
        cursor.execute("INSERT INTO games_list (name, server_id) VALUES (?, ?)", (game_title, server_id,))
        conn.commit()

    embed.add_field(name='', value=f"Gra {game_title} została pomyślnie dodana do listy.")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name='remove_game', description='Usuń grę z listy zapisanych gier')
@app_commands.describe(game_title='Wpisz nazwę gry którą chcesz usunąć')
async def remove_game(interaction: discord.Interaction, game_title: str):
    await interaction.response.defer()

    server_id = interaction.guild_id

    embed = discord.Embed(
        title='Usuwanie gry z listy',
        color=discord.Color.green(),
    )

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM games_list WHERE name = ? AND server_id = ?", (game_title, server_id))
        conn.commit()

        if cursor.rowcount > 0:
            embed.add_field(name='', value=f"Gra {game_title} została usunięta z lity.")
            await interaction.followup.send(embed=embed)
        else:
            embed.add_field(name='', value=f"Nie znaleziono gry {game_title} na liście.")
            await interaction.followup.send(embed=embed)

bot.run(os.getenv('BOT_TOKEN'))