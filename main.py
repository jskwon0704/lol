
import discord
from discord.ext import commands
import os
import random
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
    return int((iv * level / 10) + level)

def exp_to_next_level(level):
    return int(50 + (level * 10) + (1.5 * (level ** 2)))

def get_pokemon_image(name):
    images = {
        "파이리": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/4.png",
        "야돈": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/79.png"
    }
    return images.get(name, "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/0.png")

class MenuView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="대표 포켓몬 설정", style=discord.ButtonStyle.primary)
    async def set_main(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        await interaction.response.send_message(f"{interaction.user.mention}의 대표 포켓몬을 {name}(으)로 설정했습니다.", ephemeral=True)

    @discord.ui.button(label="사냥하기", style=discord.ButtonStyle.success)
    async def hunt(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message("사냥터를 선택하세요.", view=HuntingView(interaction.user), ephemeral=True)

    @discord.ui.button(label="프로필 보기", style=discord.ButtonStyle.secondary)
    async def show_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in user_profiles or user_profiles[uid]["main"] is None:
            await interaction.response.send_message("대표 포켓몬이 없습니다.", ephemeral=True)
            return
        mon = user_profiles[uid]["owned"][user_profiles[uid]["main"]]
        msg = f"{interaction.user.mention}의 프로필\n대표 포켓몬: {user_profiles[uid]['main']}\n"
        msg += f"레벨: {mon['level']}\n경험치: {mon['exp']}/{mon['next_exp']}\nIV: {mon['iv']}\nHP: {mon['hp']}/{mon['max_hp']}"
        await interaction.response.send_message(msg, ephemeral=True)

class HuntingView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user

    @discord.ui.button(label="사냥터 1", style=discord.ButtonStyle.primary)
    async def zone1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await start_battle(interaction, 1)

class BattleView(discord.ui.View):
    def __init__(self, user, player_mon, wild_mon):
        super().__init__(timeout=120)
        self.user = user
        self.player = player_mon
        self.enemy = wild_mon
        self.special_used = False
        self.message = None
        self.logs = []

    def build_status_embed(self, turn_owner, action_text=""):
        embed = discord.Embed(title=f"{self.user.display_name}의 전투", color=discord.Color.green())
        embed.add_field(name="플레이어", value=f"Lv{self.player['level']} | HP: {self.player['hp']} / {self.player['max_hp']}", inline=True)
        embed.add_field(name="상대", value=f"Lv{self.enemy['level']} | HP: {self.enemy['hp']} / {self.enemy['max_hp']}", inline=True)
        embed.add_field(name="현재 턴", value=turn_owner, inline=False)

        if action_text:
            self.logs.append(action_text)
        if len(self.logs) > 3:
            self.logs = self.logs[-3:]
        if self.logs:
            embed.add_field(name="전투 로그", value="\n".join(self.logs), inline=False)

        player_img = get_pokemon_image(self.user_profiles_main())
        enemy_img = get_pokemon_image(self.enemy["name"])
        embed.set_thumbnail(url=player_img)
        embed.set_image(url=enemy_img)
        return embed

    def user_profiles_main(self):
        uid = str(self.user.id)
        return user_profiles[uid]["main"] if uid in user_profiles else "파이리"

    async def update_message(self, interaction, action_text):
        embed = self.build_status_embed("플레이어", action_text)
        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            self.message = await interaction.response.send_message(embed=embed, view=self, wait=True)

    def calculate_damage(self, base):
        return random.randint(base - 2, base + 2)

    async def end_battle(self, interaction):
        uid = str(interaction.user.id)
        gained_exp = random.randint(30, 60)
        self.player["exp"] += gained_exp
        logs = [f"전투 종료!", f"경험치 +{gained_exp}"]
        while self.player["exp"] >= self.player["next_exp"]:
            self.player["exp"] -= self.player["next_exp"]
            self.player["level"] += 1
            self.player["next_exp"] = exp_to_next_level(self.player["level"])
            self.player["max_hp"] = calculate_stat(self.player["iv"]["HP"], self.player["level"])
            self.player["hp"] = self.player["max_hp"]
            logs.append(f"레벨업! → Lv{self.player['level']}")
        embed = discord.Embed(title="전투 종료", description="\n".join(logs), color=discord.Color.gold())
        await self.message.edit(embed=embed, view=None)
        await asyncio.sleep(2)
        await self.message.edit(content="메뉴로 돌아갑니다.", embed=None, view=MenuView(user=self.user))
        self.stop()

    @discord.ui.button(label="기본기", style=discord.ButtonStyle.primary)
    async def basic_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        dmg = self.calculate_damage(10)
        self.enemy["hp"] -= dmg
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await self.update_message(interaction, f"기본기 → {dmg} 데미지")

async def start_battle(interaction, zone):
    uid = str(interaction.user.id)
    if uid not in user_profiles or user_profiles[uid]["main"] is None:
        await interaction.response.send_message("대표 포켓몬이 없습니다.", ephemeral=True)
        return
    zones = {"1": ["야돈"]}
    if str(zone) not in zones:
        await interaction.response.send_message("존재하지 않는 사냥터입니다.", ephemeral=True)
        return
    wild_name = random.choice(zones[str(zone)])
    player_mon = user_profiles[uid]["owned"][user_profiles[uid]["main"]]
    wild_level = random.randint(player_mon["level"] - 1, player_mon["level"] + 2)
    wild_iv = generate_iv()
    wild_mon = {
        "name": wild_name,
        "level": wild_level,
        "iv": wild_iv,
        "max_hp": calculate_stat(wild_iv["HP"], wild_level),
        "hp": calculate_stat(wild_iv["HP"], wild_level)
    }
    view = BattleView(interaction.user, player_mon, wild_mon)
    embed = view.build_status_embed("플레이어", f"{wild_name}(Lv{wild_level})이 나타났다!")
    view.message = await interaction.response.send_message(embed=embed, view=view, wait=True)

@bot.command()
async def 메뉴(ctx):
    await ctx.send("포켓몬 RPG 메뉴", view=MenuView(user=ctx.author))

@bot.event
async def on_ready():
    print(f"{bot.user} 접속 완료!")

bot.run(os.getenv("DISCORD_TOKEN"))
