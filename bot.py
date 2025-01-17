import discord
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
from dotenv import load_dotenv
import os
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# Carrega o token do arquivo .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configuração de intents
intents = discord.Intents.default()
intents.message_content = True

# Inicialização do bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Dicionário para armazenar os check-ins
checkins = {}

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

url = "https://docs.google.com/spreadsheets/d/1fd_OXN8vQVldB7R1Bb-Hbtr8nEQIIqWB42v85mC3HvI/edit?gid=0#gid=0"

credenciais = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(credenciais)
sheet = client.open_by_url(url)
tab_bank = sheet.worksheet("Banco")
tab_deposit = sheet.worksheet("Deposito")

# Diretório para salvar os arquivos de check-in
CHECKIN_DIR = "checkins"
if not os.path.exists(CHECKIN_DIR):
    os.makedirs(CHECKIN_DIR)

def salvar_checkins():
    """Salva os check-ins em um arquivo com data e hora do encerramento."""
    if checkins:
        file_name = f"{CHECKIN_DIR}/checkins_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        # Especifica o encoding UTF-8 ao abrir o arquivo
        with open(file_name, "w", encoding="utf-8") as file:
            for user_id, user_name in checkins.items():
                file.write(f"{user_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")  # Inclui data e hora
        return file_name
    return None

@bot.event
async def on_ready():
    print(f'Bot logado como {bot.user}!')

# Classe personalizada para gerenciar os botões
class CheckinView(View):
    def __init__(self, timeout):
        super().__init__(timeout=timeout)  # Define o tempo limite para a view

    @discord.ui.button(label="Marcar Presença", style=discord.ButtonStyle.green)
    async def marcar_presença(self, interaction: discord.Interaction, button: Button):
        """Ação para o botão de marcar presença."""
        user_id = interaction.user.id
        user_name = interaction.user.display_name

        if user_id not in checkins:
            checkins[user_id] = user_name
            await interaction.response.send_message(f"{user_name}, você marcou presença com sucesso!", ephemeral=True)
            addPresença(user_id)
        else:
            await interaction.response.send_message(f"{user_name}, você já marcou presença!", ephemeral=True)

    async def on_timeout(self):
        """Ação a ser tomada quando o tempo limite expira."""
        for child in self.children:
            child.disabled = True  # Desativa todos os botões

        # Salvar automaticamente os check-ins
        file_name = salvar_checkins()
        if file_name:
            content = f"O check-in foi encerrado! A lista foi salva em `{file_name}`."
        else:
            content = "O check-in foi encerrado, mas ninguém marcou presença."

        checkins.clear()

        await self.message.edit(content=content, view=self)

def addPresença(user_id):
    user_ids = tab_deposit.col_values(2)
    presenca = tab_deposit.col_values(3)

    row_index_presenca = user_ids.index(str(user_id)) + 1
    current_value_presenca = int(presenca[row_index_presenca - 1]) if row_index_presenca <= len(presenca) else 0
    new_value_presenca = current_value_presenca + 1
    tab_deposit.update_cell(row_index_presenca, 3, new_value_presenca)

@bot.command()
async def checkin(ctx):
    """Inicia o processo de check-in com um botão, disponível por 10 minutos."""
    view = CheckinView(timeout=10)  # 10 minutos = 600 segundos
    message = await ctx.send(
        "Clique no botão abaixo para marcar sua presença 💚 (disponível por 10 minutos):", 
        view=view
    )
    view.message = message  # Associa a mensagem à view para que ela possa ser editada ao expirar


    #Chama a lista de presença no chat.
@bot.command()
async def lista_checkins(ctx):
    if not checkins:
        await ctx.send("Ninguém fez check-in ainda.")
    else:
        lista = "\n".join(checkins.values())
        await ctx.send(f"Usuários que fizeram check-in:\n{lista}")

@bot.command()
async def saldo(ctx):
    user_ids = tab_bank.col_values(2)
    crows = tab_bank.col_values(3)

    row_index = user_ids.index(str(ctx.author.id)) + 1
    current_value_crow = float(crows[row_index - 1].replace(",", ".")) if row_index <= len(crows) else 0
    
    await ctx.send(f"Seu saldo é: {current_value_crow} Crows!", ephemeral=True)

@bot.command()
async def depositar(ctx):
    user_ids = tab_bank.col_values(2)
    crows = tab_bank.col_values(3)

    user_ids_deposit = tab_deposit.col_values(2)
    crows_deposit = tab_deposit.col_values(5)

    user_ids_deposit.pop(0)
    crows_deposit.pop(0)
    user_ids.pop(0)
    crows.pop(0)

    for user_id in user_ids:
        row_index = user_ids.index(user_id) + 1

        current_value_crow = float(crows[row_index - 1].replace(",", ".")) if row_index <= len(crows) else 0
        update_value_crow = float(crows_deposit[row_index - 1].replace(",", ".")) if row_index <= len(crows_deposit) else 0

        new_value_crow = current_value_crow + update_value_crow
        
        tab_bank.update_cell(row_index + 1, 3, new_value_crow)
    
@bot.command()
@commands.has_role("[👑] STAFF")
async def limpar(ctx):
    user_ids = tab_bank.col_values(2)
    presencas = tab_deposit.col_values(3)
    
    user_ids.pop(0)
    presencas.pop(0)

    for user_id in user_ids:
        row_index = user_ids.index(user_id) + 1
        tab_deposit.update_cell(row_index + 1, 3, 0)

# Executa o bot
bot.run(TOKEN)