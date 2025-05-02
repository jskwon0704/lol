
import discord
from discord.ext import commands
import random
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_profiles = {}

def generate_iv():
    return {stat: random.randint(10, 31) for stat in ["HP", "ATK", "DEF", "SPD"]}

def calculate_stat(iv, level):
    base = 40 if iv == 'HP' else 0
    return int((iv * level / 10) + level + base)
    return int((iv * level / 10) + level)

def exp_to_next_level(level):
    return int(50 + (level * 10) + (1.5 * (level ** 2)))

def get_pokemon_image(name):
    images = {
        "파이리": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/4.png",
        "야돈": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/79.png"
    }
    return images.get(name, "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/0.png")

class GameView(discord.ui.View):
    def __init__(self, user, message):
        super().__init__(timeout=None)
        self.user = user
        self.message = message

    @discord.ui.button(label="대표 포켓몬 설정", style=discord.ButtonStyle.primary)
    async def 대표설정(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("본인만 조작할 수 있습니다.", ephemeral=True)
            return
        roles = [role.name for role in interaction.user.roles]
        uid = str(interaction.user.id)
        if uid not in user_profiles:
            user_profiles[uid] = {"owned": {}, "main": None}
        valid = [r for r in roles if r != "@everyone"]
        if not valid:
            await interaction.response.send_message("보유한 포켓몬 역할이 없습니다.", ephemeral=True)
            return
        name = valid[0]
        if name not in user_profiles[uid]["owned"]:
            iv = generate_iv()
            user_profiles[uid]["owned"][name] = {
                "level": 1,
                "exp": 0,
                "next_exp": exp_to_next_level(1),
                "iv": iv,
                "max_hp": calculate_stat(iv["HP"], 1),
                "hp": calculate_stat(iv["HP"], 1)
            }
        user_profiles[uid]["main"] = name
        await interaction.response.edit_message(content=f"대표 포켓몬을 **{name}**(으)로 설정했습니다.", view=self)

    @discord.ui.button(label="사냥하기", style=discord.ButtonStyle.success)
    async def 사냥(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("본인만 조작할 수 있습니다.", ephemeral=True)
            return
        await interaction.response.edit_message(content="사냥터를 선택하세요.", view=HuntingView(self.user, self.message))

    @discord.ui.button(label="프로필 보기", style=discord.ButtonStyle.secondary)
    async def 프로필(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("본인만 조작할 수 있습니다.", ephemeral=True)
            return
        uid = str(interaction.user.id)
        if uid not in user_profiles or user_profiles[uid]["main"] is None:
            await interaction.response.edit_message(content="대표 포켓몬이 없습니다.", view=self)
            return
        mon = user_profiles[uid]["owned"][user_profiles[uid]["main"]]
        msg = f"📘 프로필\n대표: {user_profiles[uid]['main']}\nLv: {mon['level']} | EXP: {mon['exp']}/{mon['next_exp']}\nIV: {mon['iv']}\nHP: {mon['hp']}/{mon['max_hp']}"
        await interaction.response.edit_message(content=msg, view=self)

class HuntingView(discord.ui.View):
    def __init__(self, user, message):
        super().__init__(timeout=None)
        self.user = user
        self.message = message

    @discord.ui.button(label="사냥터 1", style=discord.ButtonStyle.primary)
    async def zone1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("본인만 조작할 수 있습니다.", ephemeral=True)
            return
        await start_battle(interaction, self.message)

class BattleView(discord.ui.View):
    def __init__(self, user, player, enemy, message):
        super().__init__(timeout=None)
        self.user = user
        self.player = player
        self.enemy = enemy
        self.message = message
        self.logs = []
        self.special_used = False

    def build_embed(self, action=""):
        embed = discord.Embed(title=f"{self.user.display_name}의 전투", color=discord.Color.orange())
        embed.add_field(name="플레이어", value=f"Lv{self.player['level']} | HP: {self.player['hp']}/{self.player['max_hp']}", inline=True)
        embed.add_field(name="적", value=f"Lv{self.enemy['level']} | HP: {self.enemy['hp']}/{self.enemy['max_hp']}", inline=True)
        if action:
            self.logs.append(action)
        if len(self.logs) > 3:
            self.logs = self.logs[-3:]
        embed.add_field(name="전투 로그", value="\n".join(self.logs) or "없음", inline=False)
        embed.set_thumbnail(url=get_pokemon_image(self.user_profiles_main()))
        embed.set_image(url=get_pokemon_image(self.enemy["name"]))
        return embed

    def user_profiles_main(self):
        uid = str(self.user.id)
        return user_profiles[uid]["main"] if uid in user_profiles else "파이리"

    def damage(self, base): return random.randint(base - 2, base + 2)

    async def end_battle(self, interaction):

    @discord.ui.button(label="기본기", style=discord.ButtonStyle.primary, row=0)
    async def basic(self, interaction: discord.Interaction, button: discord.ui.Button):
        dmg = self.damage(10)
        self.enemy["hp"] -= dmg
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await self.message.edit(embed=self.build_embed(f"기본기 → {dmg} 데미지"), view=self)

    @discord.ui.button(label="특수기", style=discord.ButtonStyle.danger, row=0)
    async def special(self, interaction: discord.Interaction, button: discord.ui.Button):
        if random.random() < 0.7:
            dmg = self.damage(20)
            self.enemy["hp"] -= dmg
            result = f"특수기 → {dmg} 데미지"
        else:
            result = "특수기 빗나감"
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await self.message.edit(embed=self.build_embed(result), view=self)

    @discord.ui.button(label="유틸기", style=discord.ButtonStyle.secondary, row=1)
    async def utility(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.enemy["iv"]["SPD"] = max(1, self.enemy["iv"]["SPD"] - 3)
        await self.message.edit(embed=self.build_embed("상대 SPD 감소"), view=self)

    @discord.ui.button(label="필살기", style=discord.ButtonStyle.success, row=1)
    async def ultimate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.special_used:
            await interaction.response.send_message("필살기는 1회만 사용할 수 있습니다!", ephemeral=True)
            return
        dmg = int((1 - (self.player["hp"] / self.player["max_hp"])) * 40) + 15
        self.enemy["hp"] -= dmg
        self.special_used = True
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await self.message.edit(embed=self.build_embed(f"필살기 → {dmg} 데미지"), view=self)

        dmg = self.damage(10)
        self.enemy["hp"] -= dmg
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await self.message.edit(embed=self.build_embed(f"기본기 → {dmg} 데미지"), view=self)

        if random.random() < 0.7:
            dmg = self.damage(20)
            self.enemy["hp"] -= dmg
            result = f"특수기 → {dmg} 데미지"
        else:
            result = "특수기 빗나감"
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await self.message.edit(embed=self.build_embed(result), view=self)

        self.enemy["iv"]["SPD"] = max(1, self.enemy["iv"]["SPD"] - 3)
        await self.message.edit(embed=self.build_embed("상대 SPD 감소"), view=self)

        if self.special_used:
            await interaction.response.send_message("필살기는 1회만 사용할 수 있습니다!", ephemeral=True)
            return
        dmg = int((1 - (self.player["hp"] / self.player["max_hp"])) * 40) + 15
        self.enemy["hp"] -= dmg
        self.special_used = True
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await self.message.edit(embed=self.build_embed(f"필살기 → {dmg} 데미지"), view=self)
        self.logs.append("전투 종료!")
        gained = random.randint(20, 50)
        self.player["exp"] += gained
        while self.player["exp"] >= self.player["next_exp"]:
            self.player["exp"] -= self.player["next_exp"]
            self.player["level"] += 1
            self.player["next_exp"] = exp_to_next_level(self.player["level"])
            self.player["max_hp"] = calculate_stat(self.player["iv"]["HP"], self.player["level"])
            self.player["hp"] = self.player["max_hp"]
            self.logs.append(f"레벨업! → Lv{self.player['level']}")
        await self.message.edit(content="전투 종료", embed=self.build_embed("EXP +" + str(gained)), view=GameView(self.user, self.message))

        dmg = self.damage(10)
        self.enemy["hp"] -= dmg
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await self.message.edit(embed=self.build_embed(f"기본기 → {dmg} 데미지"), view=self)

async def start_battle(interaction, message):
    uid = str(interaction.user.id)
    if uid not in user_profiles or user_profiles[uid]["main"] is None:
        await interaction.response.edit_message(content="대표 포켓몬이 없습니다.")
        return
    player = user_profiles[uid]["owned"][user_profiles[uid]["main"]]
    wild = {
        "name": "야돈",
        "level": random.randint(player["level"], player["level"] + 2),
        "iv": generate_iv()
    }
    wild["max_hp"] = calculate_stat(wild["iv"]["HP"], wild["level"])
    wild["hp"] = wild["max_hp"]
    embed = discord.Embed(title="야생 포켓몬 등장!", description="전투를 시작합니다.", color=discord.Color.red())
    view = BattleView(interaction.user, player, wild, message)
    await interaction.response.edit_message(embed=view.build_embed("전투 시작!"), view=view)

@bot.command()
async def 메뉴(ctx):
    msg = await ctx.send("포켓몬 RPG 메뉴 로딩 중...")
    await msg.edit(content="메뉴를 선택하세요.", view=GameView(ctx.author, msg))

@bot.event
async def on_ready():
    print(f"{bot.user} 준비 완료!")

bot.run(os.getenv("DISCORD_TOKEN"))
