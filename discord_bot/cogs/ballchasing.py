import discord
from utils.ballchasing_api import fetch_group_stats
from models.player import Player

class BallchasingCog(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
            
        if "ballchasing.com/groups/" in message.content:
            group_id = message.content.split("/groups/")[-1]
            stats = await fetch_group_stats(group_id)
            
            for player in stats["players"]:
                await Player.update_stats(
                    player["id"], 
                    {
                        "mmr": player["mmr"],
                        "goals": player["stats"]["core"]["goals"],
                        "saves": player["stats"]["core"]["saves"],
                        "assists": player["stats"]["core"]["assists"]
                    }
                )
            await message.channel.send("Stats updated!")

    @discord.slash_command()
    async def stats(self, ctx: discord.ApplicationContext, player: discord.Member):
        data = await Player.collection.find_one({"_id": player.id})
        if data:
            embed = discord.Embed(title=f"{player.display_name}'s Stats")
            embed.add_field(name="MMR", value=data["stats"]["mmr"])
            embed.add_field(name="Goals", value=data["stats"]["goals"])
            await ctx.respond(embed=embed)
