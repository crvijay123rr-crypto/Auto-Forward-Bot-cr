import os
import sys 
import math
import time
import asyncio 
import logging
import re # regex ke liye
from .utils import STS
from database import db 
from .test import CLIENT , start_clone_bot
from config import Config, temp
from translation import Translation
from pyrogram import Client, filters 
from pyrogram.errors import FloodWait, MessageNotModified, RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Translation.TEXT

# --- FUNCTION: Caption se Topic nikalne ke liye ---
def get_topic_from_caption(caption):
    if not caption: return None
    match = re.search(r"Topic:\s*(.*)", caption, re.IGNORECASE)
    return match.group(1).strip() if match else None

@Client.on_callback_query(filters.regex(r'^start_public'))
async def pub_(bot, message):
    user = message.from_user.id
    temp.CANCEL[user] = False
    frwd_id = message.data.split("_")[2]
    if temp.lock.get(user) and str(temp.lock.get(user))=="True":
      return await message.answer("please wait until previous task complete", show_alert=True)
    sts = STS(frwd_id)
    if not sts.verify():
      await message.answer("your are clicking on my old button", show_alert=True)
      return await message.message.delete()
    
    # Task shuru hone se pehle purane topics clear karein
    await db.clear_topics(user)
    
    i = sts.get(full=True)
    if i.TO in temp.IS_FRWD_CHAT:
      return await message.answer("In Target chat a task is progressing. please wait until task complete", show_alert=True)
    m = await msg_edit(message.message, "<code>verifying your data's, please wait.</code>")
    _bot, caption, forward_tag, data, protect, button = await sts.get_data(user)
    if not _bot:
      return await msg_edit(m, "<code>You didn't added any bot. Please add a bot using /settings !</code>", wait=True)
    try:
      client = await start_clone_bot(CLIENT.client(_bot))
    except Exception as e:  
      return await m.edit(e)
    
    await msg_edit(m, "<code>processing..</code>")
    try: 
       await client.get_messages(sts.get("FROM"), 1)
    except:
       await msg_edit(m, f"**Source chat may be a private channel / group. Use userbot**", retry_btn(frwd_id), True)
       return await stop(client, user)
    
    temp.forwardings += 1
    await db.add_frwd(user)
    await send(client, user, "<b>ғᴏʀᴡᴀʀᴅɪɴɢ sᴛᴀʀᴛᴇᴅ <a href=https://t.me/dev_gagan>Dev Gagan</a></b>")
    sts.add(time=True)
    sleep = 1 if _bot['is_bot'] else 10
    await msg_edit(m, "<code>Processing...</code>") 
    temp.IS_FRWD_CHAT.append(i.TO)
    temp.lock[user] = locked = True
    
    if locked:
        try:
          MSG = []
          pling=0
          await edit(m, 'Progressing', 10, sts)
          is_continuous = getattr(sts, 'continuous', False)

          async for message in client.iter_messages(client, chat_id=sts.get('FROM'), limit=int(sts.get('limit')), offset=int(sts.get('skip')) if sts.get('skip') else 0, continuous=is_continuous):
                if await is_cancelled(client, user, m, sts): return
                
                # --- TOPIC DETECTION LOGIC ---
                cap = message.caption.html if message.caption else ""
                topic_name = get_topic_from_caption(cap)
                if topic_name:
                    # Agar naya topic hai toh DB mein save karein
                    chat_id_clean = str(sts.get('TO')).replace("-100", "")
                    link = f"https://t.me/c/{chat_id_clean}/{message.id}"
                    await db.add_topic(user, topic_name, link)
                # -----------------------------

                if pling %20 == 0: await edit(m, 'Progressing', 10, sts)
                pling += 1
                sts.add('fetched')
                if message == "DUPLICATE": sts.add('duplicate'); continue 
                elif message == "FILTERED": sts.add('filtered'); continue 
                if message.empty or message.service: sts.add('deleted'); continue
                
                if forward_tag:
                   MSG.append(message.id)
                   notcompleted = len(MSG)
                   if (notcompleted >= 100 or (sts.get('total') - sts.get('fetched')) <= 100): 
                      await forward(client, MSG, m, sts, protect)
                      sts.add('total_files', notcompleted)
                      await asyncio.sleep(10); MSG = []
                else:
                   new_caption = custom_caption(message, caption)
                   details = {"msg_id": message.id, "media": media(message), "caption": new_caption, 'button': button, "protect": protect}
                   await copy(client, details, m, sts)
                   sts.add('total_files')
                   await asyncio.sleep(sleep) 
        except Exception as e:
            await msg_edit(m, f'<b>ERROR:</b>\n<code>{e}</code>', wait=True)
            temp.IS_FRWD_CHAT.remove(sts.TO)
            return await stop(client, user)
        
        # --- FORWARDING COMPLETE & SUMMARY ---
        temp.IS_FRWD_CHAT.remove(sts.TO)
        
        # Summary Send Karein
        topics = await db.get_topics(user)
        if topics:
            keyboard = []
            for t in topics:
                keyboard.append([InlineKeyboardButton(f"📚 {t['name']}", url=t['link'])])
            await client.send_message(user, "<b>📋 TOPIC SUMMARY:</b>", reply_markup=InlineKeyboardMarkup(keyboard))
        
        await send(client, user, "<b>🎉 ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ 🥀</b>")
        await edit(m, 'Completed', "completed", sts) 
        await stop(client, user)

# ... (baaki saare functions: copy, forward, edit, is_cancelled, stop, send, etc. waise hi rehne dein)
