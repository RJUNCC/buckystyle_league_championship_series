import os
os.system("uv run --with matplotlib scripts/process.py")
os.system('uv run discord_bot/cogs/send_images.py')