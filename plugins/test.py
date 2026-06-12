import os
import re 
import sys
import asyncio 
import logging 
from database import db 
from config import Config, temp
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)]\[buttonurl:/{0,2}(.+?)(:same)?])")
BOT_TOKEN_TEXT = "<b>1) create a bot using @BotFather\n2) Then you will get a message with bot token\n3) Forward that message to me</b>"
SESSION_STRING_SIZE = 351

async def start_clone_bot(FwdBot):
   if not FwdBot.is_connected:
       await FwdBot.start()
   return FwdBot

class CLIENT: 
  def __init__(self):
     self.api_id = Config.API_ID
     self.api_hash = Config.API_HASH
    
  def client(self, data, is_session=False):
     if is_session:
        return Client(f"USER_{data[:10]}", self.api_id, self.api_hash, session_string=data)
     return Client(f"BOT_{data[:10]}", self.api_id, self.api_hash, bot_token=data, in_memory=True)
  
  async def add_bot(self, bot, message):
     user_id = message.from_user.id
     msg = await bot.ask(chat_id=user_id, text=BOT_TOKEN_TEXT)
     if msg.text == '/cancel':
        return await msg.reply('<b>Process cancelled!</b>')
     if not msg.forward_date:
       return await msg.reply_text("<b>This is not a forwarded message from BotFather.</b>")
     
     bot_token = re.findall(r'\d[0-9]{8,10}:[0-9A-Za-z_-]{35}', msg.text)
     if not bot_token:
       return await msg.reply_text("<b>No bot token found in that message.</b>")
     
     try:
       client = self.client(bot_token[0], False)
       await client.start()
       me = await client.get_me()
       details = {
         'id': me.id, 'is_bot': True, 'user_id': user_id,
         'name': me.first_name, 'token': bot_token[0], 'username': me.username 
       }
       await db.add_bot(details)
       await client.stop()
       return True
     except Exception as e:
       await msg.reply_text(f"<b>BOT ERROR:</b> `{e}`")
    
  async def add_session(self, bot, message):
     user_id = message.from_user.id
     await bot.send_message(user_id, "<b>⚠️ DISCLAIMER: Use your session at your own risk.</b>")
     msg = await bot.ask(user_id, "<b>Send your Pyrogram session string:</b>")
     if msg.text == '/cancel':
        return await msg.reply('<b>Process cancelled!</b>')
     if len(msg.text) < SESSION_STRING_SIZE:
        return await msg.reply('<b>Invalid session string.</b>')
     try:
       client = self.client(msg.text, True)
       await client.start()
       me = await client.get_me()
       details = {
         'id': me.id, 'is_bot': False, 'user_id': user_id,
         'name': me.first_name, 'session': msg.text, 'username': me.username
       }
       await db.add_bot(details)
       await client.stop()
       return True
     except Exception as e:
       await msg.reply_text(f"<b>USERBOT ERROR:</b> `{e}`")
    
@Client.on_message(filters.private & filters.command('reset'))
async def reset_settings(bot, m):
   default = await db.get_configs("01") # Assuming "01" is default template
   await db.update_configs(m.from_user.id, default)
   await m.reply("Successfully settings reset! ✔️")

async def get_configs(user_id):
  return await db.get_configs(user_id)
                          
async def update_configs(user_id, key, value):
  current = await db.get_configs(user_id)
  if key in ['caption', 'duplicate', 'db_uri', 'forward_tag', 'protect', 'file_size', 'size_limit', 'extension', 'keywords', 'button']:
     current[key] = value
  else: 
     current['filters'][key] = value
  await db.update_configs(user_id, current)
    
def parse_buttons(text, markup=True):
    buttons = []
    for match in BTN_URL_REGEX.finditer(text):
        if len(buttons) == 0 or match.group(4):
            buttons.append([InlineKeyboardButton(match.group(2), url=match.group(3).replace(" ", ""))])
        else:
            buttons[-1].append(InlineKeyboardButton(match.group(2), url=match.group(3).replace(" ", "")))
    return InlineKeyboardMarkup(buttons) if (markup and buttons) else buttons
   
