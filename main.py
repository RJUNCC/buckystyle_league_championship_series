import os
os.system('uv run scripts/process.py')
os.system('uv run discord_bot/cogs/send_images.py')