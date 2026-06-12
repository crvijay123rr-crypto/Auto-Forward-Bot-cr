import re
import asyncio
from database import db
from config import temp
from .test import CLIENT, start_clone_bot
from translation import Translation
from pyropatch.utils import unpack_new_file_id
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CLIENT = CLIENT()

# course_hub2bot buttons updated
COMPLETED_BTN = InlineKeyboardMarkup(
   [
      [InlineKeyboardButton('⚡ Support', url='https://t.me/course_hub2bot')],
      [InlineKeyboardButton('📢 Updates', url='https://t.me/course_hub2bot')]
   ]
)

CANCEL_BTN = InlineKeyboardMarkup([[InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')]])

@Client.on_message(filters.command("unequify") & filters.private)
async def unequify(client, message):
   user_id = message.from_user.id
   temp.CANCEL[user_id] = False
   
   if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
      return await message.reply("**please wait until previous task complete**")
      
   _bot = await db.get_bot(user_id)
   if not _bot or _bot['is_bot']:
      return await message.reply("<b>Need userbot to do this process. Please add a userbot using /settings</b>")
      
   target = await client.ask(user_id, text="**Forward the last message from target chat or send last message link.**\n/cancel - `cancel this process`")
   if target.text and target.text.startswith("/"):
      return await message.reply("**process cancelled !**")
      
   # Link Parsing
   if target.text:
      regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
      match = regex.match(target.text.replace("?single", ""))
      if not match:
         return await message.reply('**Invalid link**')
      chat_id = match.group(4)
      last_msg_id = int(match.group(5))
      if chat_id.isnumeric():
         chat_id = int("-100" + chat_id)
   elif target.forward_from_chat:
      chat_id = target.forward_from_chat.username or target.forward_from_chat.id
   else:
      return await message.reply_text("**invalid input!**")

   confirm = await client.ask(user_id, text="**send /yes to start the process and /no to cancel this process**")
   if confirm.text.lower() != '/yes':
      return await confirm.reply("**process cancelled !**")
      
   sts = await confirm.reply("`processing..`")
   try:
      # course_hub2bot connection
      bot = await start_clone_bot(CLIENT.client(_bot))
   except Exception as e:
      return await sts.edit(f"**Error connecting course_hub2bot:** `{e}`")
      
   try:
       # Admin check
       k = await bot.send_message(chat_id, text="testing")
       await k.delete()
   except Exception as e:
       await sts.edit(f"**Please make your course_hub2bot admin in target chat with delete permissions.**")
       return await bot.stop()

   MESSAGES = []
   DUPLICATE = []
   total = deleted = 0
   temp.lock[user_id] = True
   
   try:
     await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
     
     async for message in bot.search_messages(chat_id=chat_id, filter="document"):
        if temp.CANCEL.get(user_id) == True:
           await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴄᴀɴᴄᴇʟʟᴇᴅ"), reply_markup=COMPLETED_BTN)
           return await bot.stop()
           
        file = message.document
        # Unpacking file_id
        file_id = unpack_new_file_id(file.file_id) 
        
        if file_id in MESSAGES:
           DUPLICATE.append(message.id)
        else:
           MESSAGES.append(file_id)
           
        total += 1
        if total % 100 == 0: # Updated frequency for better UI
           await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
           
        if len(DUPLICATE) >= 50:
           await bot.delete_messages(chat_id, DUPLICATE)
           deleted += len(DUPLICATE)
           await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
           DUPLICATE = []
           
     if DUPLICATE:
        await bot.delete_messages(chat_id, DUPLICATE)
        deleted += len(DUPLICATE)
        
   except Exception as e:
       temp.lock[user_id] = False 
       await sts.edit(f"**ERROR in course_hub2bot process**\n`{e}`")
       return await bot.stop()
       
   temp.lock[user_id] = False
   await sts.edit(Translation.DUPLICATE_TEXT.format(total, deleted, "ᴄᴏᴍᴘʟᴇᴛᴇᴅ"), reply_markup=COMPLETED_BTN)
   await bot.stop()
   
