import asyncio
import aiohttp
from aiohttp import web
from contextlib import asynccontextmanager
from typing import Generator, Any, Union, Optional
import mimetypes
import sys
import os
import shutil
import re
import random
import json
import copy
from urllib import parse
from tkinter import messagebox
import tkinter as Tk
import tkinter.ttk as ttk
import webbrowser
import traceback

try:
    from plugin.debug import Debug
    global_debug = True
except:
    global_debug = False


class Battle():
    DEFAULT_BG = 'event_82'

    def __init__(self, server) -> None:
        self.server = server
        self.turn = 1
        self.characters = []
        self.summons = []
        self.bg = self.DEFAULT_BG

    async def getPayload(self) -> dict:
        payload = self.server.getJSONData('payload.json')
        if len(self.characters) == 0:
            sp1 = "No characters loaded, please wait and reload"
            sp2 = ""
        else:
            sp1 = "{} characters, {} summons loaded".format(len(self.characters), len(self.summons))
            sp2 = "" 
            for c in self.characters:
                sp2 += "{}, ".format(c.origin)
            if sp2 != "": sp2 = sp2[:-2] + "<br>"
            for s in self.summons:
                sp2 += "{}, ".format(s.origin)
            if sp2 != "": sp2 = sp2[:-2]
        payload['data'] = parse.quote((await self.server.loadFile('data/base.html')).decode('utf-8').replace('img_low', 'img').replace('GBFBPVER', 'GBFBP v' + self.server.version).replace('SP1', sp1).replace('SP2', sp2))
        return payload

    def getStart(self) -> dict:    
        start = self.server.getJSONData('start.json')
        player_param = self.server.getJSONData('player_param.json')
        summon = self.server.getJSONData('summon.json')
        start['player']['number'] = min(4, len(self.characters))
        start['background'] = "/sp/raid/bg/{}.jpg".format(self.bg if self.bg != '' else self.DEFAULT_BG)
        self.turn = 1
        for i in range(min(4, len(self.characters))):
            start['player']['param'].append(copy.deepcopy(player_param))
            if self.characters[i].what == "npc":
                start['skip_special_motion_setting'].append({"pos": i, "setting_id": str(self.characters[i].id), "skip_flag": False})
                k = "{}_0{}{}{}".format(self.characters[i].id, self.characters[i].uncap, self.characters[i].style, self.characters[i].other)
                start['player']['param'][i]['name'] = k
                start['player']['param'][i]['cjs'] = self.characters[i].lookFor('npc')
                if start['player']['param'][i]['cjs'] is None:
                    print("Missing npc:", self.characters[i].id)
                    continue
                start['player']['param'][i]['pid'] = str(self.characters[i].id)
                start['player']['param'][i]['setting_id'] = str(self.characters[i].id)
                start['player']['param'][i]['pid_image'] = self.characters[i].portrait
                start['player']['param'][i]['pid_image_cutin'] = self.characters[i].portrait
                start['player']['param'][i]['special_comment'] = k
            elif self.characters[i].what == "weapon" or self.characters[i].what == "mc":
                start['skip_special_motion_setting'].append({"pos": i, "setting_id": 1, "skip_flag": False})
                start['player']['param'][i]['name'] = str(self.characters[i].id)
                start['player']['param'][i]['cjs'] = self.characters[i].class_cjs
                start['player']['param'][i]['pid'] = self.characters[i].class_id
                start['player']['param'][i]['setting_id'] = 1
                start['player']['param'][i]['pid_image'] = self.characters[i].portrait
                start['player']['param'][i]['leader'] = 1
                start['player']['param'][i]['pid_image_cutin'] = self.characters[i].class_id
                uncap = "" if self.characters[i].uncap == 1 else "_0"+str(self.characters[i].uncap)
                if self.characters[i].melee:
                    start['weapon'] = {'weapon_l':str(self.characters[i].id) + uncap + "_1", 'weapon_r':str(self.characters[i].id) + uncap + "_2"}
                    start['weapon_kind'] = {'weapon_l':str((int(self.characters[i].id) // 100000) % 10 + 1), 'weapon_r':str((int(self.characters[i].id) // 100000) % 10 + 1)}
                else:
                    start['weapon'] = {'weapon':str(self.characters[i].id) + uncap}
                    start['weapon_kind'] = {'weapon':str((int(self.characters[i].id) // 100000) % 10 + 1)}
                if self.characters[i].what == "mc": start['player']['param'][i]['special_comment'] = '{}_{}'.format(self.characters[i].id, self.characters[i].class_cjs)
                else: start['player']['param'][i]['special_comment'] = '{}'.format(self.characters[i].id)
            start['user_full_auto_permit_flag'].append({"1":0,"2":0,"3":0,"4":0})
            start['player']['param'][i]['special_comment'] += " " + self.characters[i].what + "<br>"
            if self.characters[i].has_other: start['player']['param'][i]['special_comment'] += "[Form]"
            if self.characters[i].has_win1 and self.characters[i].has_win2: start['player']['param'][i]['special_comment'] += "[Win1]"
            if self.characters[i].has_win2: start['player']['param'][i]['special_comment'] += "[Win2]"
            if self.characters[i].ab != "": start['player']['param'][i]['special_comment'] += "[Skill:" + self.characters[i].ab + "]"

            start['player']['param'][i]['hp'] = self.characters[i].hp
            start['player']['param'][i]['recast'] = self.characters[i].gauge
            start['formation'].append(str(i))
            phit = self.characters[i].lookFor('phit')
            if phit is None: phit = "phit_ax_0001"
            for j in range(4): start['player']['param'][i]['effect'].append(phit)
            
            start['ability'][str(i)] = self.genAbility(i, self.characters[i])
        for i in range(min(5, len(self.summons))):
            start['summon'].append(copy.deepcopy(summon))
            start['summon'][-1]['id'] = str(self.summons[i].id)
            start['summon'][-1]['image_id'] = self.summons[i].portrait
            start['summon'][-1]['name'] = "{}_0{}".format(self.summons[i].id, self.summons[i].uncap)
        return start

    def getAttack(self) -> dict:
        attack = self.server.getJSONData('normal_attack.json')
        indiv = self.server.getJSONData('normal_attack_indiv.json')
        ougi = self.server.getJSONData('ougi.json')
        
        for el in attack:
            if 'bg_image' in el:
                el['bg_image'] = "/sp/raid/bg/{}.jpg".format(self.current_bg if self.current_bg != '' else 'event_82')
        c = min(4, len(self.characters))
        dbx = 0
        for j in range(2): # added twice, no idea why
            for i in range(c):
                attack['scenario'].insert(dbx, {"cmd": "condition", "pos": i, "to": "player", "condition": {"buff": None, "debuff": None, "num": i}})
                dbx += 1
        idx = 1 + dbx
        self.turn += 1
        chain = 0
        for i in range(c):
            if self.characters[i].what == "npc":
                attack['status']['skip_special_motion_setting'].append({"pos": i, "setting_id": str(self.characters[i].id), "skip_flag": False})
                nsp = self.characters[i].lookForRandom('nsp', None if self.characters[i].other == '' else self.characters[i].other)
                if nsp is None and self.characters[i].other != '':
                    nsp = self.characters[i].lookForRandom('nsp')
            elif self.characters[i].what == "weapon" or self.characters[i].what == "mc":
                attack['status']['skip_special_motion_setting'].append({"pos": i, "setting_id": 1, "skip_flag": False})
                nsp = self.characters[i].lookFor('sp', None)
            if self.characters[i].gauge >= 100:
                scenario = copy.deepcopy(ougi)
                scenario['kind'] = nsp
                scenario['pos'] = i
                scenario['num'] = i + 1
                chain += 1
                scenario['count'] = chain
                if '_s2' in nsp or '_s3' in nsp:
                    scenario['full_screen_flag'] = True
                if self.characters[i].what == "npc":
                    scenario['cutin_image'] = self.characters[i].portrait if (self.characters[i].other == '' or self.characters[i].other_portrait is None) else self.characters[i].other_portrait
                    scenario['setting_id'] = "{}".format(self.characters[i].id)
                elif self.characters[i].what == "weapon" or self.characters[i].what == "mc":
                    scenario['cmd'] = 'special'
                    scenario['cutin_image'] = self.characters[i].class_id
                    scenario['setting_id'] = 1
                attack['scenario'].insert(idx, scenario)
                idx += 1
            else:
                scenario = copy.deepcopy(indiv)
                for el in scenario:
                    if 'pos' in el: el['pos'] = i
                    if 'num' in el: el['num'] = i + 1
                    attack['scenario'].insert(idx, el)
                    idx += 1
            
            attack['status']['ability'][str(i)] = self.genAbility(i, self.characters[i])

            attack['status']['turn'] = self.turn
            attack['status']['special_skill_activate'].append({"pos": i, "special_skill_activate_flag": True})
            attack['status']['is_guard_status'].append({"pos": i,"is_guard_status": 0,"is_guard_unavailable": 0})
        # enemy attack:
        pattern = (self.turn - 2) % (len(self.server.enemy_super) + 1)
        for i in range(len(attack['scenario'])):
            if attack['scenario'][i]['cmd'] == 'turn':
                if pattern == 0:
                    attack['scenario'].insert(i+5, {"cmd":"attack","from":"boss","pos":0,"damage":{"1":[{"attack_count":1,"concurrent_attack_count":0,"pos":0,"value":0,"attr":"1","split":["0"],"hp":self.characters[0].hp,"size":"l","critical":False,"miss":4,"guard":False,"additional":[{"message":None,"effect":None}]}]},"voice":[None],"color":None,"single_motion_flag":False,"concurrent_attack_flag":False,"standby":False,"companion_weapon_flag":False,"is_all_attack":False})
                else:
                    attack['scenario'].insert(i+5, {"cmd":"super","kind":"{}".format(self.server.enemy_super[pattern-1]),"name":"{}".format(self.server.enemy_super[pattern-1]),"pos":0,"target":"player","to":"","chain":"","count":1,"serif":"","voice":None,"voice_wait":None,"attr":"1","total":[],"list":[{"damage":[]}],"skip_label_nsp":"","skip_frame_nsp":"","cutin_image":None,"window_effect_mode":"","return_motion_label":None,"cjs_param":{"voice_change_flag":0},"full_screen_flag":False,"fixed_pos_owner_bg":False,"setting_id":2,"skip_flag":False,"no_skip":False,"skip_label":"","skip_frame":"","force_top_flag":"","effect_all":"","no_change_display_order":"","is_activate_counter_damaged":False})
                break
        return attack

    def parseCustomAnimation(self, scenario : list, animations : list) -> None:
        standard = scenario[0]
        scenario.pop(0)
        try:
            wait_time = int(self.custom_ani_time)
        except:
            wait_time = 80
        for i in range(len(animations)):
            scenario.insert(i*2, standard.copy())
            scenario[i*2]["motion_label"] = "wait" if animations[i] == "" else animations[i]
            scenario[i*2]['name'] = scenario[i*2]["motion_label"]
            scenario.insert(i*2+1, {"cmd": "wait", "fps": wait_time})

    def getAbility(self, data):
        attack = self.server.getJSONData('ability_use.json')
        
        for el in attack:
            if 'bg_image' in el:
                el['bg_image'] = "/sp/raid/bg/{}.jpg".format(self.current_bg if self.current_bg != '' else 'event_82')
        c = min(4, len(self.characters))
        pos = (int(data['ability_id']) - 1) // 4
        skill_id = (int(data['ability_id']) - 1) % 4
        sub_skill = None if len(data['ability_sub_param']) == 0 else data['ability_sub_param'][0]
        attack['scenario'][0]['pos'] = pos
        attack['scenario'][0]['num'] = pos
        if not self.characters[pos].has_abmotion: # lina fix
            attack['scenario'][0]["motion_label"] = "ability"
        match skill_id:
            case 0:
                if self.characters[pos].hp == 1:
                    attack['scenario'][0]['name'] = "Full HP"
                    self.characters[pos].hp = self.characters[pos].MAX_HP
                    attack['scenario'].insert(1, {"cmd": "hp","to": "player","pos": pos,"value": self.characters[pos].MAX_HP,"max": self.characters[pos].MAX_HP,"split": ["9","9","9","9","9"]})
                else:
                    attack['scenario'][0]['name'] = "1 HP"
                    self.characters[pos].hp = 1
                    attack['scenario'].insert(1, {"cmd": "hp","to": "player","pos": pos,"value": 1,"max": self.characters[pos].MAX_HP,"split": ["1"]})
            case 1:
                if self.characters[pos].gauge == 100:
                    attack['scenario'][0]['name'] = "0% Charge Bar"
                    self.characters[pos].gauge = 0
                    attack['scenario'].insert(1, {"cmd": "recast","to": "player","pos": pos,"value": 0,"max": "","split": ["0"]})
                else:
                    attack['scenario'][0]['name'] = "100% Charge Bar"
                    self.characters[pos].gauge = 100
                    attack['scenario'].insert(1, {"cmd": "recast","to": "player","pos": pos,"value": 100,"max": "","split": ["0"]})
            case 2:
                match sub_skill:
                    case 1:
                        attack['scenario'][0]['name'] = "Win Animation"
                        attack['scenario'][0]["motion_label"] = "win_1" if self.characters[pos].has_win2 and self.characters[pos].has_win1 else "win"
                        wait_time = 100
                    case 2:
                        attack['scenario'][0]['name'] = "Win #2 Animation"
                        attack['scenario'][0]["motion_label"] = "win_2" if self.characters[pos].has_win2 else "win"
                        wait_time = 100
                    case 3:
                        attack['scenario'][0]['name'] = "Damage Animation"
                        attack['scenario'][0]["motion_label"] = "damage"
                        wait_time = 50
                    case 4:
                        attack['scenario'][0]['name'] = "Down Animation"
                        attack['scenario'][0]["motion_label"] = "down"
                        wait_time = 50
                    case 5:
                        attack['scenario'][0]['name'] = "Skill Animations"
                        wait_time = 20
                        sa = self.characters[pos].lookForAll("ab_")
                        for i in range(len(sa)):
                            ef = {"cmd":"effect","to":"player","kind":sa[i],"name":"","list":[0],"wait":"50"}
                            if '_all_' in sa[i]:
                                ef['cmd'] = "windoweffect"
                                ef['is_damage_sync_effect'] = False
                            attack['scenario'].insert(1+i, ef)
                    case 7:
                        self.parseCustomAnimation(attack['scenario'], self.server.custom_ani[0].split(';'))
                        wait_time = None
                    case 8:
                        self.parseCustomAnimation(attack['scenario'], self.server.custom_ani[1].split(';'))
                        wait_time = None
                    case _: # 6
                        attack['scenario'][0]['name'] = "Wait Animation"
                        attack['scenario'][0]["motion_label"] = "wait"
                        wait_time = 50
                if wait_time is not None:
                    attack['scenario'].insert(1, {"cmd": "wait", "fps": wait_time})
            case 3:
                attack['scenario'][0]['name'] = "Form Change"
                if self.characters[pos].has_other:
                    if self.characters[pos].other == '':
                        self.characters[pos].other = '_f1'
                        form = 2
                        phit = self.characters[pos].lookFor('phit', '_f1')
                        if phit is None: phit = self.characters[pos].lookFor('phit')
                        if phit is None: phit = "phit_ax_0001"
                        npc = self.characters[pos].lookFor('npc', '_f1')
                        if npc is None: npc = self.characters[pos].lookFor('npc')
                        portrait = self.characters[pos].other_portrait if self.characters[pos].other_portrait is not None else self.characters[pos].portrait
                    else:
                        self.characters[pos].other = ''
                        form = 1
                        phit = self.characters[pos].lookFor('phit')
                        if phit is None: phit = "phit_ax_0001"
                        npc = self.characters[pos].lookFor('npc')
                        portrait = self.characters[pos].portrait
                else:
                    form = 1
                    phit = self.characters[pos].lookFor('phit')
                    if phit is None: phit = "phit_ax_0001"
                    npc = self.characters[pos].lookFor('npc')
                    portrait = self.characters[pos].portrait
                attack['scenario'].insert(1, {"cmd":"formchange","form":form,"param":{"attr":4,"name":"{}_0{}{}{}".format(self.characters[pos].id, self.characters[pos].uncap, self.characters[pos].style, self.characters[pos].other),"effect":[phit, phit, phit, phit],"cjs":npc,"extra_attr":0,"type":"s","motion_conf":None},"pos":pos,"to":"player","type":2,"no_motion":None,"no_change_motion":None,"bg_image":None,"fullscreen":None,"runaway_motion_flg":None,"fatigue_motion_flg":None,"effect_all":None,"is_large_dead":False})
                attack['scenario'].insert(2, {"cmd": "image_change","pos": pos,"image_id": portrait})
        if self.characters[pos].what == "weapon" or self.characters[pos].what == "mc":
            attack['scenario'][0]["motion_label"] = ""

        for i in range(c):
            attack['status']['ability'][str(i)] = self.genAbility(i, self.characters[i])

            attack['status']['turn'] = self.turn
            attack['status']['special_skill_activate'].append({"pos": i, "special_skill_activate_flag": True})
            attack['status']['is_guard_status'].append({"pos": i,"is_guard_status": 0,"is_guard_unavailable": 0})
        return attack

    def genAbility(self, pos : int, chara : 'Character') -> dict:
        skill = self.server.getJSONData('skill.json')
        if chara.what == "npc":
            ability = {"mode":"npc","pos":pos,"alive":1,"src":"assets/img/sp/assets/npc/ds/{}.jpg".format(chara.id),"list":{}}
        elif chara.what == "weapon" or chara.what == "mc":
            ability = {"mode":"player","pos":pos,"alive":1,"src":"assets/img/sp/assets/leader/ds/{}.jpg".format(chara.class_id),"list":{}}
        possible = [
            ('259_3', "Toggle HP", "Set the Character's HP to 1 or 100%", False),
            ('1005_3', "Toggle Charge Bar", "Set the Character's Charge Bar to 0% or 100%", False),
            ('469_3', "Pose", "Play a specific character animation", True),
            ('1350_3', "Change Form", "Toggle the Character's other form", False)
        ]
        for i in range(1, 5):
            if i == 2:
                if chara.what == "npc":
                    nsp = chara.lookForRandom('nsp', None if chara.other == '' else chara.other)
                    if nsp is None and chara.other != '':
                        nsp = chara.lookForRandom('nsp')
                    if nsp is None:
                        continue
                elif chara.what == "weapon" or chara.what == "mc":
                    nsp = chara.lookFor('sp', None)
                    if nsp is None:
                        continue
            elif (i >= 3 and chara.what != "npc"): continue
            elif (i == 4 and not chara.has_other): continue
            ability['list'][str(i)] = copy.deepcopy(skill)
            ability['list'][str(i)][0]['class'] = ability['list'][str(i)][0]['class'].format(possible[i-1][0], str(pos), i)
            ability['list'][str(i)][0]['ability-name'] = possible[i-1][1]
            ability['list'][str(i)][0]['ability-character-num'] = pos
            ability['list'][str(i)][0]['ability-id'] = str(i + pos * 4)
            ability['list'][str(i)][0]['text-data'] = possible[i-1][2]
            ability['list'][str(i)][1]['class'] = ability['list'][str(i)][1]['class'].format(str(pos), i)
            if possible[i-1][3]:
                ability['list'][str(i)][0]["ability-pick"] = str(16) # value might be hardcoded somewhere?
        return ability

    def getSubAbility(self, data : dict) -> dict:
        possible = [
            ('1_1', 'Win', 'Win Animation'),
            ('2_1', 'Win Alt', '2nd Win Animation (if available)'),
            ('3_1', 'Damage', 'Damage Animation'),
            ('4_1', 'Down', 'Down Animation'),
            ('5_1', 'Skills', 'Skill Animations'),
            ('6_1', 'Wait', 'Wait Animation'),
            ('7_1', 'Custom 1', 'Custom Animation 1'),
            ('8_1', 'Custom 2', 'Custom Animation 2')
        ]
        subabi = {"select_ability_info":{}}
        for i in range(len(possible)):
            subabi["select_ability_info"][str(i+1)] = {"index":str(i+1),"action_id":str(i+1),"name":possible[i][1],"comment":possible[i][2],"image":possible[i][0],"ability-pick":"","recaset-default":"0","duration":"","duration-second":"","duration-type":""}
        return subabi

    def getSummon(self, data : dict) -> dict:
        pos = int(data['summon_id']) - 1
        attack = self.server.getJSONData('ability_use.json')
        call = self.summons[pos].get_call()
        if len(call) == 2:
            attack['scenario'][0] = {"cmd":"summon","attr":"1","kind": call[0],"name":"","change":"off","list":[]}
            attack['scenario'].insert(1, {"cmd":"summon","attr":"1","kind":call[1],"name":"","change":"on","list":[]})
        else:
            attack['scenario'][0] = {"cmd":"summon_simple","attr":"1","kind": call[0],"name":"","change":"on"}

        for i in range(min(4, len(self.characters))):
            attack['status']['ability'][str(i)] = self.genAbility(i, self.characters[i])

            attack['status']['turn'] = self.turn
            attack['status']['special_skill_activate'].append({"pos": i, "special_skill_activate_flag": True})
            attack['status']['is_guard_status'].append({"pos": i,"is_guard_status": 0,"is_guard_unavailable": 0})
        return attack

class GBFBP():
    DEFAULT_ENEMY = "4200293"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36" # update it once in a while
    
    def __init__(self, options : dict) -> None:
        self.version = "3.6"
        self.client = None
        self.options = options
        self.running = False
        self.dummy_bg = False
        self.green_bg = False
        self.endpoints = ["https://prd-game-a-granbluefantasy.akamaized.net/", "https://prd-game-a1-granbluefantasy.akamaized.net/", "https://prd-game-a2-granbluefantasy.akamaized.net/", "https//prd-game-a3-granbluefantasy.akamaized.net/", "https://prd-game-a4-granbluefantasy.akamaized.net/", "https://prd-game-a5-granbluefantasy.akamaized.net/"]
        self.regex = [
            re.compile('(30[0-9]{8})_01\\.'),
            re.compile('(20[0-9]{8})_01\\.')
        ]
        self.cache = {}
        self.custom_ani = [self.options.get('ani1', "short_attack;double;triple"), self.options.get('ani2', "ability;mortal_A;stbwait")]
        self.custom_ani_time = self.options.get('anitime', '80')
        self.enemy = self.DEFAULT_ENEMY
        self.enemy_super = []
        self.loaded_super = None
        self.battle = Battle(self)
        self.limit = asyncio.Semaphore(50)
        self.making_new_battle = False
        self.interface = None
        self.test = False
        self.download = False
    
    async def start(self) -> None:
        async with self.init_client():
            print("GBFPB v" + self.version)
            ui_task = None
            if 'nogui' not in self.options:
                self.interface = Interface(self)
            if self.interface:
                ui_task = asyncio.create_task(self.interface.run())
                asyncio.create_task(self.interface.build())
            else:
                await self.newBattle(self.options.get('battle', []))
            
            app = web.Application()
            app.add_routes([web.get('/favicon.ico', self.icon)])
            app.add_routes([web.get('/error{tail:.*}', self.notfound)])
            app.add_routes([web.get('/raid/content/index/{tail:.*}', self.getPayload)])
            app.add_routes([web.get('/assets/{tail:.*}', self.getFile)])
            app.add_routes([web.get('/rest/raid/condition/{tail:.*}', self.getCondition)])
            app.add_routes([web.get('/rest/{tail:.*}', self.genericRest)])
            app.add_routes([web.get('/{tail:.*}', self.getFile)])
            
            app.add_routes([web.post('/rest/raid/start.json', self.postStart)])
            app.add_routes([web.post('/rest/raid/normal_attack_result.json', self.postAttack)])
            app.add_routes([web.post('/rest/raid/ability_result.json', self.postAbility)])
            app.add_routes([web.post('/rest/raid/get_select_if.json', self.postSubAbility)])
            app.add_routes([web.post('/rest/raid/summon_result.json', self.postSummon)])
            app.add_routes([web.post('/rest/raid/setting', self.postOther)])
            app.add_routes([web.post('/{tail:.*}', self.postGeneric)])
            
            app.add_routes([web.head('/{tail:.*}', self.notfound)])
            runner = aiohttp.web.AppRunner(app)
            await runner.setup()
            print("Starting server on port", self.options.get('port', 8000))
            site = aiohttp.web.TCPSite(runner, port=self.options.get('port', 8000), ssl_context=self.options.get('ssl', None))
            self.running = True
            try:
                await site.start()
                while self.running:
                    await asyncio.sleep(2)
            except:
                self.running = False
            print("Stopping...")
            if self.interface is not None:
                try:
                    self.interface.apprunning = False
                    while not ui_task.done():
                        await asyncio.sleep(0.2)
                except:
                    pass
            await runner.cleanup()

    @asynccontextmanager
    async def init_client(self) -> Generator['aiohttp.ClientSession', None, None]:
        try:
            self.client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
            yield self.client
        finally:
            await self.client.close()

    async def request(self, url : str, headers : dict = {}) -> bytes:
        async with self.limit:
            response = await self.client.get(url, headers=({'connection':'keep-alive'} | headers), timeout=30)
            async with response:
                if response.status != 200: raise Exception()
                return await response.read()

    async def notfound(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.Response(status=404)

    async def icon(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        body = await self.loadFile("data/icon.ico")
        content_type = mimetypes.guess_type("data/icon.ico", strict=True)[0]
        return web.Response(body=body, content_type=content_type)

    async def getPayload(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response(await self.battle.getPayload())

    async def getFile(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        try:
            path = str(request.rel_url)[1:].split('?')[0]
            if path == "":
                if len(self.battle.characters) == 0:
                    if self.making_new_battle:
                        return web.Response(text="Please wait for the character loading to finish and refresh this page.")
                    else:
                        return web.Response(text="At least one character must be loaded.")
                body = (await self.loadFile('assets/index.html')).decode('utf-8').replace('Game.cjsScale = 0.5;', 'Game.cjsScale = 1;').replace('img_low', 'img').replace('js_low', 'js').replace('css_low', 'css').encode('utf-8') # patch in quality
                content_type = "text/html"
            elif self.dummy_bg and '/sp/raid/bg' in path:
                body = await self.loadFile("data/bgcheck.jpg")
                content_type = mimetypes.guess_type(path, strict=True)[0]
            elif self.green_bg and '/sp/raid/bg' in path:
                body = await self.loadFile("data/bggreen.jpg")
                content_type = mimetypes.guess_type(path, strict=True)[0]
            else:
                body = await self.loadFile(path)
                content_type = mimetypes.guess_type(path, strict=True)[0]
            return web.Response(body=body, content_type=content_type)
        except Exception as e:
            print(e)
            return await self.notfound(request)

    async def getCondition(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response({"condition":{"buff":[],"debuff":[],"num":1}})

    async def genericRest(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response({})

    async def postStart(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        if self.enemy != self.loaded_super:
            tmp = self.enemy
            print("Loading special attacks for enemy", tmp)
            if tmp == "":
                tmp = self.DEFAULT_ENEMY
                enemy = tmp
            tasks = []
            for i in range(1, 20):
                tasks.append(self.loadEnemySuper("assets/js/cjs/esp_{}_{}.js".format(tmp, str(i).zfill(2))))
                tasks.append(self.loadEnemySuper("assets/js/cjs/esp_{}_{}_all.js".format(tmp, str(i).zfill(2))))
            results = await asyncio.gather(*tasks)
            self.enemy_super = []
            for r in results:
                if r is not None:
                    self.enemy_super.append(r)
            self.enemy_super.sort()
            if len(self.enemy_super) == 0:
                print("Enemy has no special attacks")
            else:
                print("Special attacks set to:", ", ".join(self.enemy_super))
        return web.json_response(self.battle.getStart())

    async def loadEnemySuper(self, path : str) -> Optional[str]:
        try:
            if await self.loadFile(path) is None:
                return None
        except:
            return None
        return path.split('/')[-1].split('.')[0]

    async def postAttack(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response(self.battle.getAttack())

    async def postAbility(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response(self.battle.getAbility(await request.json()))

    async def postSubAbility(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response(self.battle.getSubAbility(await request.json()))

    async def postSummon(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response(self.battle.getSummon(await request.json()))

    async def postOther(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response({"success":True})

    async def postGeneric(self, request : aiohttp.web.Request) -> aiohttp.web.Response:
        return web.json_response()

    async def loadFile(self, path : str) -> bytes:
        # sub skill patch
        if path.startswith('assets/img/sp/assets/item/ability/s/'):
            return await self.loadFile("data/subskill/" + path.split('/')[-1])
        if path not in self.cache:
            try:
                with open(path, "rb") as f:
                    if path.startswith('assets/img/sp/cjs'):
                        return f.read()
                    else:
                        self.cache[path] = f.read()
                        return self.cache[path]
            except:
                if await self.updateFile(path):
                    return await self.loadFile(path)
        else:
            return self.cache[path]
        # weapon patch
        if path.startswith('assets/img/sp/cjs/10'):
            id = path.split('/')[-1].split('.')[0]
            return await self.loadFile("data/weapon_dummy/{}.png".format(id.replace(id[:10], id[4])))
        # index.html
        if path == "assets/index.html":
            if await self.generateHTML():
                return await self.loadFile("assets/index.html")
        raise Exception("Missing file " + path)

    async def updateFile(self, path : str) -> bool:
        url = "https://prd-game-a-granbluefantasy.akamaized.net/" + path.replace("/assets/", "AXXX").replace("assets/", "assets_en/").replace("AXXX", "/assets/")
        try:
            data = await self.request(url)
            if path.endswith(".js") or path.endswith(".json") or path.endswith(".txt") or path.endswith(".css") or path.endswith(".html"):
                data = data.decode("utf-8")
                # patching paths
                if path.endswith(".css"):
                    for e in self.endpoints:
                        data = data.replace(e + "assets_en/", "../../../../assets/")
                else:
                    for e in self.endpoints:
                        data = data.replace(e + "assets_en/", "assets/")
                data = data.replace("https://prd-game-a-granbluefantasy.akamaized.net/", "").replace("sp/assets/", "SPXXX").replace("gacha/assets/", "GXXX").replace("assets_en/", "assets/").replace("SPXXX", "sp/assets/").replace("GXXX", "gacha/assets/")
                
                # specific patches
                if path.endswith('router/app-router.js'):
                    data = data.replace('this.top()', 'this.raid(0, 60, 60)')
                data = data.encode('utf-8')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, mode="wb") as f:
                f.write(data)
            print("Downloaded", path)
            return True
        except:
            return False

    def getJSONData(self, path : str) -> Any:
        cpath = "JSONData:" + path
        if cpath not in self.cache:
            with open("data/" + path, mode='r', encoding='utf-8') as f:
                self.cache[cpath] = f.read()
        return copy.deepcopy(json.loads(self.cache[cpath].replace('enemy_4200293', 'enemy_'+(self.enemy if self.enemy != '' else self.DEFAULT_ENEMY))))

    async def generateHTML(self) -> bool:
        try:
            cnt = (await self.request("https://game.granbluefantasy.jp", headers={'User-Agent':self.USER_AGENT})).decode('utf-8')
            vregex = re.compile("Game\.version = \"(\d+)\";")
            ver = int(vregex.findall(cnt)[0])
            cnt = cnt.replace("Game.lang = 'ja';", "Game.lang = 'en';").replace('sound_flag: 1,', 'sound_flag: 0,').replace('bgm_mode: 2', 'bgm_mode: 0').replace('bgm_mode: 2', 'bgm_mode: 2').replace('se_mode: 2', 'se_mode: 2').replace('voice_mode: 2', 'voice_mode: 2').replace('bgm_volume: 100', 'bgm_volume: 100').replace('se_volume: 60', 'se_volume: 60').replace('voice_volume: 100', 'voice_volume: 100').replace('se_mode: 2', 'se_mode: 2').replace('voice_mode: 2', 'voice_mode: 2').replace('bgm_volume: 100', 'bgm_volume: 100').replace('se_volume: 60', 'se_volume: 60').replace('voice_volume: 100', 'voice_volume: 100').replace('is_enable_pc_footer:  1 ,', 'is_enable_pc_footer:  0 ,').replace('mobage_fixwindowsize:  0 ,', 'mobage_fixwindowsize:  1 ,').replace('dpi_mode: 2,', 'dpi_mode: 0,').replace('Game.cjsScale = 1;', 'Game.cjsScale = 0.5;').replace('Game.footer = {};', '').replace('return deviceRatio;', 'return 1.5;').replace('</footer>', '</footer><div id="treasure-footer-wrapper"><footer id="treasure-footer" class=""><div class="cnt-treasure-footer"><div class="prt-treasure-footer-setting"><div class="btn-treasure-footer-setting size1" data-size="0"></div><div class="btn-treasure-footer-setting size2" data-size="1"></div><div class="btn-treasure-footer-setting size3" data-size="2"></div><div class="btn-treasure-footer-setting sizefull" data-size="3"></div></div><div class="btn-treasure-footer-back"></div><div class="btn-treasure-footer-reload"></div>	<div class="btn-treasure-footer-mypage" data-href="mypage"></div><div id="prt-treasure-slider" class="prt-treasure-slider"><ul class="lis-treasures" id="treasure-list" data-treasure-max="18"></ul></div></div></footer><div id="treasure-pop"></div></div><script type="text/template" id="tpl-treasure-list"><% _.each(treasures, function(treasure) { %><% var hasRegistrationNum = +treasure.registration_number > 0, displayNumber = hasRegistrationNum && +treasure.number > 999 ? \'999+\' : treasure.number %><li class="lis-treasure"><figure class="prt-treasure-wrapper" data-item-id="<%= treasure.item_id %>"><img src="assets/img_low/sp/assets/item/article/m/<%= treasure.image %>.jpg" class="img-treasure"><figcaption class="txt-treasure-num"><%= displayNumber %><% if(hasRegistrationNum){ %>/<%= treasure.registration_number %><% } %></figcaption></figure></li><% }); %></script>').replace('https://prd-game-a-granbluefantasy.akamaized.net/', '').replace('https://prd-game-a1-granbluefantasy.akamaized.net/', '').replace('https://prd-game-a2-granbluefantasy.akamaized.net/', '').replace('https://prd-game-a3-granbluefantasy.akamaized.net/', '').replace('https://prd-game-a4-granbluefantasy.akamaized.net/', '').replace('https://prd-game-a5-granbluefantasy.akamaized.net/', '').replace('<script type="text/javascript" src="https://aimg-link.gree.net/js/gree.js"></script>\n', '').replace("https://game.granbluefantasy.jp/", "").replace(str(ver) + '/', '').replace(str(ver), 'VERSION').replace('<title>グランブルーファンタジー</title>', '<title>GBFBP v{}</title>'.format(self.version))
            replaced = [
                ('gree_client_id: "', '"', ''),
                ('<link rel="dns-prefetch"', '>\n', ''),
                ("window.clientData = clientData;", "})();", "\n")
            ]
            a = cnt.find("require(['lib/common'], function() {")
            for r in replaced:
                a = 0
                while True:
                    a = cnt.find(r[0], a+1)
                    if a == -1: break
                    a += len(r[0])
                    b = cnt.find(r[1], a)
                    if b == -1: break
                    cnt = cnt[:a] + r[2] + cnt[b:]
            os.makedirs(os.path.dirname("assets/index.html"), exist_ok=True)
            with open("assets/index.html", mode="w", encoding="utf-8") as f:
                f.write(cnt)
            return True
        except:
            return False

    async def newBattle(self, elements : list) -> bool:
        if self.making_new_battle or len(elements) == 0: return False
        self.making_new_battle = True
        test = self.test
        download = self.download
        print("Attempting to initialize the battle scene with the following elements:", ' '.join(elements))
        battle = Battle(self)
        ids = []
        errors = []
        for e in elements:
            e = e.strip()
            if e == "": continue
            tmp = e.split('_')
            id = tmp[0]
            style = ''
            uncap = 1
            gender = 0
            other = ''
            try:
                id = int(id)
            except:
                try: id = int(await self.search_id_on_wiki(id))
                except: id = None
                if id is None:
                    errors.append(e)
                    continue
            for i in range(1, len(tmp)):
                try:
                    if tmp[i].startswith('st'):
                        style = tmp[i]
                    elif tmp[i].lower() in ['gran', 'djeeta']:
                        gender = 0 if tmp[i].lower() == 'gran' else 1
                    else:
                        try:
                            uncap = int(tmp[i])
                        except:
                            other = tmp[i]
                except:
                    pass
            ids.append((id, uncap, style, gender, other, e))
        nd = 0
        ns = 0
        for id in ids:
            try:
                if id[0] >= 3000000000 and id[0] < 4000000000:
                    if len(battle.characters) >= 4:
                        nd += 1
                    else:
                        e = Character(self, id[5])
                        await e.build(id[0], id[1], id[2], id[3], test, download)
                        if e.loaded:
                            battle.characters.append(e)
                        else:
                            errors.append(id[5])
                elif id[0] >= 2000000000 and id[0] < 3000000000:
                    if len(battle.summons) >= 5:
                        ns += 1
                    else:
                        e = Summon(self, id[5])
                        await e.build(id[0], id[1], id[2], id[3], test, download)
                        if e.loaded:
                            battle.summons.append(e)
                        else:
                            errors.append(id[5])
                elif id[0] >= 1000000000 and id[0] < 2000000000:
                    if len(battle.characters) >= 4:
                        nd += 1
                    else:
                        e = Weapon(self, id[5])
                        await e.build(id[0], id[1], id[2], id[3], test, download)
                        if e.loaded:
                            battle.characters.append(e)
                        else:
                            errors.append(id[5])
                else:
                    if len(battle.characters) >= 4:
                        nd += 1
                    else:
                        e = MC(self, id[5])
                        await e.build(id[0], id[1], id[4], id[3], test, download) # pass other as style
                        if e.loaded:
                            battle.characters.append(e)
                        else:
                            errors.append(id[5])
            except:
                errors.append(id[5])
        battle.bg = self.battle.bg
        self.battle = battle
        print(len(self.battle.characters), "characters")
        print(len(self.battle.summons), "summons")
        print(len(errors), "errors")
        print("Skipped", nd, "characters")
        print("Skipped", ns, "summons")
        if self.interface is not None and self.interface.apprunning:
            self.interface.bell()
            self.interface.notifications.append("The Battle is ready.\nPlease press OK and reload the page." + ("" if len(errors) == 0 else "\nThe following lines couldn't be processed due to errors:\n" + "\n".join(errors)) + ("" if nd == 0 else "\n" + str(nd) + " Weapon/Character(s) didn't get processed (Max 4)") + ("" if ns == 0 else "\n" + str(ns) + " Summon(s) didn't get processed (Max 5)"))
        self.making_new_battle = False
        return True

    def fixCase(self, terms : str) -> str: # function to fix the case (for wiki search requests)
        terms = terms.split(' ')
        fixeds = []
        for term in terms:
            fixed = ""
            up = False
            special = {"and":"and", "of":"of", "de":"de", "for":"for", "the":"the", "(sr)":"(SR)", "(ssr)":"(SSR)", "(r)":"(R)"} # case where we don't don't fix anything and return it
            if term.lower() in special:
                fixeds.append(special[term.lower()])
                continue
            for i in range(0, len(term)): # for each character
                if term[i].isalpha(): # if letter
                    if term[i].isupper(): # is uppercase
                        if not up: # we haven't encountered an uppercase letter
                            up = True
                            fixed += term[i] # save
                        else: # we have
                            fixed += term[i].lower() # make it lowercase and save
                    elif term[i].islower(): # is lowercase
                        if not up: # we haven't encountered an uppercase letter
                            fixed += term[i].upper() # make it uppercase and save
                            up = True
                        else: # we have
                            fixed += term[i] # save
                    else: # other characters
                        fixed += term[i] # we just save
                elif term[i] == "/" or term[i] == ":" or term[i] == "#" or term[i] == "-": # we reset the uppercase detection if we encounter those
                    up = False
                    fixed += term[i]
                else: # everything else,
                    fixed += term[i] # we save
            fixeds.append(fixed)
        return "_".join(fixeds) # return the result

    async def search_id_on_wiki(self, sps : str) -> Optional[str]: # search on gbf.wiki to match a name to its id
        try:
            data = (await self.request("https://gbf.wiki/" + parse.quote(self.fixCase(sps)), headers={'User-Agent':self.USER_AGENT})).decode('utf-8')
            for r in self.regex:
                group = r.findall(data)
                if len(group) > 0:
                    return group[0]
            return None
        except:
            return None

    def printex(self, exception : Exception) -> None:
        print("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))

class BaseElement():
    def __init__(self, server : GBFBP, origin: str) -> None:
        self.server = server
        self.origin = origin
        self.loaded = False
        self.id = None
        self.uncap = None
        self.style = None
        self.gender = None
        self.verified = {}
        self.what = "undefined"
        
    async def verify(self, target : str, testing=False, download=False) -> None:
        if target not in self.verified:
            r = await self.loadManifest(target, download)
        else:
            r = False
        if (not global_debug and not r) or target not in self.verified:
            return
        if not r or testing:
            if not global_debug: raise Exception()
            try:
                data = (await self.server.loadFile('assets/js/cjs/{}.js'.format(target))).decode('utf-8')
                d = Debug(self, target)
                await d.do(data)
            except Exception as e:
                self.server.printex(e)
                self.verified.pop(target)

    async def loadManifest_subroutine(self, target : str, el : dict, download : bool = False) -> bool:
        try:
            path = "assets/img" + el['src'].split('?')[0]
            self.verified[target].append(el['id'])
            if download: await self.server.updateFile(path)
            await self.server.loadFile(path)
            return True
        except:
            return False

    async def loadManifest(self, target : str, download : bool = False) -> bool:
        try:
            data = (await self.server.loadFile('assets/js/model/manifest/{}.js'.format(target))).decode('utf-8') # TODO
            st = data.find('manifest:') + len('manifest:')
            ed = data.find(']', st) + 1
            data = json.loads(data[st:ed].replace('Game.imgUri+', '').replace('src:', '"src":').replace('type:', '"type":').replace('id:', '"id":'))
            found = True
            self.verified[target] = []
            tasks = []
            for el in data:
                tasks.append(self.loadManifest_subroutine(target, el, download))
            results = await asyncio.gather(*tasks)
            for r in results:
                found = found and (r is True)
            return found
        except:
            return False

    async def verify_process(self, test : bool = False, download : bool = False) -> bool:
        return False

    async def build(self, id : Union[str, int], uncap : int  = 1, style : str = "", gender : int = 0, test : bool = False, download : bool = False) -> bool:
        return False

    def lookFor(self, s : str, o : str = None) -> Optional[str]:
        for k in self.verified:
            if (o is None and s in k) or (o is not None and s in k and o in k):
                return k
        return None

    def lookForAll(self, s : str, o : str = None) -> Optional[str]:
        l = []
        for k in self.verified:
            if (o is None and s in k) or (o is not None and s in k and o in k):
                l.append(k)
        l.sort()
        return l

    def lookForRandom(self, s : str, o : str = None) -> Optional[str]:
        try:
            return random.choice(self.lookForAll(s, o))
        except:
            return None

class Character(BaseElement):
    MAX_HP = 999999

    def __init__(self, server : GBFBP, origin: str) -> None:
        super().__init__(server, origin)
        self.other = None
        self.has_other = False
        self.has_other_ougi = False
        self.has_win1 = False
        self.has_win2 = False
        self.has_abmotion = True
        self.ab = ""
        self.other_portrait = None
        self.portrait = None
        self.what = "npc"
        
        # stats
        self.hp = self.MAX_HP
        self.gauge = 0

    async def verify_process(self, test : bool = False, download : bool = False) -> bool:
        tasks = []
        for k in ["npc_{}_0{}{}{}".format(self.id, self.uncap, self.style, self.other), "npc_{}_0{}{}{}{}".format(self.id, self.uncap, self.style, self.gender, self.other)]:
            for s in ["", "_s2", "_s3"]:
                tasks.append(self.verify(k+s, test, download))
        for k in ["phit_{}{}{}{}".format(self.id, self.uncap, self.style, self.other), "phit_{}{}{}".format(self.id, self.style, self.other)]:
            for s in ["", "_1", "_2", "_3"]:
                tasks.append(self.verify(k+s, test, download))
        for k in ["nsp_{}_0{}{}{}".format(self.id, self.uncap, self.style, self.other), "nsp_{}_0{}{}{}{}".format(self.id, self.uncap, self.style, self.gender, self.other)]:
            for s in ["", "_s2", "_s3"]:
                for l in ['', '_a', '_b', '_c', '_e', '_f', '_g', '_h', '_i', '_j']:
                    tasks.append(self.verify(k+s+l, test, download))
        for i in range(1, 9):
            tasks.append(self.verify("ab_{}_0{}".format(self.id, i), test, download))
            tasks.append(self.verify("ab_all_{}_0{}".format(self.id, i), test, download))
        await asyncio.gather(*tasks)
        k = self.lookFor('npc_')
        if k is None: return False
        data = (await self.server.loadFile('assets/js/cjs/{}.js'.format(k))).decode('utf-8')
        if k + "_win_1=" in data: self.has_win1 = True
        if k + "_win_2=" in data: self.has_win2 = True
        if "_ab_motion." not in data and "_ab_motion=" not in data: self.has_abmotion = False
        self.ab = []
        ab_all = []
        for k in self.verified:
            if k.startswith("ab"):
                if '_all_' in k: ab_all.append(k[-1])
                else: self.ab.append(k[-1])
        self.ab.sort()
        ab_all.sort()
        self.ab = ''.join(self.ab) + '|' + ''.join(ab_all)
        # no nsp, check inferior uncap ones
        if self.lookFor('nsp_') is None:
            for uncap in range(self.uncap-1, 0, -1):
                tasks = []
                for k in ["nsp_{}_0{}{}{}".format(self.id, uncap, self.style, self.other), "nsp_{}_0{}{}{}{}".format(self.id, uncap, self.style, self.gender, self.other)]:
                    for s in ["", "_s2", "_s3"]:
                        for l in ['', '_a', '_b', '_c', '_e', '_f', '_g', '_h', '_i', '_j']:
                            tasks.append(self.verify(k+s+l, test, download))
                await asyncio.gather(*tasks)
                if self.lookFor('nsp_') is not None:
                    break
        return True

    async def build(self, id : Union[str, int], uncap : int  = 1, style : str = "", gender : int = 0, test : bool = False, download : bool = False) -> bool:
        self.id = str(id)
        self.uncap = uncap
        self.style = style
        self.gender = "_{}".format(gender)
        self.other = ""
        # check main form
        if not await self.verify_process(test, download): return False
        cpy_verified = self.verified
        # check other
        self.verified = {}
        self.has_other = True
        self.other = '_f1'
        if not await self.verify_process(test, download): self.has_other = False
        self.other = ''
        self.verified = cpy_verified | self.verified
        # check portrait
        for f in ["{}_0{}{}".format(self.id, self.uncap, self.style), "{}_0{}{}_01".format(self.id, self.uncap, self.style), "3040097000_01"]:
            try:
                await self.server.loadFile("assets/img_low/sp/assets/npc/raid_normal/" + f + ".jpg")
                self.portrait = f
                break
            except:
                pass
        if self.has_other and self.portrait != "3040097000_01":
            for f in ["{}_0{}{}_f1".format(self.id, self.uncap, self.style), "{}_0{}{}_f1_01".format(self.id, self.uncap, self.style), "{}_0{}{}_f".format(self.id, self.uncap, self.style), "{}_0{}{}_f_01".format(self.id, self.uncap, self.style)]:
                try:
                    await self.server.loadFile("assets/img_low/sp/assets/npc/raid_normal/" + f + ".jpg")
                    self.other_portrait = f
                    break
                except:
                    pass
        self.loaded = True
        return True

class Summon(BaseElement):
    SKIP = { # hard coded summon effect fix
        2040003000 : 2, # baha
        2040056000 : 2 # lucifer
    }
    def __init__(self, server : GBFBP, origin: str) -> None:
        super().__init__(server, origin)
        self.what = "summon"
        self.multi_call = False
        self.calls = []
        self.call_count = 0

    async def verify_process(self, test : bool = False, download : bool = False) -> bool:
        skip_id = self.SKIP.get(self.id, -1)
        for uncap in range(self.uncap, 0, -1):
            if self.uncap == skip_id and skip_id == uncap: continue
            tasks = []
            for k in ["summon_{}_0{}".format(self.id, uncap)]:
                for m in ["", "_a", "_b", "_c", "_d", "_e"]:
                    for t in ["_attack", "_damage"]:
                        tasks.append(self.verify(k+m+t, test, download))
            await asyncio.gather(*tasks)
            if self.lookFor('attack') is not None and self.lookFor('damage') is not None:
                break
        if self.lookFor('attack') is None or self.lookFor('damage') is None:
            tasks = []
            for k in ["summon_{}".format(self.id)]:
                for m in ["", "_a", "_b", "_c", "_d", "_e"]:
                    for t in ["_attack", "_damage"]:
                        tasks.append(self.verify(k+m+t, test, download))
            await asyncio.gather(*tasks)
        if (self.lookFor('attack') is None and self.lookFor('damage') is not None) or (self.lookFor('attack') is not None and self.lookFor('damage') is None):
            return False
        elif self.lookFor('attack') is None and self.lookFor('damage') is None:
            await self.verify("summon_{}".format(self.id), test, download)
            f = self.lookFor('summon_')
            if f is None:
                return False
            self.calls.append((f,))
        else:
            atks = self.lookForAll('attack')
            dmgs = self.lookForAll('damage')
            if len(atks) >= len(dmgs):
                for i in range(len(atks)):
                    if i >= len(dmgs):
                        self.calls.append((atks[i], dmgs[-1]))
                    else:
                        self.calls.append((atks[i], dmgs[i]))
            else:
                for i in range(len(dmgs)):
                    if i >= len(atks):
                        self.calls.append((atks[-1], dmgs[i]))
                    else:
                        self.calls.append((atks[i], dmgs[i]))
        if self.lookFor('_a_attack') is not None: self.multi_call = True
        return True

    async def build(self, id : Union[str, int], uncap : int  = 1, style : str = "", gender : int = 0, test : bool = False, download : bool = False) -> bool:
        self.id = str(id)
        self.uncap = uncap
        # check main form
        if not await self.verify_process(test, download): return False
        # check portrait
        for f in ["{}_0{}".format(self.id, self.uncap), "{}".format(self.id), "2030002000"]:
            try:
                await self.server.loadFile("assets/img_low/sp/assets/summon/raid_normal/" + f + ".jpg")
                self.portrait = f
                break
            except:
                pass
        self.loaded = True
        return True

    def get_call(self):
        if len(self.calls) == 0: return ("", "")
        c = self.calls[self.call_count]
        self.call_count = (self.call_count + 1) % len(self.calls)
        return c

class Weapon(Character):
    CLASSES = [
        ("bsk_sw_{}_01", "100301_sw_{}_01"), # sword
        ("gzk_kn_{}_01", "140301_kn_{}_01"), # dagger
        ("aps_sp_{}_01", "190301_sp_{}_01"), # spear
        ("lmb_ax_{}_01", "410301_ax_{}_01"), # axe
        ("wrk_wa_{}_01", "130301_wa_{}_01"), # staff
        ("kks_gu_{}_01", "290201_gu_{}_01"), # gun
        ("rsr_me_{}_01", "160301_me_{}_01"), # melee
        ("rbn_bw_{}_01", "440301_bw_{}_01"), # bow
        ("els_mc_{}_01", "180301_mc_{}_01"), # harp
        ("kng_kt_{}_01", "220301_kt_{}_01") # katana
    ]
    def __init__(self, server, origin):
        super().__init__(server, origin)
        self.what = "weapon"
        self.melee = False
        self.class_cjs = None
        self.class_id = None

    async def verify_process(self, test : bool = False, download : bool = False) -> bool:
        phit = False
        sp = False
        uncap = self.uncap
        while uncap > 0:
            u = self.gender if uncap == 1 else uncap
            su = "" if uncap == 1 else "_0" + str(uncap)
            tasks = []
            if not phit:
                for s in ["", "_1", "_2", "_3"]:
                    tasks.append(self.verify("phit_{}{}{}".format(self.id, su, s), test, download))
            if not sp:
                for k in ["sp_{}".format(self.id), "sp_{}_{}".format(self.id, u), "sp_{}_{}_s2".format(self.id, u), "sp_{}_s2".format(self.id)]:
                    tasks.append(self.verify(k, test, download))
            if len(tasks) > 0:
                await asyncio.gather(*tasks)
            phit = self.lookFor('phit_') is not None
            sp = self.lookFor('sp_') is not None
            if phit and sp: break
            uncap -= 1
        if not sp: return False
        return True

    async def build(self, id : Union[str, int], uncap : int  = 1, style : str = "", gender : int = 0, test : bool = False, download : bool = False) -> bool:
        self.gender = gender
        self.style = ""
        self.id = str(id)
        self.uncap = uncap
        self.other = ""
        x = (int(self.id) // 100000) % 10
        self.melee = (x == 6)
        x = self.CLASSES[x]
        self.class_cjs = x[0].format(self.gender)
        self.class_id = x[1].format(self.gender)
        self.portrait = self.class_id
        # check main form
        if not await self.verify_process(test, download): return False
        self.loaded = True
        return True

class MC(Weapon):
    LOOKUP = { # need to be manually updated..... :(
        "150201": ["dkf_sw", "dkf_kn"], # dark fencer
        "200201": ["acm_kn", "acm_gu"], # alchemist
        "310401": ["mcd_sw"], # mac do
        "130201": ["hrm_wa", "hrm_kn"], # hermit
        "120401": ["hlr_wa", "hlr_sp"], # iatromantis
        "150301": ["csr_sw", "csr_kn"], # chaos ruler
        "170201": ["sdw_bw", "sdw_gu"], # sidewinder
        "240201": ["gns_gu"], # gunslinger
        "360001": ["vee_me"], # vyrn suit
        "310701": ["fal_sw"], # fallen
        "400001": ["szk_kt"], # zhuque
        "450301": ["rlc_sw", "rlc_gu"], # relic buster
        "140301": ["gzk_kn", "gzk_gu"], # bandit tycoon
        "110001": ["kni_sw", "kni_sp"], # knight
        "270301": ["ris_mc"], # rising force
        "290201": ["kks_gu"], # mechanic
        "190101": ["drg_sp", "drg_ax"], # dragoon
        "140201": ["hky_kn", "hky_gu"], # hawkeye
        "240301": ["sol_gu"], # soldier
        "120301": ["sag_wa", "sag_sp"], # sage
        "120101": ["cle_wa", "cle_sp"], # cleric
        "150101": ["ars_sw", "ars_kn"], # arcana dueler
        "130301": ["wrk_wa", "wrk_kn"], # warlock
        "130401": ["mnd_wa", "mnd_kn"], # manadiver
        "310601": ["edg_sw"], # eternal 2
        "120001": ["pri_wa", "pri_sp"], # priest
        "180101": ["mst_kn", "mst_mc"], # bard
        "200301": ["dct_kn", "dct_gu"], # doctor
        "220201": ["smr_bw", "smr_kt"], # samurai
        "140001": ["thi_kn", "thi_gu"], # thief
        "370601": ["bel_me"], # belial 1
        "370701": ["ngr_me"], # cook
        "330001": ["sry_sp"], # qinglong
        "370501": ["phm_me"], # anime s2 skin
        "440301": ["rbn_bw"], # robin hood
        "160201": ["ogr_me"], # ogre
        "210301": ["mhs_me", "mhs_kt"], # runeslayer
        "310001": ["lov_sw"], # lord of vermillion
        "370801": ["frb_me"], # belial 2
        "180201": ["sps_kn", "sps_mc"], # superstar
        "310301": ["chd_sw"], # attack on titan
        "125001": ["snt_wa"], # santa
        "110301": ["spt_sw", "spt_sp"], # spartan
        "310801": ["ykt_sw"], # yukata
        "110201": ["hsb_sw", "hsb_sp"], # holy saber
        "230301": ["glr_sw", "glr_kt"], # glorybringer
        "130101": ["srr_wa", "srr_kn"], # sorcerer
        "430301": ["mnk_wa", "mnk_me"], # monk
        "280301": ["msq_kn"], # masquerade
        "250201": ["wmn_wa"], # mystic
        "160001": ["grp_me"], # grappler
        "110101": ["frt_sw", "frt_sp"], # sentinel
        "270201": ["drm_mc"], # taiko
        "300301": ["crs_sw", "crs_kt"], # chrysaor
        "360101": ["rac_gu"], # platinum sky 2
        "300201": ["gda_sw", "gda_kt"], # gladiator
        "100101": ["wrr_sw", "wrr_ax"], # warrior
        "170001": ["rng_bw", "rng_gu"], # ranger
        "280201": ["dnc_kn"], # dancer
        "410301": ["lmb_ax", "lmb_mc"],
        "100001": ["fig_sw", "fig_ax"], # fighter
        "180301": ["els_kn", "els_mc"], # elysian
        "250301": ["knd_wa"], # nekomancer
        "260201": ["asa_kn"], # assassin
        "370301": ["kjm_me"], # monster 3
        "140101": ["rdr_kn", "rdr_gu"], # raider
        "180001": ["hpt_kn", "hpt_mc"], # superstar
        "370001": ["kjt_me"], # monster 1
        "165001": ["stf_me"], # street fighter
        "160301": ["rsr_me"], # luchador
        "100201": ["wms_sw", "wms_ax"], # weapon master
        "170301": ["hdg_bw", "hdg_gu"], # nighthound
        "230201": ["sdm_sw", "sdm_kt"], # swordmaster
        "310201": ["swm_sw"], # summer
        "190301": ["aps_sp", "aps_ax"], # apsaras
        "100401": ["vkn_sw", "vkn_ax"], # viking
        "150001": ["enh_sw", "enh_kn"], # enhancer
        "220301": ["kng_bw", "kng_kt"], # kengo
        "120201": ["bis_wa", "bis_sp"], # bishop
        "310101": ["ani_sw"], # anime season 1
        "130001": ["wiz_wa", "wiz_kn"], # wizard
        "185001": ["idl_kn", "idl_mc"], # idol
        "100301": ["bsk_sw", "bsk_ax"], # berserker
        "160101": ["kun_me"], # kung fu artist
        "370201": ["kjb_me"], # monster 2
        "110401": ["pld_sw", "pld_sp"], # paladin
        "310501": ["cnq_sw"], # eternal 1
        "310901": ["vss_sw"], # versus skin
        "190001": ["lnc_sp", "lnc_ax"], # lancer
        "420301": ["cav_sp", "cav_gu"], # cavalier
        "190201": ["vkr_sp", "vkr_ax"], # valkyrie
        "260301": ["tmt_kn"], # tormentor
        "210201": ["nnj_me", "nnj_kt"], # ninja
        "370401": ["ybk_me"], # bird
        "320001": ["sut_kn"], # story dancer
        "170101": ["mrk_bw", "mrk_gu"], # archer
        "311001": ["gkn_sw"], # school
        "340001": ["gnb_ax"], # xuanwu
        "360201": ["ebi_gu"], # premium friday
        "370901": ["byk_me"], # baihu
        "460301": ["ymt_sw", "ymt_kt"], # yamato
        "140401": ["kig_kn", "kig_gu"], # king
        "311101": ["vs2_sw"], # versus rising skin
        "311201": ["tbs_sw"], # relink skin
        "400101": ["nir_kt"], # 2B skin
        "150401": ["omj_kn", "omj_kt"] # onmyoji
    }
    OUGI = {
        "320001": "1040115000", # school dancer
        "340001": "1040315700", # xuanwu
        "400001": "1040913700", # zhuque
        "330001": "1040216600", # qinglong
        "370901": "1040617400", # baihu
        "310501": "1040016700", # eternal 1
        "310601": "1040016800", # eternal 2
        "360101": "1040508600", # platinum sky 2
        "370801": "1040616000", # belial 2
        "310701": "1040016900", # fallen
        "370001": "1040610300", # monster 1
        "310901": "1040019100", # versus
        "370201": "1040610200", # monster 2
        "370301": "1040610400", # monster 3
        "370601": "1040614400", # belial 1
        "370701": "1040615300", # cook
        "310001": "1040009100", # lord of vermillion
        "310801": "1040018800", # yukata
        "311001": "1040020200", # school
        "310301": "1040014200", # attack on titan
        "360201": "1040515800", # premium friday
        "311101": "1040025000", # versus skin
        "311201": "1040025600", # relink skin
        "400101": "1040916100" # 2B skin
    }
    PLACEHOLDER = {
        "sw": "1010000000",
        "kn": "1010100000",
        "sp": "1010200000",
        "ax": "1010300000",
        "wa": "1010400000",
        "gu": "1010500000",
        "me": "1010600000",
        "bw": "1010700000",
        "mc": "1010800000",
        "kt": "1010900000"
    }
        
    def __init__(self, server, origin):
        super().__init__(server, origin)
        self.what = "mc"
        self.class_cjs = None

    async def verify_process(self, test : bool = False, download : bool = False) -> bool:
        tasks = []
        for k in ["phit_{}".format(self.id), "phit_{}_1".format(self.id), "phit_{}_2".format(self.id), "phit_{}_3".format(self.id), "sp_{}".format(self.id), "sp_{}_{}".format(self.id, self.gender), "sp_{}_{}_s2".format(self.id, self.gender), "sp_{}_s2".format(self.id)]:
            tasks.append(self.verify(k, test, download))
        await asyncio.gather(*tasks)
        if self.lookFor('sp_') is None:
            self.verified['sp_sw_01410001'] = ['sp_sw_01410001']
        return True

    async def build(self, id : Union[str, int], uncap : int  = 1, style : str = "", gender : int = 0, test : bool = False, download : bool = False) -> bool:
        self.gender = gender
        self.style = ""
        self.id = str(id)
        color = self.id[-2:]
        self.id = self.id[:-2] + "01"
        self.uncap = uncap
        wpnt = style
        
        if self.id not in self.LOOKUP: return False
        cjs = None
        if style != "":
            for k in self.LOOKUP[self.id]:
                if k.split('_')[-1] == style:
                    cjs = k
        if cjs is None:
            cjs = self.LOOKUP[self.id][0]
            wpnt = cjs.split('_')[-1]
        base_wpn = self.LOOKUP[self.id][0].split('_')[-1]
        self.class_cjs = cjs + "_{}_".format(self.gender) + color
        tmp = self.id
        if color[0] != 0: tmp = tmp[:-2] + color
        self.portrait = tmp + "_" + base_wpn + "_" + str(self.gender) + "_01"
        self.id = self.OUGI.get(self.id, None)
        if self.id is None:
            self.id = self.PLACEHOLDER[wpnt]
        self.uncap = uncap
        self.other = ""
        x = (int(self.id) // 100000) % 10
        self.melee = (x == 6)
        if not await self.verify_process(test, download): return False
        self.loaded = True
        return True

class Interface(Tk.Tk): # interface
    def __init__(self, server) -> None:
        self.parent = None
        self.server = server
        self.loop = asyncio.get_event_loop()
        self.apprunning = True
        self.default_input = "3040036000_04\n3040335000\nMirin"
        self.notifications = []
        # load settings and start thread
        self.load()
        
        # window
        Tk.Tk.__init__(self,None)
        self.title("GBFBP {}".format(self.server.version))
        self.iconbitmap('data/icon.ico')
        self.resizable(width=False, height=False) # not resizable
        self.protocol("WM_DELETE_WINDOW", self.close) # call close() if we close the window
        
        # run part
        tabs = ttk.Notebook(self)
        tabs.grid(row=1, column=0, rowspan=2, sticky="we")
        tabcontent = Tk.Frame(tabs)
        tabs.add(tabcontent, text="Run")
        Tk.Label(tabcontent, text="Character/Summon IDs (One per line)").grid(row=0, column=0, sticky="w")
        Tk.Label(tabcontent, text="Up to 4 Characters and 5 Summons").grid(row=1, column=0, sticky="w")
        
        f = ttk.Frame(tabcontent)
        f.grid(row=2, column=0, sticky="wne")
        scrollbar = Tk.Scrollbar(f) # the scroll bar
        scrollbar.pack(side=Tk.RIGHT, fill=Tk.Y)
        self.inputbox = Tk.Text(f, yscrollcommand=scrollbar.set, height=8, width=30, wrap=Tk.WORD)
        self.inputbox.pack(side=Tk.LEFT, fill=Tk.Y)
        self.inputbox.insert(Tk.END, self.default_input)
        
        self.loadbutton = Tk.Button(tabcontent, text="Apply Characters/Summons", command=lambda: self.loop.create_task(self.build()))
        self.loadbutton.grid(row=3, column=0, sticky="we")
        Tk.Button(tabcontent, text="http{}://localhost:{}".format('s' if 'ssl' in self.server.options else '', self.server.options.get('port', 8000)), command=self.open_page).grid(row=4, column=0, sticky="we")

        # setting part
        tabcontent = Tk.Frame(tabs)
        tabs.add(tabcontent, text="Settings")
        f = Tk.Frame(tabcontent)
        f.pack(side=Tk.TOP, fill=Tk.X)
        
        Tk.Button(f, text="Reload HTML", command=lambda: self.loop.create_task(self.reloadHTML())).grid(row=1, column=0, sticky="we")
        Tk.Button(f, text="Clean Disk", command=self.cleanDisk).grid(row=1, column=1, sticky="we")
        Tk.Button(f, text="Clean Memory", command=self.cleanCache).grid(row=1, column=2, sticky="we")
        
        f = Tk.Frame(tabcontent)
        f.pack(side=Tk.TOP, fill=Tk.X)
        
        self.current_bg = Tk.StringVar()
        self.current_bg.set(self.server.battle.bg)
        Tk.Label(f, text="Background").grid(row=0, column=0, sticky="w")
        self.bg = Tk.StringVar()
        self.bg.set(self.server.battle.bg)
        self.bg.trace_add("write", self.bgmodified)
        Tk.Entry(f, textvariable=self.bg).grid(row=0, column=1, stick="ws")
        Tk.Label(f, text="Enemy").grid(row=1, column=0, sticky="w")
        self.enemy = Tk.StringVar()
        self.enemy.set(self.server.enemy)
        self.enemy.trace_add("write", self.enemymodified)
        Tk.Entry(f, textvariable=self.enemy).grid(row=1, column=1, stick="ws")
        
        f = Tk.Frame(tabcontent)
        f.pack(side=Tk.TOP, fill=Tk.X)
        
        self.bgdum_var = Tk.IntVar(value=self.server.dummy_bg)
        self.bggreen_var = Tk.IntVar(value=self.server.green_bg)
        Tk.Label(f, text="Checkerboard Background").grid(row=0, column=1, sticky="ws")
        Tk.Checkbutton(f, variable=self.bgdum_var, command=self.toggleBGDum).grid(row=0, column=0, sticky="w")
        Tk.Label(f, text="Green Background").grid(row=1, column=1, sticky="ws")
        Tk.Checkbutton(f, variable=self.bggreen_var, command=self.toggleGreen).grid(row=1, column=0, sticky="w")
        Tk.Label(f, text="Refresh the page to apply the changes").grid(row=2, column=0, columnspan=3, sticky="ws")

        # animation part
        tabcontent = Tk.Frame(tabs)
        tabs.add(tabcontent, text="Animation")
        f = Tk.Frame(tabcontent)
        f.pack(side=Tk.TOP, fill=Tk.X)
        Tk.Label(f, text="Set Animation Buttons 7 and 8").grid(row=0, column=0, sticky="w")
        Tk.Label(f, text="Custom Animation 1").grid(row=1, column=0, sticky="w")
        self.custom_ani_1 = Tk.StringVar()
        self.custom_ani_1.set(self.server.custom_ani[0])
        self.custom_ani_1.trace_add("write", self.animodified1)
        Tk.Entry(f, textvariable=self.custom_ani_1).grid(row=2, column=0, columnspan=3, stick="wse")
        Tk.Label(f, text="Custom Animation 2").grid(row=3, column=0, sticky="w")
        self.custom_ani_2 = Tk.StringVar()
        self.custom_ani_2.set(self.server.custom_ani[1])
        self.custom_ani_2.trace_add("write", self.animodified2)
        Tk.Entry(f, textvariable=self.custom_ani_2).grid(row=4, column=0, columnspan=3, stick="wse")
        Tk.Label(f, text="Animation Duration").grid(row=5, column=0, sticky="w")
        self.custom_ani_time = Tk.StringVar()
        self.custom_ani_time.set(self.server.custom_ani_time)
        self.custom_ani_time.trace_add("write", self.animodifiedtime)
        Tk.Entry(f, textvariable=self.custom_ani_time).grid(row=6, column=0, columnspan=3, stick="wse")
        Tk.Label(f, text="- No Refresh required").grid(row=7, column=0, sticky="w")
        Tk.Label(f, text="- Chain animations by separating with ;").grid(row=8, column=0, sticky="w")

        self.db1v = Tk.IntVar(value=self.server.test)
        self.db2v = Tk.IntVar(value=self.server.download)
        if global_debug:
            Debug.interface(self, tabs)

    async def run(self) -> None:
        run_flag = False
        while self.apprunning:
            if self.focus_displayof() is not None and len(self.notifications) > 0:
                messagebox.showinfo(title="Notification", message=self.notifications[0])
                self.notifications.pop(0)
            if not self.server.making_new_battle:
                if run_flag:
                    self.loadbutton.configure(state=Tk.NORMAL)
                    self.loadbutton['text'] = "Apply Characters/Summons"
                    self.inputbox.configure(state=Tk.NORMAL)
                    run_flag = False
            else:
                if not run_flag:
                    self.loadbutton.configure(state=Tk.DISABLED)
                    self.loadbutton['text'] = "Please Wait..."
                    self.inputbox.configure(state=Tk.DISABLED)
                    run_flag = True
            self.update()
            await asyncio.sleep(0.02)
        try: self.destroy()
        except: pass
        self.server.running = False

    def close(self): # called by the app when closed
        self.save()
        self.apprunning = False

    def load(self): # load settings.json
        try:
            with open('settings.json') as f:
                settings = json.load(f)
            self.default_input = settings.get('last_input', '')
            self.server.test = settings.get('test', False)
            self.server.download = settings.get('download', False)
            self.server.dummy_bg = settings.get('dummy_bg', False)
            self.server.green_bg = settings.get('green_bg', False)
            self.server.battle.bg = settings.get('background', self.server.battle.DEFAULT_BG)
            if self.server.battle.bg == "": self.server.battle.bg = self.server.battle.DEFAULT_BG
            self.server.enemy = settings.get('enemy', self.server.DEFAULT_ENEMY)
            if self.server.enemy == "": self.server.enemy = self.server.DEFAULT_ENEMY
            self.server.custom_ani_1 = settings.get('custom_ani_1', "short_attack;double;triple")
            self.server.custom_ani_2 = settings.get('custom_ani_2', "ability;mortal_A;stbwait")
            self.server.custom_ani_time = settings.get('custom_ani_time', "80")
        except Exception as e:
            if 'No such file or directory' not in str(e):
                self.server.printex(e)

    def save(self): # save settings.json
        try:
            with open('settings.json', 'w') as outfile:
                json.dump({'last_input':self.inputbox.get("1.0", "end")[:-1], 'test':self.server.test, 'download':self.server.download, 'version':self.server.version, 'dummy_bg':self.server.dummy_bg, 'green_bg':self.server.green_bg, 'background':self.server.battle.bg, 'enemy':self.server.enemy, 'custom_ani_1':self.server.custom_ani[0], 'custom_ani_2':self.server.custom_ani[1], 'custom_ani_time':self.server.custom_ani_time}, outfile)
        except Exception as e:
            self.server.printex(e)

    def open_page(self):
        webbrowser.open("http{}://localhost:{}".format('s' if 'ssl' in self.server.options else '', self.server.options.get('port', 8000)), new=2)

    async def build(self):
        await self.server.newBattle(self.inputbox.get("1.0", "end").split('\n'))

    def cleanDisk(self):
        try:
            shutil.rmtree("assets/")
        except:
            pass
        messagebox.showinfo("Info", "'assets' folder have been cleaned up")

    def cleanCache(self):
        self.server.cache = {}
        messagebox.showinfo("Info", "Memory Cache has been cleared")

    async def reloadHTML(self) -> None:
        if await self.server.generateHTML():
            messagebox.showinfo("Info", "A new 'index.html' has been generated, please press OK and reload the page.")
        else:
            messagebox.showerror("Error", "An error occured and 'index.html' couldn't be generated.\nIf GBF isn't in maintenance, contact the developer about this issue.\nPress OK to continue.")

    def bgmodified(self, *args) -> None:
        self.server.battle.bg = self.bg.get()

    def enemymodified(self, *args) -> None:
        self.server.enemy = self.enemy.get()

    def animodified1(self, *args) -> None:
        self.server.custom_ani[0] = self.custom_ani_1.get()

    def animodified2(self, *args) -> None:
        self.server.custom_ani[1] = self.custom_ani_2.get()

    def animodifiedtime(self, *args) -> None:
        self.server.custom_ani_time = self.custom_ani_time.get()

    def toggleBGDum(self) -> None:
        self.server.dummy_bg = (self.bgdum_var.get() != 0)

    def toggleGreen(self) -> None:
        self.server.green_bg = (self.bggreen_var.get() != 0)

    def db1(self) -> None:
        self.server.test = (self.db1v.get() != 0)

    def db2(self) -> None:
        self.server.download = (self.db2v.get() != 0)

if __name__ == '__main__':
    i = 1
    options = {}
    while i < len(sys.argv):
        match sys.argv[i]:
            case '-port':
                i += 1
                try:
                    tmp = int(sys.argv[i])
                    if tmp < 0 or tmp > 65535: raise Exception()
                    options['port'] = tmp
                    tmp = None
                except:
                    print("Invalid '-port' value:", sys.argv[i])
            case '-ssl':
                try:
                    import ssl
                    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    ssl_context.load_cert_chain('domain.crt', 'domain.key')
                    options['ssl'] = ssl_context
                except:
                    pass
            case '-ani1':
                i += 1
                options['ani1'] = sys.argv[i]
            case '-ani2':
                i += 1
                options['ani2'] = sys.argv[i]
            case '-anitime':
                i += 1
                options['anitime'] = sys.argv[i]
            case '-nogui':
                options['nogui'] = True
            case '-battle':
                tmp = []
                for j in range(i+1, len(sys.argv)):
                    if sys.argv[j].startswith('-'):
                        break
                    tmp.append(sys.argv[j])
                    i += 1
                options['battle'] = tmp
                tmp = None
        i += 1
    asyncio.run(GBFBP(options).start())