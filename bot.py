import asyncio
import logging 
import logging.config
from database import db 
from config import Config  
from pyrogram import Client, __version__
from pyrogram.raw.all import layer 
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait 

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

class Bot(Client): 
    def __init__(self):
        super().__init__(
            Config.BOT_SESSION,
            api_hash=Config.API_HASH,
            api_id=Config.API_ID,
            plugins={"root": "plugins"},
            workers=50,
            bot_token=Config.BOT_TOKEN
        )
        self.log = logging

    async def start(self):
        await super().start()
        me = await self.get_me()
        
        self.id = me.id
        self.username = me.username
        self.first_name = me.first_name
        
        # Parse Mode HTML set karna hamesha safe rehta hai
        self.set_parse_mode(ParseMode.HTML)
        
        logging.info(f"{me.first_name} (v{__version__}) started on @{me.username}.")

        # Database check
        if "mongodb+srv://" not in Config.DATABASE_URI or "chhjgjkkjhkjhkjh" in Config.DATABASE_URI:
             logging.error("DATABASE_URI is not set or using default. Bot might not work.")
             return

        # Restart Notification
        text = "<b>๏[-ิ_•ิ]๏ bot restarted!</b>"
        try:
            success = failed = 0
            users = await db.get_all_frwd()
            # Users ko iterate karte waqt safe handling
            async for user in users:
               chat_id = user['user_id']
               try:
                  await self.send_message(chat_id, text)
                  success += 1
               except FloodWait as e:
                  await asyncio.sleep(e.value)
                  await self.send_message(chat_id, text)
                  success += 1
               except Exception:
                  failed += 1

            if (success + failed) != 0:
               await db.rmve_frwd(all=True)
               logging.info(f"Restart broadcast: {success} success, {failed} failed.")
        except Exception as e:
            logging.error(f"Error during bot start: {e}")

    async def stop(self, *args):
        await super().stop()
        logging.info(f"@{self.username} stopped.")
        
