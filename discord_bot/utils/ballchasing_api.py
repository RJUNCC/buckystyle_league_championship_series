import aiohttp
import os

async def fetch_group_stats(group_id: str):
    headers = {"Authorization": os.getenv("TOKEN")}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://ballchasing.com/api/groups/{group_id}",
            headers=headers
        ) as response:
            if response.status != 200:
                raise ValueError(f"API Error: {await response.text()}")
            return await response.json()
