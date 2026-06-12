import re
import asyncio 
from .utils import STS
from database import db
from config import temp 
from translation import Translation
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait 
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, ChannelPrivate
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
 
#===================Run Function===================#
@Client.on_message(filters.private & filters.command(["fwd", "forward"]))
async def run(bot, message):
    buttons = []
    btn_data = {}
    user_id = message.from_user.id
    _bot = await db.get_bot(user_id)
    if not _bot:
        return await message.reply("<code>You didn't added any bot. Please add a bot using /settings !</code>")
    
    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text("Please set a target channel in /settings before forwarding.")
    
    # 1. Target Channel Selection
    if len(channels) > 1:
        for channel in channels:
            buttons.append([KeyboardButton(f"{channel['title']}")])
            btn_data[channel['title']] = channel['chat_id']
        buttons.append([KeyboardButton("cancel")]) 
        _toid = await bot.ask(message.chat.id, Translation.TO_MSG.format(_bot['name'], _bot['username']), reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))
        if _toid.text.lower() in ['cancel', '/cancel']:
            return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
        to_title = _toid.text
        toid = btn_data.get(to_title)
        if not toid:
            return await message.reply_text("Wrong channel chosen!", reply_markup=ReplyKeyboardRemove())
    else:
        toid = channels[0]['chat_id']
        to_title = channels[0]['title']

    # 2. Source Input
    fromid = await bot.ask(message.chat.id, Translation.FROM_MSG, reply_markup=ReplyKeyboardRemove())
    if fromid.text and fromid.text.startswith('/'):
        return await message.reply(Translation.CANCEL)

    continuous = False
    
    # Validation: Saved Messages
    if fromid.text and fromid.text.lower() in ["me", "saved"]:
        if _bot.get('is_bot'):
            return await message.reply("<b>You cannot forward from Saved Messages using a Bot. Please add a Userbot session via /settings.</b>")
        chat_id, title = "me", "Saved Messages"
        # Mode Selection
        mode_msg = await bot.ask(message.chat.id, Translation.SAVED_MSG_MODE)
        continuous = "live" in mode_msg.text.lower() or "2" in mode_msg.text
        last_msg_id = 1000000 if continuous else 500 # Default limit

    # Validation: Link Input
    elif fromid.text and not fromid.forward_date:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(fromid.text.replace("?single", ""))
        if not match:
            return await message.reply('Invalid link format.')
        chat_id, last_msg_id = match.group(4), int(match.group(5))
        if chat_id.isnumeric(): chat_id = int("-100" + chat_id)
        title = "Source Chat"

    # Validation: Forwarded Message
    elif fromid.forward_from_chat:
        last_msg_id = fromid.forward_from_message_id
        chat_id = fromid.forward_from_chat.username or fromid.forward_from_chat.id
        title = fromid.forward_from_chat.title
    else:
        return await message.reply_text("**Invalid source provided!**")

    # 3. Skip Number Validation
    skipno = await bot.ask(message.chat.id, Translation.SKIP_MSG)
    if not skipno.text.isdigit() and skipno.text != '0':
        return await message.reply("Invalid number. Please enter a valid digit.")

    forward_id = f"{user_id}-{skipno.id}"
    
    # 4. Final Confirmation
    await message.reply_text(
        text=Translation.DOUBLE_CHECK.format(botname=_bot['name'], botuname=_bot['username'], from_chat=title, to_chat=to_title, skip=skipno.text),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('Yes', callback_data=f"start_public_{forward_id}"),
            InlineKeyboardButton('No', callback_data="close_btn")
        ]])
    )
    STS(forward_id).store(chat_id, toid, int(skipno.text), int(last_msg_id), continuous=continuous)
 
