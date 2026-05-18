import discord
from discord import app_commands
from discord.ext import commands
import requests
from dotenv import load_dotenv
import os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user.name}!")
    try:
        synced = await bot.tree.sync()
        print(f"Liczba zsynchronizowanych komend: {len(synced)}")
    except Exception as e:
        print(f"Błąd poczas synchonizacji komend: {e}")

@bot.tree.command(name="check_price", description="Sprawdza cenę gry na Steam")
@app_commands.describe(game_title="Wpisz nazwę gry")
async def check_price(interaction: discord.Integration, game_title: str):
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
            raise Exception("Nie znaleziono podanej gry")         
        
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

bot.run(os.getenv('BOT_TOKEN'))