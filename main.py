import asyncio
import os
import logging
import time
import aiohttp
from aiohttp import web
from pyrogram import idle
from bot import Bot

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

START_TIME = time.time()

def get_uptime():
    elapsed = time.time() - START_TIME
    days, rem = divmod(elapsed, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

async def web_server():
    async def handle(request):
        uptime = get_uptime()
        # course_hub2bot Branding
        html_content = f"""
        <html><body>
            <h1>course_hub2bot is Running</h1>
            <p>Status: Active</p>
            <p>Uptime: {uptime}</p>
        </body></html>
        """
        return web.Response(text=html_content, content_type='text/html')

    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def ping_server():
    # Ping URL lein (External URL environment variable se, agar ho)
    url = os.environ.get('RENDER_EXTERNAL_URL', 'http://127.0.0.1:8080')
    while True:
        await asyncio.sleep(300) 
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    logging.info(f"Self-ping to {url}: Status {resp.status}")
        except Exception as e:
            logging.error(f"Self-ping failed: {e}")

async def main():
    bot = Bot()
    await bot.start()
    
    # Web server aur ping start karein
    await web_server()
    asyncio.create_task(ping_server())

    logging.info("--- course_hub2bot Started Successfully ---")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot Stopped!")
        
