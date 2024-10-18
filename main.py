# code by kaitxk | kaixk.xyz
# designed by hunter13004

import discord
from discord import app_commands
import requests
from PIL import Image
from io import BytesIO
import os
import re
import asyncio
from fuzzywuzzy import process

# global vars
ocr_space_key = 'apikey'
ocr_space_api_url = 'https://api.ocr.space/parse/image'

botIntents = discord.Intents.default()
botClient = discord.Client(intents=botIntents)
botCommandTree = app_commands.CommandTree(botClient)


def process_image_using_ocr_space(image: Image, key: str = ocr_space_key) -> str:
    with open(image, 'rb') as img:
        payload = {
            'apikey': key,
            'language': 'eng'
        }
        response = requests.post(ocr_space_api_url, files={'file': img}, data=payload)
        response_json = response.json()
        if not response_json.get('IsErroredOnProcessing', True):
            return response_json['ParsedResults'][0]['ParsedText']
        else:
            return f"Error: {response_json['ErrorMessage']}"


def cleanup_text(text: str) -> str:
    cleaned_text = re.sub(r'[<•$]', '', text)
    cleaned_text = re.sub(r'\s*:\s*', ':', cleaned_text)
    cleaned_text = re.sub(r'9k', '', cleaned_text)
    return cleaned_text.strip()


def process_image(url: str, replay_count: int) -> list[list[str]]:
    response = requests.get(url)
    source_image = Image.open(BytesIO(response.content))
    source_image = source_image.resize((1920, 1080), Image.Resampling.LANCZOS)
    cropping_zones = [
        (430, 396, 487, 68),
        (916, 407, 105, 24),
        (1021, 396, 240, 68)
    ]
    crop_zone_increments = [72, 73, 72]
    row_list = []
    for row_number in range(1, replay_count + 1):
        row = []
        for col_number, (x, y, width, height) in enumerate(cropping_zones):
            snip = (x, y, x + width, y + height)
            cropped_image = source_image.crop(snip)
            temporary_filename = f'temp_row{row_number}_text{col_number + 1}.png'
            cropped_image.save(temporary_filename)
            raw_text = process_image_using_ocr_space(temporary_filename)
            cleaned_text = cleanup_text(raw_text) if raw_text else ""
            row.append(cleaned_text)
            cropping_zones[col_number] = (x, y + crop_zone_increments[col_number], width, height)
            os.remove(temporary_filename)
        if 'WORKSHOP CHAMBER' in row[0].upper():
            continue
        if 'CUSTOM GAME' in row[2].upper():
            row_list.append([row[0], row[1]])
    return row_list


async def start_image_processing(url: str, replay_count: int) -> asyncio.Coroutine:
    return await asyncio.to_thread(process_image, url, replay_count)


def replay_code_autocorrect(raw_code_text: str) -> str:
    char_replacement_dict = {"I": "1", "O": "0", "U": "V", "!": "1", "$": "S", "&": "8"}
    raw_code_char_list = list(raw_code_text)
    for i, item in enumerate(raw_code_char_list):
        for key, value in char_replacement_dict.items():
            if item == key:
                raw_code_char_list[i] = value
    corrected_code_text = "".join(raw_code_char_list)
    return corrected_code_text


def map_name_autocorrect(map_name: str) -> str:
    overwatch_maps = [
        "Antarctic Peninsula",
        "Busan",
        "Ilios",
        "Lijiang Tower",
        "Nepal",
        "Oasis",
        "Samoa",
        "Circuit Royal",
        "Dorado",
        "Havana",
        "Junkertown",
        "Rialto",
        "Route 66",
        "Shambali Monastery",
        "Watchpoint: Gibraltar",
        "New Junk City",
        "Suravasa",
        "Blizzard World",
        "Eichenwalde",
        "Hollywood",
        "King's Row",
        "Midtown",
        "Numbani",
        "Paraiso",
        "Colosseo",
        "Esperanca",
        "New Queen Street",
        "Runasapi",
        "Hanaoka",
        "Throne of Anubis"
    ]
    corrected_map_name, autocorrect_confidence = process.extractOne(map_name, overwatch_maps)
    if autocorrect_confidence > 70:
        return corrected_map_name
    else:
        return map_name


def filter_text(data: str) -> str:
    lines = data.splitlines()
    names = []
    codes = []

    for line in lines:
        name, code = line.split(": ")
        names.append(name)
        filtered_code = replay_code_autocorrect(code)
        codes.append(filtered_code)

    merged_data = "\n".join([f"{name}: {code}" for name, code in zip(names, codes)])
    return merged_data


def format_text(name: str, rows: list[list[str]]) -> str:
    formatted_text = f"{name}\n"
    for row in rows:
        formatted_text += f"{map_name_autocorrect(row[0])}: {replay_code_autocorrect(row[1])}\n"
    return formatted_text.strip()


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botCommandTree.command(name="getcodes", description="Extracts replays from OW2 screenshot")
async def get_codes(interaction: discord.Interaction, name: str, attachment: discord.Attachment):
    await interaction.response.defer()
    url = attachment.url
    amt = 7
    rows = await start_image_processing(url, amt)
    final_text = format_text(name, rows)
    await interaction.followup.send(f"\n{final_text}\n")


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botCommandTree.command(name="getcodesraw", description="Extracts replays from OW2 screenshot, shows them only to you")
async def get_codes_raw(interaction: discord.Interaction, attachment: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    url = attachment.url
    amt = 7
    name = ""
    rows = await start_image_processing(url, amt)
    final_text = format_text(name, rows)
    await interaction.followup.send(f"\n{final_text}\n")


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botCommandTree.command(name="feedback", description="sends feedback form link")
async def feedback(interaction: discord.Interaction):
    await interaction.response.defer()
    await interaction.followup.send("https://forms.gle/esXC72V6hGznYGmu9")


@botClient.event
async def on_ready():
    await botCommandTree.sync()
    print(f'logged in as {botClient.user}')


botClient.run('token')
