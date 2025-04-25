import discord
from discord.ext import commands
import json
import random
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True  # 이 줄도 꼭 있어야 해

bot = commands.Bot(command_prefix="!", intents=intents)

user_profiles = {}

def generate_iv():
    return {stat: random.randint(10, 31) for stat in ["HP", "ATK", "DEF", "SPD"]}

def calculate_stat(iv, level):
    return int((iv * level / 10) + level)

def exp_to_next_level(level):
    return int(50 + (level * 10) + (1.5 * (level ** 2)))

def load_hunting_data():
    with open("hunting_zones.json", "r", encoding="utf-8") as f:
        return json.load(f)

class MenuView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user

    @discord.ui.button(label="대표 포켓몬 설정", style=discord.ButtonStyle.primary)
    async def 대표설정(self, interaction: discord.Interaction, button: discord.ui.Button):
        roles = [role.name for role in interaction.user.roles]
        uid = str(interaction.user.id)
        if uid not in user_profiles:
            user_profiles[uid] = {"owned": {}, "main": None}
        valid = [r for r in roles if r not in ["@everyone"]]
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
        await interaction.response.send_message(f"대표 포켓몬을 {name}(으)로 설정했습니다.", ephemeral=True)

    @discord.ui.button(label="사냥하기", style=discord.ButtonStyle.success)
    async def 사냥(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("사냥터를 선택하세요.", view=HuntingView(interaction.user), ephemeral=True)

    @discord.ui.button(label="프로필 보기", style=discord.ButtonStyle.secondary)
    async def 프로필(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in user_profiles or user_profiles[uid]["main"] is None:
            await interaction.response.send_message("대표 포켓몬이 없습니다.", ephemeral=True)
            return
        mon = user_profiles[uid]["owned"][user_profiles[uid]["main"]]
        msg = f"🎒 대표 포켓몬: {user_profiles[uid]['main']}\n"
        msg += f"📊 레벨: {mon['level']}\n경험치: {mon['exp']}/{mon['next_exp']}\nIV: {mon['iv']}\nHP: {mon['hp']}/{mon['max_hp']}"
        await interaction.response.send_message(msg, ephemeral=True)

class HuntingView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user
        for i in range(1, 6):
            self.add_item(discord.ui.Button(label=f"사냥터 {i}", custom_id=f"hunt_{i}", style=discord.ButtonStyle.primary))

    @discord.ui.button(label="사냥터 1", style=discord.ButtonStyle.primary, row=0)
    async def hunt1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_hunt(interaction, 1)

    @discord.ui.button(label="사냥터 2", style=discord.ButtonStyle.primary, row=0)
    async def hunt2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_hunt(interaction, 2)

    @discord.ui.button(label="사냥터 3", style=discord.ButtonStyle.primary, row=1)
    async def hunt3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_hunt(interaction, 3)

    @discord.ui.button(label="사냥터 4", style=discord.ButtonStyle.primary, row=1)
    async def hunt4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_hunt(interaction, 4)

    @discord.ui.button(label="사냥터 5", style=discord.ButtonStyle.primary, row=2)
    async def hunt5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_hunt(interaction, 5)

async def handle_hunt(interaction, zone):
    uid = str(interaction.user.id)
    if uid not in user_profiles or user_profiles[uid]["main"] is None:
        await interaction.response.send_message("대표 포켓몬이 없습니다.", ephemeral=True)
        return

    zones = load_hunting_data()
    if str(zone) not in zones:
        await interaction.response.send_message("존재하지 않는 사냥터입니다.", ephemeral=True)
        return

    wild_name = random.choice(zones[str(zone)])
    wild_level = random.randint(zone * 5, zone * 10)
    wild_iv = generate_iv()
    wild_stat = {
        "DEF": calculate_stat(wild_iv["DEF"], wild_level),
        "SPD": calculate_stat(wild_iv["SPD"], wild_level),
    }

    mon = user_profiles[uid]["owned"][user_profiles[uid]["main"]]
    atk_stat = calculate_stat(mon["iv"]["ATK"], mon["level"])
    spd_stat = calculate_stat(mon["iv"]["SPD"], mon["level"])
    player_score = atk_stat + spd_stat
    wild_score = wild_stat["DEF"] + wild_stat["SPD"]

    result = "승리" if player_score >= wild_score else "실패"
    gained_exp = random.randint(20, 50) + (zone * 10) if result == "승리" else random.randint(5, 10)
    mon["exp"] += gained_exp
    message = f"[사냥터 {zone}] Lv{wild_level} {wild_name}과의 조우 결과: {result}!\n얻은 경험치: {gained_exp}\n"

    while mon["exp"] >= mon["next_exp"]:
        mon["exp"] -= mon["next_exp"]
        mon["level"] += 1
        mon["next_exp"] = exp_to_next_level(mon["level"])
        mon["max_hp"] = calculate_stat(mon["iv"]["HP"], mon["level"])
        mon["hp"] = mon["max_hp"]
        message += f"📈 {mon['level']}레벨 상승! 체력 완전 회복!\n"

    await interaction.response.send_message(message, ephemeral=True)

@bot.command()
async def 메뉴(ctx):
    await ctx.send("원하는 버튼을 선택하세요.", view=MenuView(ctx.author))

bot.run(os.getenv("DISCORD_TOKEN"))
