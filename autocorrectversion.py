import discord
from discord import app_commands
from discord.ext import commands
import requests
from PIL import Image
from io import BytesIO
import pytesseract
import os
from fuzzywuzzy import fuzz
import time
import sys

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
botIntents = discord.Intents.default()
botClient = commands.Bot(command_prefix="!", intents=botIntents)

overwatchMaps = [
    "Antarctic Peninsula", "Busan", "Ilios", "Lijiang Tower", "Nepal", "Oasis", "Samoa", "Circuit Royal",
    "Dorado", "Havana", "Junkertown", "Rialto", "Route 66", "Shambali Monastery", "Watchpoint: Gibraltar",
    "New Junk City", "Suravasa", "Blizzard World", "Eichenwalde", "Hollywood", "King's Row", "Midtown",
    "Numbani", "Paraiso", "Colosseo", "Esperanca", "New Queen Street", "Runasapi", "Hanaoka", "Throne of Anubis"
]
saveDir = "cropped"
os.makedirs(saveDir, exist_ok=True)
cropAreas = [(430, 396, 487, 68), (916, 407, 105, 24), (1021, 396, 240, 68)]
moveDownSteps = [72, 73, 72]
numRows = 7
bw = "bw"
grey = "gray"
os.makedirs(bw, exist_ok=True)
os.makedirs(grey, exist_ok=True)
chars = {"I": "1", "O": "0", "U": "V", "!": "1", "$": "S", "&": "8"}

@botClient.event
async def on_ready():
    try:
        await botClient.tree.sync()
        print('commmands synced')
    except Exception as e:
        print(f"Failed to sync commands: {e}")

def correctCodes(txt):
    corrected = list(txt)
    for i, char in enumerate(corrected):
        if char in chars:
            corrected[i] = chars[char]
    return "".join(corrected)

def cleanText(txtList):
    return [txt.replace("<", "").replace(">", "").replace("=", "") for txt in txtList]

def resizeImageFromURL(url):
    targetSize = (1920, 1080)
    response = requests.get(url)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))
    return img.resize(targetSize, Image.Resampling.LANCZOS)

def cropImageAndSave(img, cA, moveDown, nR):
    croppedImages = []
    for row in range(nR):
        for textNum, (x, y, width, height) in enumerate(cA):
            cropBox = (x, y, x + width, y + height)
            croppedImg = img.crop(cropBox)
            tempPath = f"{saveDir}/row{row + 1}_text{textNum + 1}.png"
            croppedImg.save(tempPath)
            croppedImages.append((croppedImg, tempPath))
            cA[textNum] = (x, y + moveDown[textNum], width, height)
    return croppedImages

def categorizeText(croppedImages):
    r = 3
    d = 0.5
    names, codes, types = [], [], []
    tesseractConfig = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    for croppedImg, imgName in croppedImages:
        if "text1" in imgName.lower():
            processedImg = croppedImg.convert("L").point(lambda x: 255 if x >= 200 else 0, '1')
            processedImgName = f"{bw}/bw_{os.path.basename(imgName)}"
        else:
            processedImg = croppedImg.convert("L")
            processedImgName = f"{grey}/gray_{os.path.basename(imgName)}"
        processedImg.save(processedImgName)
        text, retryCount = "", 0
        while retryCount < r:
            text = pytesseract.image_to_string(processedImg, config=tesseractConfig).strip()
            if text:
                break
            retryCount += 1
            time.sleep(d)
        if "text1" in imgName:
            names.append(text)
        elif "text2" in imgName:
            codes.append(text)
        elif "text3" in imgName:
            types.append(text)
    return names, codes, types

def filterCustomGames(names, codes, types):
    filteredNames, filteredCodes = [], []
    for idx, gameType in enumerate(types):
        if fuzz.partial_ratio(gameType.lower(), "custom game") >= 80:
            filteredNames.append(names[idx])
            filteredCodes.append(codes[idx])
    return filteredNames, filteredCodes

def replaceMapNames(names, threshold=80):
    for i, name in enumerate(names):
        if name.strip().lower() == "il":
            names[i] = "Ilios"
            continue
        bestMatch, highestScore = None, 0
        for mapName in overwatchMaps:
            score = fuzz.ratio(name.lower(), mapName.lower())
            if score > highestScore:
                highestScore, bestMatch = score, mapName
        if highestScore >= threshold:
            names[i] = bestMatch
    return names

def formatMessage(names, codes, title):
    message = f"{title}\n"
    for i in range(len(names) - 1, -1, -1):
        message += f"{names[i]}: {codes[i]}\n"
    return message

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botClient.tree.command(name="getcodes", description="Extracts replays from OW2 screenshot")
async def getcodes(interaction: discord.Interaction, name: str, attachment: discord.Attachment):
    await interaction.response.defer()
    img = resizeImageFromURL(attachment.url)
    croppedImages = cropImageAndSave(img, cropAreas, moveDownSteps, numRows)
    names, codes, types = categorizeText(croppedImages)
    names, codes = filterCustomGames(names, codes, types)
    names = replaceMapNames(names)
    names = cleanText(names)
    codes = cleanText(codes)
    codes = [correctCodes(code) for code in codes]
    finalMessage = formatMessage(names, codes, name)
    await interaction.followup.send(finalMessage)
    os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botClient.tree.command(name="getcodesraw", description="Extracts replays from OW2 screenshot, shows them only to you")
async def getcodesraw(interaction: discord.Interaction, attachment: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    img = resizeImageFromURL(attachment.url)
    croppedImages = cropImageAndSave(img, cropAreas, moveDownSteps, numRows)
    names, codes, types = categorizeText(croppedImages)
    names, codes = filterCustomGames(names, codes, types)
    names = replaceMapNames(names)
    names = cleanText(names)
    codes = cleanText(codes)
    codes = [correctCodes(code) for code in codes]
    finalMessage = formatMessage(names, codes, '')
    await interaction.followup.send(finalMessage)
    os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install
@botClient.tree.command(name="feedback", description="sends feedback form link")
async def feedback(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("https://forms.gle/esXC72V6hGznYGmu9")
    os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

botClient.run("token")
