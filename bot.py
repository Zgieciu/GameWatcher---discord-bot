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
                name TEXT UNIQUE
            )
    """)

    conn.commit()
    conn.close()
    print("Baza danych została zainicjowana.")

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

    message = ''
    steam_game_id = 0

    try:    
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
        price_overview = data.get('price_overview')

        message += f"Gra: {data['name']}\n\n"

        if price_overview: 
            if price_overview['discount_percent'] > 0:
                message += f"Wykryto promocję {price_overview['discount_percent']}%\n"
                message += f"Cena aktualna: {price_overview['final_formatted']}\n"
                message += f"Cena przed obniżką: {price_overview['initial_formatted']}\n"
            else:
                message += f"Cena aktualna: {price_overview['final_formatted']}\n"
        else:
            message += f"Premiera gry nastąpi: {data['release_date']['date']}\n"

        await interaction.followup.send(message)

    except Exception as e: 
        await interaction.followup.send(f"Wystąpił błąd poczas pobierania danych: {e}")

@bot.tree.command(name='games_list', description='Wyświetla listę zapisanych gier')
async def games_list(interaction: discord.Interaction):
    await interaction.response.defer()

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM games_list")
        rows = cursor.fetchall()

    if not rows:
        await interaction.followup.send("Lista zapisanych gier jest pusta.")
        return
    
    message = 'Lista zapisanych gier:\n'
    for row in rows:
        message += f"• {row[0]}\n"
    
    await interaction.followup.send(message)

@bot.tree.command(name='add_game', description='Dodaj grę to listy zapisanych gier')
@app_commands.describe(game_title='Wpisz nazwę gry którą chcesz dodać')
async def add_game(interaction: discord.Interaction, game_title: str):
    await interaction.response.defer()

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM games_list WHERE name = ?", (game_title,))
        game_found = cursor.fetchone()

        if game_found:
            await interaction.followup.send(f"Gra {game_title} znajduje się już na liście.")
            return
        
        cursor.execute("INSERT INTO games_list (name) VALUES (?)", (game_title,))
        conn.commit()

    await interaction.followup.send(f"Gra {game_title} została pomyślnie dodana do listy.")

@bot.tree.command(name='remove_game', description='Usuń grę z listy zapisanych gier')
@app_commands.describe(game_title='Wpisz nazwę gry którą chcesz usunąć')
async def remove_game(interaction: discord.Interaction, game_title: str):
    await interaction.response.defer()

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM games_list WHERE name = ?", (game_title,))
        conn.commit()

        if cursor.rowcount > 0:
            await interaction.followup.send(f"Gra {game_title} została usunięta z lity.")
        else:
            await interaction.followup.send(f"Nie znaleziono gry {game_title} na liście.")

bot.run(os.getenv('BOT_TOKEN'))