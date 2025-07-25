import discord
from discord.ext import commands
import asyncio
from imapclient import IMAPClient
import pyzmail
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('TOKEN')
imap_server = "imap.zmailservice.com"
imap_port = 143

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def verify(ctx):
    user_id = str(ctx.author.id)
    found = False
    email = None
    password = None
    user_line = None

    # Read admins.txt to find the matching line
    with open('admins.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            parts = line.strip().split(':')
            if len(parts) == 3 and parts[2] == user_id:
                email = parts[0]
                password = parts[1]
                user_line = line.strip()
                found = True
                break

    if not found:
        await ctx.send("❌ You don't have an email to verify.")
        return

    msg = await ctx.send("⏳ Waiting for verification link...")

    def check_for_verification():
        imap_obj = None

        # Try IMAP login up to 10 times, every 5 seconds
        for attempt in range(10):
            try:
                imap_obj = IMAPClient(imap_server, port=imap_port, ssl=False, use_uid=True)
                imap_obj.login(email, password)
                imap_obj.select_folder("INBOX")
                print("✅ IMAP login successful.")
                break
            except Exception as e:
                print(f"⚠️ Login attempt {attempt+1}/10 failed: {e}")
                time.sleep(5)
        else:
            print("❌ All login attempts failed.")
            return None

        seen_uids = set()

        # Check every 15s for up to 5 minutes (20 attempts)
        for _ in range(20):
            try:
                uids = imap_obj.search(['UNSEEN'])
                new_uids = [uid for uid in uids if uid not in seen_uids]

                # If any new messages, process them
                for uid in new_uids:
                    raw = imap_obj.fetch([uid], ['BODY[]', 'FLAGS'])
                    message = pyzmail.PyzMessage.factory(raw[uid][b'BODY[]'])

                    subject = message.get_subject()
                    sender = message.get_addresses('from')

                    if subject == "Verify Email Address for Discord" and sender and sender[0][1] == "noreply@discord.com":
                        if message.html_part:
                            html_body = message.html_part.get_payload().decode(message.html_part.charset)
                            soup = BeautifulSoup(html_body, 'html.parser')
                            links = [a['href'] for a in soup.find_all('a', href=True) if 'click.discord.com' in a['href']]

                            if len(links) >= 2:
                                imap_obj.add_flags(uid, [b'\\Seen'])
                                return links[1]

                    imap_obj.add_flags(uid, [b'\\Seen'])
                    seen_uids.add(uid)

                time.sleep(15)
            except Exception as e:
                print(f"⚠️ Email check error: {e}")
                time.sleep(10)

        return None

    loop = asyncio.get_event_loop()
    link = await loop.run_in_executor(None, check_for_verification)

    if link:
        await msg.edit(content=f"{link}")

        # ✅ Remove the user's line from admins.txt
        with open("admins.txt", "r") as f:
            lines = f.readlines()
        with open("admins.txt", "w") as f:
            for line in lines:
                if line.strip() != user_line:
                    f.write(line)
        print(f"✅ Removed line from admins.txt: {user_line}")

    else:
        await msg.edit(content="❌ No verification link found in time.")

# Run the bot
def run_bot():
    bot.run(TOKEN)
