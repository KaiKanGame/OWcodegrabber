#code by kaitxk | kaixk.xyz
#designed by hunter13004

import discord
from discord import app_commands
import requests
from PIL import Image
from io import BytesIO
import os
import re
import asyncio
from fuzzywuzzy import process

#global vars
oskey = 'apikey'
osurl = 'https://api.ocr.space/parse/image'

botIntents = discord.Intents.default()
botClient = discord.Client(intents=botIntents)
botCommandTree = app_commands.CommandTree(botClient)

def gimmecodes(fp, key=oskey):
    with open(fp, 'rb') as img:
        stuff = {
            'apikey': key,
            'language': 'eng'
        }
        hii = requests.post(osurl, files={'file': img}, data=stuff)
        hello = hii.json()
        if not hello.get('IsErroredOnProcessing', True):
            return hello['ParsedResults'][0]['ParsedText']
        else:
            return f"Error: {hello['ErrorMessage']}"

def cleanup(txt):
    foo = re.sub(r'[<•$]', '', txt)
    foo = re.sub(r'\s*:\s*', ':', foo)
    foo = re.sub(r'9k', '', foo)
    return foo.strip()

def processstuff(url, howmany):
    hiii = requests.get(url)
    img = Image.open(BytesIO(hiii.content))
    img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
    snippyzones = [
        (430, 396, 487, 68),
        (916, 407, 105, 24),
        (1021, 396, 240, 68)
    ]
    amtdown = [72, 73, 72]
    rs = []
    for rn in range(1, howmany + 1):
        r = []
        for tn, (x, y, w, h) in enumerate(snippyzones):
            snip = (x, y, x + w, y + h)
            circumcised = img.crop(snip)
            temppath = f'temp_row{rn}_text{tn + 1}.png'
            circumcised.save(temppath)
            raw = gimmecodes(temppath)
            goodtext = cleanup(raw) if raw else ""
            r.append(goodtext)
            snippyzones[tn] = (x, y + amtdown[tn], w, h)
            os.remove(temppath)
        if 'WORKSHOP CHAMBER' in r[0].upper():
            continue
        if 'CUSTOM GAME' in r[2].upper():
            rs.append([r[0], r[1]])
    return rs

async def keepoutofway(url, rplys):
    return await asyncio.to_thread(processstuff, url, rplys)

def ifixit(foo):
    chars = {"I": "1", "O": "0", "U": "V", "!": "1", "$": "S", "&": "8"}
    bar = list(foo)
    for i, item in enumerate(bar):
        for key, value in chars.items():
            if item == key:
                bar[i] = value
    foobar = "".join(bar)
    return foobar

def ifixitmap(dumb):
    overwatch_maps  = [
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
    sigma, s = process.extractOne(dumb, overwatch_maps)
    if s > 70:
        return sigma
    else:
        return dumb

def filterText(data):
  lines = data.splitlines()
  names = []
  codes = []

  for line in lines:
      name, code = line.split(": ")
      names.append(name)
      filtered_code = ifixit(code)
      codes.append(filtered_code)

  merged_data = "\n".join([f"{name}: {code}" for name, code in zip(names, codes)])
  return merged_data

def format(name, rows):
    r = f"{name}\n"
    for row in rows:
        r += f"{ifixitmap(row[0])}: {ifixit(row[1])}\n"
    return r.strip()

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botCommandTree.command(name="getcodes", description="Extracts replays from OW2 screenshot")
async def getcodes(interaction: discord.Interaction, name: str, attachment: discord.Attachment):
    await interaction.response.defer()
    url = attachment.url
    amt = 7
    rows = await keepoutofway(url, amt)
    finaltxt = format(name, rows)
    await interaction.followup.send(f"\n{finaltxt}\n")

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botCommandTree.command(name="getcodesraw", description="Extracts replays from OW2 screenshot, shows them only to you")
async def getcodesraw(interaction: discord.Interaction, attachment: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    url = attachment.url
    amt = 7
    name = ""
    rows = await keepoutofway(url, amt)
    finaltxt = format(name, rows)
    await interaction.followup.send(f"\n{finaltxt}\n")

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
