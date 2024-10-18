import discord
from cv2 import Mat
from discord import app_commands
import cv2
import numpy as np
import requests
from io import BytesIO
from PIL import Image
import pytesseract
from typing import Sequence
import os

bot_token: str = 'token'
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
botIntents = discord.Intents.default()
botClient = discord.Client(intents=botIntents)
botCommandTree = app_commands.CommandTree(botClient)
map_name_list = [
    "Antarctic Peninsula", "Busan", "Ilios", "Lijiang Tower", "Nepal", "Oasis", "Samoa", "Circuit Royal",
    "Dorado", "Havana", "Junkertown", "Rialto", "Route 66", "Shambali Monastery", "Watchpoint: Gibraltar",
    "New Junk City", "Suravasa", "Blizzard World", "Eichenwalde", "Hollywood", "King's Row", "Midtown",
    "Numbani", "Paraíso", "Colosseo", "Esperança", "New Queen Street", "Runasapi", "Hanaoka", "Throne of Anubis"
]


def save_cropped_image(img: Mat | np.ndarray[np.any, np.dtype] | np.ndarray, row_number: int) -> None:
    file_name = f"cropped_row_{row_number}.png"
    cv2.imwrite(file_name, img)
    print(f"Saved cropped row as {file_name}")


def find_box(mask: Mat | np.ndarray) -> Sequence[int] or None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        foo = max(contours, key=cv2.contourArea)
        return cv2.boundingRect(foo)
    return None


def find_orange_percent(mask: Mat | np.ndarray) -> int:
    return (cv2.countNonZero(mask) / mask.size) * 100


def process_image(url: str) -> tuple[list[str], list[str]]:
    response = requests.get(url)
    print("got source image")

    source_image = Image.open(BytesIO(response.content))
    source_image = source_image.resize((1920, 1080), Image.Resampling.LANCZOS)
    print("resized source image.")
    image = cv2.cvtColor(np.array(source_image), cv2.COLOR_RGB2BGR) # TODO np.array DOES NOT TAKE IMAGEFILE AS A TYPE SEE DOC: https://numpy.org/doc/stable/reference/generated/numpy.array.html
    print("converted image colorspace to cv.")

    template = cv2.imread('share.png')
    if template is None:
        return [], []

    print("got share location temp ")

    image_grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    template_grey = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(image_grey, template_grey, cv2.TM_CCOEFF_NORMED)
    icon_height, icon_width = template_grey.shape
    locations = np.where(result >= 0.8)
    print(f"found {len(locations[0])} locations")
    print(f"locations: {locations}")

    if len(locations[0]) == 0:
        print("couldn't find share icon in image")
        return [], []

    lower_orange, upper_orange = np.array([5, 100, 100]), np.array([20, 255, 255])
    relative_x, relative_y, relative_width, relative_height, count = None, None, None, None, 1
    row_text_list, code_text_list = [], []

    for pt in zip(*locations[::-1]):
        print(pt)
        row = image[max(0, pt[1] - 15):min(image.shape[0], pt[1] + icon_height + 25), :]
        save_cropped_image(row, count)
        hue_saturation_value_row = cv2.cvtColor(row, cv2.COLOR_BGR2HSV)
        mask_orange = cv2.inRange(hue_saturation_value_row, lower_orange, upper_orange)
        print(f"row {count}")

        if count == 1:
            x, y, w, h = find_box(mask_orange)
            print(f"cut box for row: {(x, y, w, h)}")
            if x is not None:
                relative_x, relative_y, relative_width, relative_height = x / icon_width, y / icon_height, w / icon_width, h / icon_height
                box_orange = row[y:y + h, x:x + w]
                code_text = pytesseract.image_to_string(box_orange)
                code_text_list.append(code_text)
                print(f"code text: {code_text}")

        else:
            if relative_x is not None:
                x, y, w, h = int(relative_x * icon_width), int(relative_y * icon_height), int(relative_width * icon_width), int(relative_height * icon_height)
                cropped = row[y:y + h, x:x + w]
                orange_percent = find_orange_percent(
                    cv2.inRange(cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV), lower_orange, upper_orange))
                print(f"orangeP for {count}: {orange_percent}%")
                if orange_percent >= 70:
                    code_text = pytesseract.image_to_string(cropped)
                    code_text_list.append(code_text)
                    print(f"{count} code {code_text}")

        row_text = pytesseract.image_to_string(row)
        row_text_list.append(row_text)
        print(f"{count} text {row_text}")
        count += 1

    print("done")
    return row_text_list, code_text_list


def format_text(title: str, row_text_list: list[str], code_text_list: list[str]) -> str:
    formatted_text = f"{title}\n"
    row_count = min(len(row_text_list), 7)
    for i in range(row_count, 0, -1):
        formatted_text += f"{row_text_list[i - 1]}: {code_text_list[i - 1]}\n"
    print("text formatted")
    return formatted_text


def check_map(row_text_list: list[str]) -> list[str]:
    for i in range(len(row_text_list)):
        for map_name in map_name_list:
            if map_name.lower() in row_text_list[i].lower():
                row_text_list[i] = map_name
                print(f"'{map_name}'in {i + 1}.")
                break
    return row_text_list


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
async def get_codes(interaction: discord.Interaction, name: str, attachment: discord.Attachment):
    try:
        await interaction.response.defer()
        print(f"received cmd getcodes, {name}, {attachment.filename}")
        img_url = attachment.url
        row_text_list, code_text_list = process_image(img_url)
        for i, (rT, cT) in enumerate(zip(row_text_list, code_text_list), start=1):
            print(f"row {i}, text from tess: {rT}")
            print(f"code {i}, text from tess: {cT}")
        filtered = [(row, code) for row, code in zip(row_text_list, code_text_list) if 'CUSTOM' in row.upper()]
        row_text_list, code_text_list = zip(*filtered) if filtered else ([], [])
        row_text_list = check_map(list(row_text_list))
        formatted = format_text(name, row_text_list, code_text_list)
        await interaction.followup.send(f"```\n{formatted}\n```")
        print("sent")
    except Exception as e:
        await interaction.followup.send(f"error {str(e)}")
        print(f"err {e}")

botClient.run(bot_token)
