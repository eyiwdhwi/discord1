import discord
import sys
print("Python version:", sys.version)
from discord.ext import commands
import json
import os
import requests
import random
import string
from discord.ext.commands import BucketType, CommandOnCooldown, CommandNotFound
import y  # Your third bot module
import threading
from dotenv import load_dotenv
load_dotenv()
try:
    import audioop
    print("audioop module is available")
except ModuleNotFoundError:
    print("audioop module NOT found")

# === CONFIG ===
TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_KEY = '376aa4740363494a8f9eb7d98c99f6c5685479'
OWNER_ID = 942375690009985045
DATA_FILE = 'data.json'
ADMIN_LOG_FILE = 'admins.txt'

# === Setup bot ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# === Utility Functions ===
def get_random_text(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read {DATA_FILE}: {e}")
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def user_has_unverified_email(user_id):
    if not os.path.exists(ADMIN_LOG_FILE):
        return False
    with open(ADMIN_LOG_FILE, 'r') as f:
        return any(line.strip().endswith(f":{user_id}") for line in f)

def buy_short_lived_email(user_id):
    try:
        response = requests.get(
            'https://gapi.hotmail007.com/api/mail/getMail',
            params={
                'clientKey': CLIENT_KEY,
                'mailType': 'hotmail',
                'quantity': 1
            }
        )
        res = response.json()
        print("DEBUG API response:", res)  # Optional: for debugging

        if res.get("code") == 0 and res.get("data"):
            email_entry = res["data"][0]

            # Handle both possible formats: string or dict
            if isinstance(email_entry, str):
                parts = email_entry.split(":")
                if len(parts) < 2:
                    return {'success': False, 'error': 'Malformed email entry from API.'}
                email = parts[0]
                password = parts[1]
            elif isinstance(email_entry, dict):
                email = email_entry.get("mail")
                password = email_entry.get("password")
            else:
                return {'success': False, 'error': 'Unexpected data format from API.'}

            if not email or not password:
                return {'success': False, 'error': 'Email or password missing in API response.'}

            with open(ADMIN_LOG_FILE, 'a') as f:
                f.write(f"{email}:{password}:{user_id}\n")

            return {'success': True, 'email': email, 'password': password}
        else:
            return {'success': False, 'error': res.get("msg", "Unknown error")}

    except Exception as e:
        return {'success': False, 'error': str(e)}

# === Events ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print("🧠 Loaded commands:", [command.name for command in bot.commands])

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandOnCooldown):
        await ctx.send(f"⏳ Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        raise error

# === Commands ===
@bot.command()
async def coins(ctx):
    user_id = str(ctx.author.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {'coins': 0}
        save_data(data)
    await ctx.send(f'🪙 You have **{data[user_id]["coins"]}** coins.')

@bot.command()
async def add(ctx, member: discord.Member = None, amount: int = 0):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ You are not allowed to use this command.")
    if member is None or amount <= 0:
        return await ctx.send("❌ Usage: `!add @user amount`")

    user_id = str(member.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {'coins': 0}
    data[user_id]['coins'] += amount
    save_data(data)
    await ctx.send(f'✅ Added {amount} coins to {member.mention}.')

@bot.command()
@commands.cooldown(rate=1, per=10, type=BucketType.user)
async def mail(ctx):
    user_id = str(ctx.author.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {'coins': 0}
        save_data(data)

    if user_has_unverified_email(user_id):
        return await ctx.send("❌ You already have an unverified email. Please verify it first using `!verify`.")

    if data[user_id]['coins'] < 1:
        return await ctx.send("❌ You do not have enough coins. Each email costs 1 coin.")

    wait_msg = await ctx.send("⏳ Getting an email, please wait...")
    result = buy_short_lived_email(user_id)

    if result['success'] and result.get('email'):
        data[user_id]['coins'] -= 1
        save_data(data)

        email = result['email']
        display = get_random_text(8)
        username = get_random_text(8)

        await wait_msg.edit(content=(
            f"📧 Email: `{email}`\n"
            f"🔑 Password: `eyad0707`\n"
            f"🧾 Display Name: `{display}`\n"
            f"🆔 Username: `{username}`\n"
            f"✅ **تم حفظ الإيميل في ملفك الخاص**"
        ))
    else:
        await wait_msg.edit(content=f"no stock❌ check: https://discord.com/channels/1398036195665117289/1398195927189164054")

# Run the bot

def run_bot_thread(bot_func, name):
    try:
        print(f"Starting bot thread: {name}")
        bot_func()
    except Exception as e:
        print(f"Error in {name} bot thread: {e}")

# Start other bots in daemon threads so they exit when main thread exits
threading.Thread(target=run_bot_thread, args=(y.run_bot, 'y'), daemon=True).start()

bot.run(TOKEN)
