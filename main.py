import discord
from discord.ext import commands
import json
import random
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_profiles = {}
TARGET_CHANNEL_ID = 123456789012345678  # 여기에 봇이 메뉴 버튼을 보내야 할 채널 ID를 입력하세요

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
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="대표 포켓몬 설정", style=discord.ButtonStyle.primary)
    async def 대표설정(self, interaction: discord.Interaction, button: discord.ui.Button):
        roles = [role.name for role in interaction.user.roles]
        uid = str(interaction.user.id)
        if uid not in user_profiles:
            user_profiles[uid] = {"owned": {}, "main": None}
        valid = [r for r in roles if r != "@everyone"]
        if not valid:
            await interaction.response.send_message("보유한 포켓몬 역할이 없습니다.")
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
        await interaction.response.send_message(f"{interaction.user.mention}의 대표 포켓몬을 {name}(으)로 설정했습니다.")

    @discord.ui.button(label="사냥하기", style=discord.ButtonStyle.success)
    async def 사냥(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("사냥터를 선택하세요.", view=HuntingView(interaction.user))

    @discord.ui.button(label="프로필 보기", style=discord.ButtonStyle.secondary)
    async def 프로필(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in user_profiles or user_profiles[uid]["main"] is None:
            await interaction.response.send_message(f"{interaction.user.mention}의 대표 포켓몬이 없습니다.")
            return
        mon = user_profiles[uid]["owned"][user_profiles[uid]["main"]]
        msg = f"{interaction.user.mention}의 프로필\n🎒 대표 포켓몬: {user_profiles[uid]['main']}\n"
        msg += f"📊 레벨: {mon['level']}\n경험치: {mon['exp']}/{mon['next_exp']}\nIV: {mon['iv']}\nHP: {mon['hp']}/{mon['max_hp']}"
        await interaction.response.send_message(msg)

    @discord.ui.button(label="배틀 시작", style=discord.ButtonStyle.danger)
    async def 배틀(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_battle(interaction)

class HuntingView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user

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
        await interaction.response.send_message("대표 포켓몬이 없습니다.")
        return

    zones = load_hunting_data()
    if str(zone) not in zones:
        await interaction.response.send_message("존재하지 않는 사냥터입니다.")
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
    message = f"[사냥터 {zone}] Lv{wild_level} {wild_name} 조우 결과: {result}!\n획득 경험치: {gained_exp}\n"

    while mon["exp"] >= mon["next_exp"]:
        mon["exp"] -= mon["next_exp"]
        mon["level"] += 1
        mon["next_exp"] = exp_to_next_level(mon["level"])
        mon["max_hp"] = calculate_stat(mon["iv"]["HP"], mon["level"])
        mon["hp"] = mon["max_hp"]
        message += f"📈 레벨업! 현재 레벨: {mon['level']}\n"

    await interaction.response.send_message(message)

@bot.command()
async def 메뉴(ctx):
    await ctx.send("\U0001F525 포켓몬 RPG 메뉴", view=MenuView(user=ctx.author))

@bot.event
async def on_ready():
    print(f"{bot.user} 접속 완료!")
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        await channel.send("\U0001F525 포켓몬 RPG 메뉴", view=MenuView(user=None))

async def start_battle(interaction):
    uid = str(interaction.user.id)
    if uid not in user_profiles or user_profiles[uid]["main"] is None:
        await interaction.response.send_message("대표 포켓몬이 없습니다.")
        return

    player_mon = user_profiles[uid]["owned"][user_profiles[uid]["main"]]
    wild_name = random.choice(["야돈", "깨비참", "리자드", "푸호꼬"])
    wild_level = random.randint(player_mon["level"] - 1, player_mon["level"] + 2)
    wild_iv = generate_iv()
    wild_mon = {
        "name": wild_name,
        "level": wild_level,
        "iv": wild_iv,
        "max_hp": calculate_stat(wild_iv["HP"], wild_level),
        "hp": calculate_stat(wild_iv["HP"], wild_level)
    }
    await interaction.response.send_message(f"야생의 {wild_name}(Lv{wild_level})이 나타났다!", view=BattleView(interaction.user, player_mon, wild_mon))

class BattleView(discord.ui.View):
    def __init__(self, user, player_mon, wild_mon):
        super().__init__(timeout=60)
        self.user = user
        self.player = player_mon
        self.enemy = wild_mon
        self.special_used = False

    async def end_battle(self, interaction, result):
        await interaction.response.send_message(f"배틀 종료! 결과: {result}")
        self.stop()

    def calculate_damage(self, base):
        return random.randint(base - 2, base + 2)

    @discord.ui.button(label="🥊 기본기", style=discord.ButtonStyle.primary, row=0)
    async def basic_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        damage = self.calculate_damage(10)
        self.enemy["hp"] -= damage
        msg = f"기본기로 {self.enemy['name']}에게 {damage} 데미지를 입혔다!\n"
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction, "승리")
            return
        msg += f"{self.enemy['name']} 남은 체력: {self.enemy['hp']}/{self.enemy['max_hp']}"
        await interaction.response.send_message(msg)

    @discord.ui.button(label="🔥 특수기", style=discord.ButtonStyle.danger, row=0)
    async def special_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        if random.random() < 0.7:
            damage = self.calculate_damage(20)
            self.enemy["hp"] -= damage
            msg = f"특수기로 {self.enemy['name']}에게 {damage} 데미지를 입혔다!\n"
        else:
            msg = "특수기가 빗나갔다!\n"
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction, "승리")
            return
        msg += f"{self.enemy['name']} 남은 체력: {self.enemy['hp']}/{self.enemy['max_hp']}"
        await interaction.response.send_message(msg)

    @discord.ui.button(label="🌀 유틸기", style=discord.ButtonStyle.secondary, row=1)
    async def utility(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.enemy["iv"]["SPD"] = max(1, self.enemy["iv"]["SPD"] - 2)
        await interaction.response.send_message(f"{self.enemy['name']}의 스피드가 감소했다!")

    @discord.ui.button(label="💥 필살기", style=discord.ButtonStyle.success, row=1)
    async def ultimate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.special_used:
            await interaction.response.send_message("이미 필살기를 사용했습니다!")
            return
        damage = int((1 - (self.player["hp"] / self.player["max_hp"])) * 40) + 10
        self.enemy["hp"] -= damage
        self.special_used = True
        msg = f"필살기로 {self.enemy['name']}에게 {damage} 데미지를 입혔다!\n"
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction, "승리")
            return
        msg += f"{self.enemy['name']} 남은 체력: {self.enemy['hp']}/{self.enemy['max_hp']}"
        await interaction.response.send_message(msg)

bot.run(os.getenv("DISCORD_TOKEN"))
