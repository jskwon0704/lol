import discord
from discord.ext import commands
import json
import random
import os
import asyncio

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

def hp_bar(current, max_hp):
    ratio = current / max_hp
    total_bars = 10
    filled = int(ratio * total_bars)
    empty = total_bars - filled
    return '🟩' * filled + '🟥' * empty

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

class HuntingView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user

    @discord.ui.button(label="사냥터 1", style=discord.ButtonStyle.primary, row=0)
    async def hunt1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await start_battle(interaction, 1)

    @discord.ui.button(label="사냥터 2", style=discord.ButtonStyle.primary, row=0)
    async def hunt2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await start_battle(interaction, 2)

    @discord.ui.button(label="사냥터 3", style=discord.ButtonStyle.primary, row=1)
    async def hunt3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await start_battle(interaction, 3)

    @discord.ui.button(label="사냥터 4", style=discord.ButtonStyle.primary, row=1)
    async def hunt4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await start_battle(interaction, 4)

    @discord.ui.button(label="사냥터 5", style=discord.ButtonStyle.primary, row=2)
    async def hunt5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await start_battle(interaction, 5)
class BattleView(discord.ui.View):
    def __init__(self, user, player_mon, wild_mon):
        super().__init__(timeout=60)
        self.user = user
        self.player = player_mon
        self.enemy = wild_mon
        self.special_used = False

    def build_status(self, turn_owner):
        msg = f"턴: {turn_owner}\n"
        msg += f"플레이어 Lv{self.player['level']} HP: {self.player['hp']}/{self.player['max_hp']}\n"
        msg += f"상대 Lv{self.enemy['level']} HP: {self.enemy['hp']}/{self.enemy['max_hp']}\n\n"
        return msg

    async def update_message(self, interaction, action_text):
        status = self.build_status("플레이어")
        await interaction.message.edit(content=status + action_text, view=self)

    def calculate_damage(self, base):
        return random.randint(base - 2, base + 2)

    async def end_battle(self, interaction):
        uid = str(interaction.user.id)
        gained_exp = random.randint(30, 60)
        self.player["exp"] += gained_exp
        level_up_msgs = []
        while self.player["exp"] >= self.player["next_exp"]:
            self.player["exp"] -= self.player["next_exp"]
            self.player["level"] += 1
            self.player["next_exp"] = exp_to_next_level(self.player["level"])
            self.player["max_hp"] = calculate_stat(self.player["iv"]["HP"], self.player["level"])
            self.player["hp"] = self.player["max_hp"]
            level_up_msgs.append(f"레벨업! 현재 레벨: {self.player['level']}")

        summary = f"전투 종료! 승리\n경험치 +{gained_exp}\n" + "\n".join(level_up_msgs)
        await asyncio.sleep(1)
        await interaction.message.edit(content=summary, view=None)
        await interaction.followup.send("다음 행동을 선택하세요:", view=MenuView(user=interaction.user))
        self.stop()

    @discord.ui.button(label="기본기", style=discord.ButtonStyle.primary, row=0)
    async def basic_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        damage = self.calculate_damage(10)
        await interaction.message.edit(content="기본기 시전 중...", view=None)
        await asyncio.sleep(1)
        self.enemy["hp"] -= damage
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await interaction.followup.send(self.build_status("플레이어") + f"기본기로 상대에게 {damage} 데미지!", view=self)

    @discord.ui.button(label="특수기", style=discord.ButtonStyle.danger, row=0)
    async def special_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(content="특수기 시전 중...", view=None)
        await asyncio.sleep(1)
        if random.random() < 0.7:
            damage = self.calculate_damage(20)
            self.enemy["hp"] -= damage
            result = f"특수기로 상대에게 {damage} 데미지!"
        else:
            result = "특수기가 빗나갔다!"
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await interaction.followup.send(self.build_status("플레이어") + result, view=self)

    @discord.ui.button(label="유틸기", style=discord.ButtonStyle.secondary, row=1)
    async def utility(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(content="유틸기 사용 중...", view=None)
        await asyncio.sleep(1)
        self.enemy["iv"]["SPD"] = max(1, self.enemy["iv"]["SPD"] - 2)
        await interaction.followup.send(self.build_status("플레이어") + f"상대의 스피드가 감소했다!", view=self)

    @discord.ui.button(label="필살기", style=discord.ButtonStyle.success, row=1)
    async def ultimate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.special_used:
            await interaction.response.send_message("이미 필살기를 사용했습니다!", ephemeral=True)
            return
        await interaction.message.edit(content="필살기 발동 중...", view=None)
        await asyncio.sleep(1)
        damage = int((1 - (self.player["hp"] / self.player["max_hp"])) * 40) + 10
        self.enemy["hp"] -= damage
        self.special_used = True
        if self.enemy["hp"] <= 0:
            await self.end_battle(interaction)
            return
        await interaction.followup.send(self.build_status("플레이어") + f"필살기로 상대에게 {damage} 데미지!", view=self)

# start_battle 내부 메시지 문구도 수정
async def start_battle(interaction, zone):
    uid = str(interaction.user.id)
    if uid not in user_profiles or user_profiles[uid]["main"] is None:
        await interaction.response.send_message("대표 포켓몬이 없습니다.")
        return

    zones = load_hunting_data()
    if str(zone) not in zones:
        await interaction.response.send_message("존재하지 않는 사냥터입니다.")
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
    status = f"야생의 {wild_name}(Lv{wild_level})이 나타났다!\n"
    view = BattleView(interaction.user, player_mon, wild_mon)
    status += view.build_status("플레이어")
    await interaction.response.send_message(status, view=view)

# MenuView 텍스트도 이모지 제거
@bot.command()
async def 메뉴(ctx):
    await ctx.send("포켓몬 RPG 메뉴", view=MenuView(user=ctx.author))

@bot.event
async def on_ready():
    print(f"{bot.user} 접속 완료!")
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        await channel.send("포켓몬 RPG 메뉴", view=MenuView(user=None))


bot.run(os.getenv("DISCORD_TOKEN"))
