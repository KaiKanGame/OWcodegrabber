import discord
from discord import app_commands
from discord.ext import commands
import cv2
import numpy as np
import requests
from io import BytesIO
from PIL import Image
import pytesseract
import os

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
botIntents = discord.Intents.default()
botClient = discord.Client(intents=botIntents)
botCommandTree = app_commands.CommandTree(botClient)
maps = [
    "Antarctic Peninsula", "Busan", "Ilios", "Lijiang Tower", "Nepal", "Oasis", "Samoa", "Circuit Royal",
    "Dorado", "Havana", "Junkertown", "Rialto", "Route 66", "Shambali Monastery", "Watchpoint: Gibraltar",
    "New Junk City", "Suravasa", "Blizzard World", "Eichenwalde", "Hollywood", "King's Row", "Midtown",
    "Numbani", "Paraiso", "Colosseo", "Esperanca", "New Queen Street", "Runasapi", "Hanaoka", "Throne of Anubis"
]

def saveCutImg(img, i):
    imgP = f"cropped_row_{i}.png"
    cv2.imwrite(imgP, img)
    print(f"Saved cropped row as {imgP}")

def findBox(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        foo = max(contours, key=cv2.contourArea)
        return cv2.boundingRect(foo)
    return None

def findOrangeP(mask):
    return (cv2.countNonZero(mask) / mask.size) * 100

def processImg(url):
    response = requests.get(url)
    print("got img")
    img = Image.open(BytesIO(response.content))
    img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
    print("resized img.")
    image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    print("converted img to cv.")
    template = cv2.imread('share.png')
    if template is None:
        return [], []

    print("got share location temp ")
    imageGrey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    templateGrey = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(imageGrey, templateGrey, cv2.TM_CCOEFF_NORMED)
    iconH, iconW = templateGrey.shape
    locations = np.where(result >= 0.8)
    print(f"found {len(locations[0])} locations")
    print(f"locations: {locations}")
    if len(locations[0]) == 0:
        print("couldnt find share icaon in img")
        return [], []

    lowerO, upperO = np.array([5, 100, 100]), np.array([20, 255, 255])
    relX, relY, relW, relH, count = None, None, None, None, 1
    rowT, codeT = [], []


    for pt in zip(*locations[::-1]):
        print(pt)
        row = image[max(0, pt[1] - 15):min(image.shape[0], pt[1] + iconH + 25), :]
        saveCutImg(row, count)
        hsvR = cv2.cvtColor(row, cv2.COLOR_BGR2HSV)
        maskO = cv2.inRange(hsvR, lowerO, upperO)
        print(f"row {count}")

        if count == 1:
            x, y, w, h = findBox(maskO)
            print(f"cubox for row: {(x, y, w, h)}")
            if x is not None:
                relX, relY, relW, relH = x / iconW, y / iconH, w / iconW, h / iconH
                boxO = row[y:y + h, x:x + w]
                codeText = pytesseract.image_to_string(boxO)
                codeT.append(codeText)
                print(f"code text: {codeText}")

        else:
            if relX is not None:
                x, y, w, h = int(relX * iconW), int(relY * iconH), int(relW * iconW), int(relH * iconH)
                cropped = row[y:y + h, x:x + w]
                orangeP = findOrangeP(
                    cv2.inRange(cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV), lowerO, upperO))
                print(f"orangeP for {count}: {orangeP}%")
                if orangeP >= 70:
                    codeText = pytesseract.image_to_string(cropped)
                    codeT.append(codeText)
                    print(f"{count} code {codeText}")

        rowText = pytesseract.image_to_string(row)
        rowT.append(rowText)
        print(f"{count} text {rowText}")
        count += 1

    print("done")
    return rowT, codeT

def formatText(name, rowT, codeT):
    foo = f"{name}\n"
    bar = min(len(rowT), 7)
    for i in range(bar, 0, -1):
        foo += f"{rowT[i - 1]}: {codeT[i - 1]}\n"
    print("text formatted")
    return foo

def checkMap(rowT):
    for i in range(len(rowT)):
        for map in maps:
            if map.lower() in rowT[i].lower():
                rowT[i] = map
                print(f"'{map}'in {i + 1}.")
                break
    return rowT

@botClient.event
async def on_ready():
    print(f'logged in as {botClient.user}')

    try:
        synced = await botCommandTree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botCommandTree.command(name="getcodes", description="Extracts replays from OW2 screenshot")
async def processimage(interaction: discord.Interaction, name: str, number_of_replays: int, attachment: discord.Attachment):
    try:
        await interaction.response.defer()
        print(f"recived cmd getcodes, {name}, {attachment.filename}")
        imgURL = attachment.url
        rowT, codeT = processImg(imgURL)
        for i, (rT, cT) in enumerate(zip(rowT, codeT), start=1):
            print(f"row {i}, text from tess: {rT}")
            print(f"code {i}, text from tess: {cT}")
        filtered = [(row, code) for row, code in zip(rowT, codeT) if 'CUSTOM' in row.upper()]
        rowT, codeT = zip(*filtered) if filtered else ([], [])
        rowT = checkMap(list(rowT))
        formatted = formatText(name, rowT, codeT)
        await interaction.followup.send(f"```\n{formatted}\n```")
        print("sent")
    except Exception as e:
        await interaction.followup.send(f"error {str(e)}")
        print(f"err {e}")

botClient.run('TOKEM')
