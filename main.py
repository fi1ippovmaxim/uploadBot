import datetime
import decimal
import os
import random
import re
import string

import pytesseract as pytesseract
import requests
import telebot
from PIL import Image, ImageDraw
from pony.orm import *
from telebot import TeleBot

API_TOKEN = '5376696497:AAEm3Sei-8FXw7JFbWJYM6omw7shlypS03g'
bot: TeleBot = telebot.TeleBot(API_TOKEN)

db = Database()
db.bind(provider='sqlite', filename='database.sqlite', create_db=True)


class PhotoUpload(db.Entity):
    id = PrimaryKey(int, auto=True)
    date_upload = Required(datetime.datetime)
    link = Required(str)
    filename = Required(str)
    geo = Optional(str, default='')
    desc = Optional(str, default='')


def up_photo(img_path):
    i = Image.open(img_path)
    new_n = ''.join(
        [str(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)) for _
         in range(8)]) + ".png"
    i = i.convert("RGB")
    i.save(new_n)
    i.close()
    f = open(new_n, 'rb')
    resp = requests.post('https://telegra.ph/upload', files={'file': ('file', f, 'image/png')},).json()
    lnk = "https://telegra.ph" + resp[0]['src']
    f.close()
    os.remove(new_n)
    return lnk


pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'


def get_coordinates(path):
    img = Image.open(path)
    width = img.size[0]  # Определяем ширину
    height = img.size[1]  # Определяем высоту
    img = img.crop((4, height * 0.9, width // 3, height))
    draw = ImageDraw.Draw(img)  # Создаем инструмент для рисования
    width = img.size[0]  # Определяем ширину
    height = img.size[1]  # Определяем высоту
    pix = img.load()  # Выгружаем значения пикселей
    for x in range(width - 1):
        for y in range(height - 1):
            r = pix[x, y][0]  # узнаём значение красного цвета пикселя
            g = pix[x, y][1]  # зелёного
            b = pix[x, y][2]  # синего
            sr = 0 if (r + g + b) / 3 < 120 else 255  # среднее значение
            draw.point((x, y), (sr, sr, sr))
    s = pytesseract.image_to_string(img, lang='rus').split("\n")
    while "р" not in s[0] and len(s) > 0:
        del (s[0])
    p = '[\d]*[.][\d]+'
    a, b = 0.0, 0.0
    if re.search(p, s[0]) is not None:
        for catch in re.finditer(p, s[0]):
            a = catch[0]
    else:
        a = 0.0

    if re.search(p, s[1]) is not None:
        for catch in re.finditer(p, s[1]):
            b = catch[0]
    else:
        b = 0.0
    a, b = decimal.Decimal(a), decimal.Decimal(b)
    return str(a) + "," + str(b)


@db_session
def one_pic(img_path):
    dt = datetime.datetime.now()
    lnk = up_photo(img_path)
    fn = img_path.replace('\\', '/').split('/')[-1]
    c = PhotoUpload(date_upload=dt, filename=fn, link=lnk)
    try:
        coords = get_coordinates(img_path)
        if int(coords.split(',')[0].split('.')[0]) and int(coords.split(',')[1].split('.')[0]):
            c.geo = coords
    except:
        coords = '0.0,0.0'
    commit()
    return lnk, coords


@db_session
def search(lnk):
    c = PhotoUpload.get(link=lnk)
    if c:
        return c.filename
    else:
        return 0


@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id not in [951054728, 724068144, 307695119, 5394491066, 951054728, 5212085288]:
        return
    bot.reply_to(message, "Hi! Send me photo and get link!")


@bot.message_handler(commands=['search'])
def search_by_link(message):
    if message.chat.id not in [951054728, 724068144, 307695119, 5394491066, 951054728, 5212085288]:
        return
    photo_path = search(message.text.split()[1])
    if photo_path:
        bot.send_photo(message.chat.id, open("up_f/" + str(photo_path), 'rb'))
    else:
        bot.send_message(message.chat.id, "Фото не найдено")


@bot.message_handler(content_types=['photo'])
def echo_message(message):
    if message.chat.id not in [951054728, 724068144, 307695119, 5394491066, 951054728, 5212085288]:
        return
    fileID = message.photo[-1].file_id
    filename = "up_f/" + ''.join(
        [str(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)) for _
         in range(18)]) + ".jpg"
    file_info = bot.get_file(fileID)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(filename, 'wb') as new_file:
        new_file.write(downloaded_file)
    i = one_pic(filename)
    bot.reply_to(message, "Ссылка:\n" + i[0] + (
        "\nКоординаты:\n\n" + i[1] if int(i[1].split(',')[0].split('.')[0]) and int(
            i[1].split(',')[1].split('.')[0]) else ''), disable_web_page_preview=True)


db.generate_mapping(create_tables=True)

bot.infinity_polling()
