import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");
const moduleName = "凡戴尔的失落矿坑";
const moduleRoot = path.join(projectRoot, "document", "modules", moduleName);
const mapsDir = path.join(moduleRoot, "maps");
const playerImageDir = path.join(moduleRoot, "pictures", "Player", "exploration");
const battleImageDir = path.join(moduleRoot, "pictures", "DM", "battle");
const libraryDir = path.join(moduleRoot, "resource-library");

const W = 1280;
const H = 720;

const chapters = {
  goblin: "地精箭矢",
  phandalin: "凡达林",
  spider: "蜘蛛网",
  echo: "回声洞"
};

const explorationScenes = [
  scene("triboar-trail-road", "三猪小径", chapters.goblin, "forest-road", "pictures/Player/triboar-trail-exploration.png", "triboar-trail-ambush", "补给车沿林间小径前进，前方出现异常路障；先询问行进队列、侦查与调查方式。"),
  scene("goblin-trail", "地精踪迹", chapters.goblin, "forest", null, null, "隐藏小径钻入灌木和湿泥之间，适合处理追踪、陷阱、队列和警戒。"),
  scene("cragmaw-hideout-entrance", "克拉摩窝点洞口", chapters.goblin, "cave-mouth", null, "cragmaw-hideout-goblin-blind", "溪流从矮崖洞口流出，灌木丛遮住暗哨；让玩家选择靠近、潜行或侦查。"),
  scene("cragmaw-hideout-kennel", "克拉摩窝点犬舍", chapters.goblin, "cave", null, "cragmaw-hideout-kennel", "潮湿洞室里有兽栏、铁链和低吼声；可谈判、安抚、潜行或爆发战斗。"),
  scene("cragmaw-hideout-steep-passage", "克拉摩窝点陡峭通道", chapters.goblin, "cave", null, null, "狭窄斜坡连接上下层，碎石和黑暗让移动变得危险。"),
  scene("cragmaw-hideout-overpass", "克拉摩窝点天桥", chapters.goblin, "cave", null, "cragmaw-hideout-overpass", "洞穴上方横跨木桥，下方水声回荡；适合察觉哨兵、潜行或引发警报。"),
  scene("cragmaw-hideout-goblin-den", "克拉摩窝点地精休息室", chapters.goblin, "cave-camp", null, "cragmaw-hideout-goblin-den", "烟火、杂物和俘虏让局势紧绷；把派系争执和谈判空间留给玩家。"),
  scene("cragmaw-hideout-twin-pools", "克拉摩窝点双子池", chapters.goblin, "cave-water", null, "cragmaw-hideout-twin-pools", "两座蓄水池被简陋石坝拦住，守卫能利用水势制造混乱。"),
  scene("cragmaw-hideout-klarg-cave", "克拉摩窝点首领洞穴", chapters.goblin, "cave-camp", null, "cragmaw-hideout-klarg-cave", "较大的洞室堆满劫掠物和火坑，首领的宠兽与手下都在附近。"),

  scene("phandalin-arrival", "凡达林镇口", chapters.phandalin, "town", null, null, "边境小镇出现在山丘和尘土路之间，适合交付补给、打听消息和休整。"),
  scene("stonehill-inn", "石丘旅馆", chapters.phandalin, "inn", null, null, "温暖灯光、旅人闲谈和紧张流言交织，适合收集线索。"),
  scene("barthens-provisions", "巴森补给", chapters.phandalin, "shop", null, null, "货架、矿工工具和补给账本构成实用的贸易场景。"),
  scene("edermath-orchard", "埃德玛果园", chapters.phandalin, "orchard", null, null, "老果树、篱笆和退役冒险者的小屋，适合交谈与任务钩子。"),
  scene("lionshield-coster", "狮盾小贩", chapters.phandalin, "shop", null, null, "整齐货箱与蓝狮徽记暗示失货线索，适合询问地精活动。"),
  scene("miners-exchange", "凡达林矿工兑换所", chapters.phandalin, "office", null, null, "尘土、秤盘和矿权记录让这里适合交易消息与灰色委托。"),
  scene("alderleaf-farm", "阿德里夫农场", chapters.phandalin, "farm", null, null, "菜畦、谷仓与孩子讲述的秘密入口线索，适合低压探索。"),
  scene("shrine-of-luck", "幸运圣坛", chapters.phandalin, "shrine", null, null, "路边小圣坛挂着彩带和献礼，适合宗教、传闻和远行任务。"),
  scene("sleeping-giant", "沉睡的巨人", chapters.phandalin, "tavern", null, "phandalin-redbrand-street", "破旧酒馆外有红标帮游荡，气氛像火星落在干草上。"),
  scene("townmasters-hall", "镇长大厅", chapters.phandalin, "hall", null, null, "告示板、简陋办公桌和焦虑官员构成任务集散点。"),
  scene("tresendar-manor", "崔森德庄园", chapters.phandalin, "ruin", null, null, "废弃庄园俯瞰小镇，残墙和地窖入口暗示地下巢穴。"),
  scene("redbrand-hideout-cellar", "红标帮窝点地窖", chapters.phandalin, "cellar", null, null, "石阶通向潮湿地窖，水声、酒桶和暗门适合潜入。"),
  scene("redbrand-hideout-barracks", "红标帮营房", chapters.phandalin, "dungeon-room", null, "redbrand-barracks", "简陋床铺、赌具和武器散落，守卫可能松懈但人数占优。"),
  scene("redbrand-hideout-trapped-hall", "陷阱走廊", chapters.phandalin, "dungeon", null, null, "狭长走廊表面平静，地面结构和尘土痕迹暗藏危险。"),
  scene("redbrand-hideout-crypts", "崔森德墓室", chapters.phandalin, "crypt", null, "redbrand-crypts", "石棺和冷光之间有守墓亡者，适合谨慎推进。"),
  scene("redbrand-hideout-slave-pens", "奴隶围栏", chapters.phandalin, "cell", null, "redbrand-slave-pen-guards", "铁栏、哭声和守卫脚步把营救压力推到台前。"),
  scene("redbrand-hideout-armory", "军械库", chapters.phandalin, "armory", null, null, "武器架和红斗篷装备堆放整齐，可补给或伪装。"),
  scene("redbrand-hideout-storage", "储藏室和工作间", chapters.phandalin, "workshop", null, null, "木箱、工具台与灰尘覆盖的货物等待搜查。"),
  scene("redbrand-hideout-chasm", "红标帮窝点裂隙", chapters.phandalin, "chasm", null, "redbrand-nothic-chasm", "地下裂隙散发冷意，窄桥和窥视感让谈判或战斗都很危险。"),
  scene("redbrand-hideout-guard-barracks", "警卫营房", chapters.phandalin, "dungeon-room", null, "redbrand-bugbear-barracks", "粗重脚步、粗糙床铺和被欺压的小帮手制造可变局势。"),
  scene("redbrand-hideout-common-room", "公共休息室", chapters.phandalin, "tavern", null, "redbrand-common-room", "牌桌、酒杯和松散警戒适合突袭或伪装混入。"),
  scene("redbrand-hideout-workshop", "法师的工作坊", chapters.phandalin, "wizard-room", null, null, "烧瓶、书卷和炼金气味提示幕后法师的研究。"),
  scene("redbrand-hideout-glasstaff", "玻璃手杖的居所", chapters.phandalin, "wizard-room", null, "redbrand-glasstaff-quarters", "私密房间中有书桌、法器和逃生路线，适合审问或追逐。"),

  scene("triboar-wilderness", "三猪小径荒野", chapters.spider, "wilderness", null, "wilderness-goblin-patrol", "开阔荒野适合旅行遭遇、迷路、天气和营地事件。"),
  scene("conyberry", "兔莓废村", chapters.spider, "ruin", null, null, "废弃村落只剩残墙和风声，通向幽灵巢穴的路显得荒凉。"),
  scene("agathas-lair", "阿加莎的巢穴", chapters.spider, "forest-spirit", null, "agatha-hostile-banshee", "藤蔓遮住古老树屋，空气中有寒意；优先营造谨慎交涉。"),
  scene("old-owl-well", "古枭井", chapters.spider, "ruin-camp", null, "old-owl-well-zombies", "荒废瞭望塔旁搭着营地，亡者在残石间游荡。"),
  scene("wyvern-tor", "飞龙突岩", chapters.spider, "rocky-camp", null, "wyvern-tor-orc-camp", "荒石山脊下有兽人营火和岗哨，适合侦察、包抄或夜袭。"),
  scene("thundertree-arrival", "雷树废墟入口", chapters.spider, "ruin-forest", null, null, "被灰烬与藤蔓吞没的废镇散发毒雾和龙影压迫。"),
  ...numberedScenes("thundertree", chapters.spider, "雷树", "ruin-forest", [
    ["west-cottage", "最西边的小屋", "thundertree-blighted-cottages"],
    ["blighted-cottage", "枯萎的小屋", "thundertree-blighted-cottages"],
    ["brown-horse", "棕马酒馆", "thundertree-ash-zombie-tavern"],
    ["druid-watch", "德鲁伊哨点", null],
    ["blighted-farmhouse", "枯萎的农舍", "thundertree-blighted-cottages"],
    ["store-ruin", "商店废墟", "thundertree-spider-store"],
    ["dragon-tower", "龙之塔", "thundertree-dragon-tower"],
    ["old-smithy", "旧铁匠铺", "thundertree-blighted-cottages"],
    ["herbalist-shop", "草药店", null],
    ["town-square", "城镇广场", null],
    ["old-garrison", "旧卫戍营", "thundertree-ash-zombie-garrison"],
    ["weavers-cottage", "织布工小屋", "thundertree-blighted-cottages"],
    ["cultist-house", "龙之邪教徒", "thundertree-cultist-house"]
  ]),
  scene("cragmaw-castle-approach", "克拉摩堡外缘", chapters.spider, "castle-ruin", null, null, "林中废堡显露在树影后，破墙和箭孔提示强攻代价。"),
  ...numberedScenes("cragmaw-castle", chapters.spider, "克拉摩堡", "castle-ruin", [
    ["entrance", "城堡入口", "cragmaw-castle-entrance"],
    ["trapped-hall", "陷阱大厅", null],
    ["archer-post", "弓箭手岗哨", "cragmaw-castle-archer-post"],
    ["ruined-barracks", "营房废墟", "cragmaw-castle-ruined-barracks"],
    ["storeroom", "储藏室", null],
    ["hobgoblin-barracks", "大地精营房", "cragmaw-castle-hobgoblin-barracks"],
    ["banquet-hall", "宴会厅", "cragmaw-castle-banquet-hall"],
    ["dark-hall", "黑暗大厅", "cragmaw-castle-dark-hall"],
    ["shrine", "地精圣坛", "cragmaw-castle-shrine"],
    ["back-door", "后门", "cragmaw-castle-back-door"],
    ["ruined-tower", "塔楼废墟", null],
    ["guard-barracks", "警卫营房", "cragmaw-castle-guard-barracks"],
    ["owlbear-tower", "枭熊塔楼", "cragmaw-castle-owlbear-tower"],
    ["kings-quarters", "王之居所", "cragmaw-castle-king-quarters"]
  ]),
  scene("cragmaw-return-trail", "克拉摩堡返程小队", chapters.spider, "forest-road", null, "cragmaw-castle-returning-warband", "离开废堡后仍可能撞上巡逻返程者，适合追击或伏击。"),

  scene("wave-echo-cave-arrival", "回声洞入口", chapters.echo, "mine-mouth", null, null, "山坡裂口通向失落矿井，潮湿空气带着遥远轰鸣。"),
  ...numberedScenes("wave-echo", chapters.echo, "回声洞", "mine", [
    ["cave-entrance", "洞穴入口", null],
    ["mine-tunnels", "矿道", "wave-echo-mine-tunnels-stirges"],
    ["old-entrance", "旧入口", "wave-echo-old-entrance-ooze"],
    ["old-guardroom", "旧警卫室", "wave-echo-guardroom-undead"],
    ["assayers-office", "试金师办公室", null],
    ["south-barracks", "南部营房", "wave-echo-south-barracks-ghouls"],
    ["ruined-storeroom", "储物间废墟", null],
    ["fungi-cavern", "真菌洞窟", "wave-echo-fungi-cavern"],
    ["great-cavern", "大洞窟", "wave-echo-great-cavern-bugbears"],
    ["dark-pool", "黑水池", null],
    ["north-barracks", "北部营房", "wave-echo-north-barracks"],
    ["smelter-cavern", "冶炼洞窟", "wave-echo-smelter-cavern"],
    ["glittering-cavern", "明亮的洞窟", null],
    ["wizards-quarters", "法师的居所", "wave-echo-wizards-quarters"],
    ["spell-forge", "法术工厂", "wave-echo-spell-forge-guardian"],
    ["booming-cavern", "轰鸣洞窟", null],
    ["old-streambed", "古老河床", null],
    ["collapsed-cavern", "崩塌的洞窟", "wave-echo-collapsed-cavern"],
    ["temple", "杜马松的神庙", "wave-echo-temple-final"],
    ["priests-quarters", "祭司的居所", "wave-echo-priests-quarters"]
  ])
];

const combatScenes = [
  combat("triboar-trail-ambush", "三猪小径伏击", chapters.goblin, "triboar-trail-road", "forest-road", [["地精", 4]], "角色接近路障、调查遗留物或未能发现埋伏时。"),
  combat("cragmaw-hideout-goblin-blind", "洞口暗哨", chapters.goblin, "cragmaw-hideout-entrance", "cave-mouth", [["地精", 2]], "角色靠近洞口灌木或惊动暗哨。"),
  combat("cragmaw-hideout-kennel", "狼群犬舍", chapters.goblin, "cragmaw-hideout-kennel", "cave", [["狼", 3]], "角色进入犬舍、激怒或未能安抚被拴住的狼。"),
  combat("cragmaw-hideout-overpass", "天桥哨兵", chapters.goblin, "cragmaw-hideout-overpass", "cave-bridge", [["地精", 1]], "天桥哨兵发现入侵者或警报扩散。"),
  combat("cragmaw-hideout-goblin-den", "地精休息室", chapters.goblin, "cragmaw-hideout-goblin-den", "cave-camp", [["地精", 6]], "谈判失败、俘虏局势恶化或角色突袭。"),
  combat("cragmaw-hideout-twin-pools", "双子池守卫", chapters.goblin, "cragmaw-hideout-twin-pools", "cave-water", [["地精", 3]], "守卫发现角色或试图释放洪水。"),
  combat("cragmaw-hideout-klarg-cave", "首领洞穴", chapters.goblin, "cragmaw-hideout-klarg-cave", "cave-camp", [["熊地精", 1], ["狼", 1], ["地精", 2]], "角色进入首领洞穴或从其他区域引来首领。"),

  combat("phandalin-redbrand-street", "红标帮街头冲突", chapters.phandalin, "sleeping-giant", "town", [["红标恶霸", 4]], "角色在镇中公开挑战红标帮或被其威胁。"),
  combat("redbrand-barracks", "红标帮营房", chapters.phandalin, "redbrand-hideout-barracks", "dungeon-room", [["红标恶霸", 3]], "角色闯入营房、潜入失败或守卫听见动静。"),
  combat("redbrand-crypts", "墓室守卫", chapters.phandalin, "redbrand-hideout-crypts", "crypt", [["骷髅", 3]], "角色穿过墓室或触发亡者守卫。"),
  combat("redbrand-slave-pen-guards", "奴隶围栏守卫", chapters.phandalin, "redbrand-hideout-slave-pens", "cell", [["红标恶霸", 2]], "角色营救俘虏、开锁或惊动看守。"),
  combat("redbrand-nothic-chasm", "裂隙窥视者", chapters.phandalin, "redbrand-hideout-chasm", "chasm", [["独眼异怪", 1]], "角色拒绝交易、靠近藏匿物或被其袭击。"),
  combat("redbrand-bugbear-barracks", "大地精警卫营房", chapters.phandalin, "redbrand-hideout-guard-barracks", "dungeon-room", [["熊地精", 3], ["地精仆从", 1]], "角色进入警卫营房或从附近引发警报。"),
  combat("redbrand-common-room", "公共休息室混战", chapters.phandalin, "redbrand-hideout-common-room", "tavern", [["红标恶霸", 4]], "角色撞见休息中的帮众或伪装被识破。"),
  combat("redbrand-glasstaff-quarters", "玻璃手杖的居所", chapters.phandalin, "redbrand-hideout-glasstaff", "wizard-room", [["法师头目", 1]], "角色堵住幕后法师、追击或阻止其逃脱。"),

  combat("wilderness-goblin-patrol", "荒野地精巡逻", chapters.spider, "triboar-wilderness", "wilderness", [["地精", 6]], "旅行中遇到克拉摩巡逻队或追踪者。"),
  combat("wilderness-orc-raiders", "荒野兽人劫掠者", chapters.spider, "triboar-wilderness", "rocky-camp", [["兽人", 4]], "队伍在野外扎营或穿越偏僻山路时。"),
  combat("wilderness-owlbear", "荒野枭熊", chapters.spider, "triboar-wilderness", "forest", [["枭熊", 1]], "队伍误入猛兽领地或夜间遭袭。"),
  combat("agatha-hostile-banshee", "幽灵怒意", chapters.spider, "agathas-lair", "forest-spirit", [["报丧妖", 1]], "角色攻击、侮辱或破坏巢穴导致交涉破裂。"),
  combat("old-owl-well-zombies", "古枭井亡者", chapters.spider, "old-owl-well", "ruin-camp", [["僵尸", 12]], "角色靠近营地或亡者被命令阻拦。"),
  combat("wyvern-tor-orc-camp", "飞龙突岩兽人营地", chapters.spider, "wyvern-tor", "rocky-camp", [["兽人", 6], ["食人魔", 1]], "角色突袭兽人营地或被岗哨发现。"),
  combat("thundertree-blighted-cottages", "雷树枯枝怪袭击", chapters.spider, "thundertree-blighted-cottage", "ruin-forest", [["枯枝怪", 8]], "角色探索被植物占据的小屋或废墟。"),
  combat("thundertree-ash-zombie-tavern", "棕马酒馆灰烬僵尸", chapters.spider, "thundertree-brown-horse", "ruin-forest", [["灰烬僵尸", 6]], "角色进入旧酒馆或制造响动。"),
  combat("thundertree-spider-store", "蛛网商店", chapters.spider, "thundertree-store-ruin", "ruin-forest", [["巨蛛", 2]], "角色触碰蛛网、搜查货物或惊动巢穴。"),
  combat("thundertree-dragon-tower", "龙之塔", chapters.spider, "thundertree-dragon-tower", "tower", [["绿龙", 1]], "角色与幼龙谈判破裂、偷窃或挑战其领地。"),
  combat("thundertree-ash-zombie-garrison", "旧卫戍营灰烬僵尸", chapters.spider, "thundertree-old-garrison", "ruin-forest", [["灰烬僵尸", 8]], "角色进入卫戍营废墟。"),
  combat("thundertree-cultist-house", "龙之邪教徒", chapters.spider, "thundertree-cultist-house", "ruin-forest", [["邪教徒", 6]], "角色攻击邪教徒、揭穿其目的或与龙事件牵连。"),

  combat("cragmaw-castle-entrance", "城堡入口守卫", chapters.spider, "cragmaw-castle-entrance", "castle-ruin", [["地精", 4]], "角色从正门接近或被门口守卫发现。"),
  combat("cragmaw-castle-archer-post", "弓箭手岗哨", chapters.spider, "cragmaw-castle-archer-post", "castle-ruin", [["地精", 2]], "角色穿过大厅或进入箭孔控制区。"),
  combat("cragmaw-castle-ruined-barracks", "营房废墟", chapters.spider, "cragmaw-castle-ruined-barracks", "castle-ruin", [["地精", 3]], "角色撞上休息或巡逻的地精。"),
  combat("cragmaw-castle-hobgoblin-barracks", "大地精营房", chapters.spider, "cragmaw-castle-hobgoblin-barracks", "castle-room", [["大地精", 4]], "角色进入营房或警报召集守卫。"),
  combat("cragmaw-castle-banquet-hall", "宴会厅", chapters.spider, "cragmaw-castle-banquet-hall", "castle-room", [["地精", 7]], "角色闯入嘈杂宴会厅或谈判失败。"),
  combat("cragmaw-castle-dark-hall", "黑暗大厅", chapters.spider, "cragmaw-castle-dark-hall", "castle-room", [["格里克", 1]], "角色深入黑暗大厅、靠近潜伏怪物。"),
  combat("cragmaw-castle-shrine", "地精圣坛", chapters.spider, "cragmaw-castle-shrine", "shrine", [["地精祭司", 1], ["地精", 2]], "角色打扰仪式或从侧门突入。"),
  combat("cragmaw-castle-back-door", "后门箭孔", chapters.spider, "cragmaw-castle-back-door", "castle-ruin", [["地精", 2]], "角色从后门潜入或被箭孔守卫发现。"),
  combat("cragmaw-castle-guard-barracks", "警卫营房", chapters.spider, "cragmaw-castle-guard-barracks", "castle-room", [["大地精", 2]], "角色进入警卫区或战斗声引来守卫。"),
  combat("cragmaw-castle-owlbear-tower", "枭熊塔楼", chapters.spider, "cragmaw-castle-owlbear-tower", "tower", [["枭熊", 1]], "角色打开封闭塔楼或激怒被困猛兽。"),
  combat("cragmaw-castle-king-quarters", "王之居所", chapters.spider, "cragmaw-castle-kings-quarters", "castle-room", [["熊地精首领", 1], ["狼", 1], ["变形怪", 1]], "角色找到被俘矮人、谈判破裂或首领设伏。"),
  combat("cragmaw-castle-returning-warband", "返程小队", chapters.spider, "cragmaw-return-trail", "forest-road", [["大地精", 3], ["地精", 4]], "角色离堡后遭遇返程巡逻或尾随。"),

  combat("wave-echo-mine-tunnels-stirges", "矿道蝙蝠群", chapters.echo, "wave-echo-mine-tunnels", "mine", [["吸血蝙蝠", 10]], "角色穿过旧矿道惊动巢群。"),
  combat("wave-echo-old-entrance-ooze", "旧入口黏液怪", chapters.echo, "wave-echo-old-entrance", "mine", [["赭冻怪", 1]], "角色靠近坍塌旧入口或搜查尸骸。"),
  combat("wave-echo-guardroom-undead", "旧警卫室亡者", chapters.echo, "wave-echo-old-guardroom", "crypt", [["僵尸", 9]], "角色进入旧警卫室或制造响动。"),
  combat("wave-echo-south-barracks-ghouls", "南部营房食尸鬼", chapters.echo, "wave-echo-south-barracks", "mine-room", [["食尸鬼", 3]], "角色搜查营房废墟。"),
  combat("wave-echo-fungi-cavern", "真菌洞窟", chapters.echo, "wave-echo-fungi-cavern", "fungi", [["紫色真菌", 4]], "角色靠近真菌丛或误判其威胁。"),
  combat("wave-echo-great-cavern-bugbears", "大洞窟巡逻", chapters.echo, "wave-echo-great-cavern", "mine-cavern", [["熊地精", 4]], "角色穿越大洞窟或被敌方巡逻撞见。"),
  combat("wave-echo-north-barracks", "北部营房", chapters.echo, "wave-echo-north-barracks", "mine-room", [["熊地精", 5]], "角色突入敌方驻扎区。"),
  combat("wave-echo-smelter-cavern", "冶炼洞窟", chapters.echo, "wave-echo-smelter-cavern", "forge", [["火焰骷髅", 1], ["僵尸", 8]], "角色靠近旧熔炉区或惊动守卫亡灵。"),
  combat("wave-echo-wizards-quarters", "法师的居所", chapters.echo, "wave-echo-wizards-quarters", "wizard-room", [["怨魂", 1]], "角色进入法师居所、交涉失败或冒犯其执念。"),
  combat("wave-echo-spell-forge-guardian", "法术工厂守卫", chapters.echo, "wave-echo-spell-forge", "forge", [["观者守卫", 1]], "角色进入法术工厂并触发守卫反应。"),
  combat("wave-echo-collapsed-cavern", "崩塌洞窟伏兵", chapters.echo, "wave-echo-collapsed-cavern", "mine-cavern", [["熊地精", 3]], "角色穿过崩塌洞窟、跨越裂谷或被伏击。"),
  combat("wave-echo-temple-final", "最终神庙", chapters.echo, "wave-echo-temple", "shrine", [["黑蜘蛛", 1], ["巨蛛", 4], ["变形怪", 1]], "角色抵达神庙并与幕后敌人决战。"),
  combat("wave-echo-priests-quarters", "祭司居所伏兵", chapters.echo, "wave-echo-priests-quarters", "mine-room", [["熊地精", 2]], "角色搜查祭司居所或敌人从侧翼包抄。")
];

function scene(id, name, chapter, kind, background, battleSceneId, scenePrompt) {
  const image = background || `pictures/Player/exploration/${id}.png`;
  return {
    id,
    name,
    chapter,
    kind,
    background: image,
    battleSceneId: battleSceneId || "",
    combatSceneId: battleSceneId || "",
    scenePrompt,
    imagePrompt: promptFor(name, kind, "exploration")
  };
}

function numberedScenes(prefix, chapter, area, kind, rooms) {
  return rooms.map(([slug, name, battleSceneId]) => scene(`${prefix}-${slug}`, `${area}：${name}`, chapter, kindForName(name, kind), null, battleSceneId, `${area}的${name}。用原创描述呈现环境、可疑细节和玩家可行动点，不复述官方房间文本。`));
}

function combat(id, name, chapter, locationId, template, monsters, trigger) {
  return {
    id,
    name,
    chapter,
    locationId,
    template,
    map: `maps/${id}.json`,
    trigger,
    monsters: expandMonsters(id, monsters),
    imagePrompt: promptFor(name, template, "battle map")
  };
}

function expandMonsters(sceneId, entries) {
  const result = [];
  for (const [name, count] of entries) {
    for (let i = 1; i <= count; i += 1) {
      result.push({ id: `${sceneId}-m${result.length + 1}`, name });
    }
  }
  return result;
}

function kindForName(name, fallback) {
  if (/神庙|圣坛|圣堂|圣坛/.test(name)) return "shrine";
  if (/塔|塔楼/.test(name)) return "tower";
  if (/营房|居所|房间|办公室/.test(name)) return "dungeon-room";
  if (/洞窟|洞穴|矿道|河床|裂谷/.test(name)) return "mine-cavern";
  if (/酒馆/.test(name)) return "tavern";
  if (/废墟|小屋|农舍|商店|铁匠铺/.test(name)) return "ruin-forest";
  return fallback;
}

function promptFor(name, kind, use) {
  return [
    `Use case: stylized-concept`,
    `Asset type: ${use} background for a fantasy tabletop session`,
    `Primary request: original atmospheric art for ${name}`,
    `Scene/backdrop: ${kind.replaceAll("-", " ")} fantasy location, inspired by classic sword-and-sorcery adventure play but not copying official maps or art`,
    `Style/medium: painterly cinematic digital illustration, no text, no watermark`,
    `Composition/framing: wide 16:9 scene with clear foreground, midground, and readable tactical space`,
    `Lighting/mood: dramatic but usable at the table, enough contrast for tokens or dialogue overlays`,
    `Constraints: original composition only; do not reproduce official D&D artwork, maps, boxed text, logos, or trade dress`
  ].join("\n");
}

function moduleAssetUrl(relativePath) {
  const encodedModule = encodeURIComponent(moduleName);
  const encodedPath = relativePath.split("/").map(encodeURIComponent).join("/");
  return `/module-assets/${encodedModule}/${encodedPath}`;
}

function buildMap(scene) {
  const template = scene.template;
  const width = template.includes("road") ? 16 : template.includes("castle") ? 14 : template.includes("town") ? 16 : 12;
  const height = template.includes("road") ? 10 : template.includes("tower") ? 12 : 10;
  const terrain = [];
  const walls = [];
  const doors = [];
  const obstacles = [];
  const annotations = [];
  const addTerrain = (x, y, type) => pushUnique(terrain, { x, y, type });
  const addWall = (x, y) => pushUnique(walls, { x, y, type: "wall" });
  const addObstacle = (x, y, type = "obstacle") => pushUnique(obstacles, { x, y, type });
  const addAnnotation = (x, y, label) => pushUnique(annotations, { x, y, label });

  if (template.includes("road") || template === "forest" || template === "wilderness") {
    for (let x = 0; x < width; x += 1) {
      for (const y of [0, 1, height - 2, height - 1]) addTerrain(x, y, "difficult");
    }
    for (let y = 2; y < height - 2; y += 1) {
      for (const x of [0, 1, width - 2, width - 1]) addTerrain(x, y, "difficult");
    }
    addAnnotation(Math.floor(width / 2), Math.floor(height / 2), template.includes("road") ? "路障" : "空地");
    addObstacle(Math.floor(width / 2), Math.floor(height / 2));
  } else if (template.includes("cave") || template.includes("mine") || template === "fungi" || template === "forge" || template === "chasm") {
    for (let x = 0; x < width; x += 1) {
      addWall(x, 0);
      addWall(x, height - 1);
    }
    for (let y = 0; y < height; y += 1) {
      addWall(0, y);
      addWall(width - 1, y);
    }
    for (let i = 0; i < Math.floor(width * height * 0.08); i += 1) {
      const x = 2 + ((hash(`${scene.id}-rock-${i}`) % (width - 4)) | 0);
      const y = 2 + ((hash(`${scene.id}-stone-${i}`) % (height - 4)) | 0);
      addTerrain(x, y, template === "cave-water" ? "water" : "difficult");
    }
    if (template.includes("water") || scene.id.includes("pool") || scene.id.includes("dark-pool")) {
      for (let x = 3; x < width - 3; x += 1) addTerrain(x, Math.floor(height / 2), "water");
    }
    if (template === "chasm") {
      for (let y = 1; y < height - 1; y += 1) addTerrain(Math.floor(width / 2), y, "difficult");
      addAnnotation(Math.floor(width / 2), Math.floor(height / 2), "裂隙");
    }
    addAnnotation(1, Math.floor(height / 2), "入口");
  } else {
    for (let x = 0; x < width; x += 1) {
      addWall(x, 0);
      addWall(x, height - 1);
    }
    for (let y = 0; y < height; y += 1) {
      addWall(0, y);
      addWall(width - 1, y);
    }
    doors.push({ x: Math.floor(width / 2), y: height - 1, type: "door", open: false });
    for (let i = 0; i < 8; i += 1) {
      const x = 2 + (hash(`${scene.id}-obj-${i}`) % (width - 4));
      const y = 2 + (hash(`${scene.id}-furn-${i}`) % (height - 4));
      addObstacle(x, y);
    }
    addAnnotation(Math.floor(width / 2), Math.floor(height / 2), labelForTemplate(template));
  }

  const monsters = positionMonsters(scene.monsters, width, height, walls);
  scene.monsters = monsters;
  const layers = {
    terrain,
    walls,
    doors,
    obstacles,
    annotations,
    fog: [],
    effects: [],
    dmNotes: [{ id: "trigger", x: 1, y: 1, text: scene.trigger }]
  };
  return {
    id: scene.id,
    name: scene.name,
    width,
    height,
    gridSize: 48,
    background: {
      url: moduleAssetUrl(`pictures/DM/battle/${scene.id}.png`),
      width: W,
      height: H,
      opacity: 0.72
    },
    grid: { size: 80, originX: 0, originY: 0, scale: 1, offsetX: 0, offsetY: 0 },
    terrain,
    annotations,
    layers
  };
}

function positionMonsters(monsters, width, height, walls) {
  const blocked = new Set(walls.map((item) => `${item.x},${item.y}`));
  const points = [];
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      if (!blocked.has(`${x},${y}`)) points.push([x, y]);
    }
  }
  return monsters.map((monster, index) => {
    const [x, y] = points[(index * 5 + 3) % points.length];
    return { ...monster, x, y };
  });
}

function labelForTemplate(template) {
  if (template.includes("shrine")) return "祭坛";
  if (template.includes("tower")) return "塔楼";
  if (template.includes("tavern")) return "牌桌";
  if (template.includes("wizard")) return "法器";
  if (template.includes("crypt")) return "石棺";
  if (template.includes("castle")) return "残墙";
  return "掩体";
}

function pushUnique(items, next) {
  if (!items.some((item) => item.x === next.x && item.y === next.y)) items.push(next);
}

function ensureDirs() {
  for (const dir of [mapsDir, playerImageDir, battleImageDir, libraryDir]) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function writeJson(file, data) {
  fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

function writeMarkdown(file, text) {
  fs.writeFileSync(file, text.trimEnd() + "\n", "utf8");
}

function buildLibrary() {
  ensureDirs();
  for (const item of explorationScenes) {
    const relative = item.background;
    if (relative.startsWith("pictures/Player/exploration/")) {
      writeProceduralPng(path.join(moduleRoot, relative), item.id, item.kind);
    }
  }

  const maps = [];
  for (const item of combatScenes) {
    writeProceduralPng(path.join(battleImageDir, `${item.id}.png`), item.id, item.template);
    const mapData = buildMap(item);
    maps.push(mapData);
    writeJson(path.join(moduleRoot, item.map), mapData);
  }

  const scenesJson = {
    moduleName,
    version: "resource-library-1",
    assetPolicy: "原创资源；用于兼容跑团，不复制官方地图、原文或美术。",
    openingSceneId: "triboar-trail-road",
    explorationScenes,
    combatScenes: combatScenes.map(({ template, locationId, imagePrompt, ...scene }) => scene)
  };
  writeJson(path.join(moduleRoot, "scenes.json"), scenesJson);

  const prompts = {
    styleGuide: "所有提示词都要求原创构图，不复刻官方地图、插图、版式或文字。",
    exploration: explorationScenes.map(({ id, name, chapter, kind, background, imagePrompt }) => ({ id, name, chapter, kind, background, imagePrompt })),
    battle: combatScenes.map(({ id, name, chapter, template, map, imagePrompt }) => ({ id, name, chapter, template, map, imagePrompt }))
  };
  writeJson(path.join(libraryDir, "image-prompts.json"), prompts);
  writeJson(path.join(libraryDir, "resource-index.json"), {
    moduleName,
    counts: {
      explorationScenes: explorationScenes.length,
      combatScenes: combatScenes.length,
      explorationBackgrounds: explorationScenes.filter((item) => item.background.includes("/exploration/")).length + 1,
      battleBackgrounds: combatScenes.length,
      maps: maps.length
    },
    explorationScenes: explorationScenes.map(({ id, name, chapter, background, battleSceneId }) => ({ id, name, chapter, background, battleSceneId })),
    combatScenes: combatScenes.map(({ id, name, chapter, map, trigger, monsters }) => ({ id, name, chapter, map, trigger, monsters: monsters.map((monster) => monster.name) }))
  });

  writeMarkdown(path.join(libraryDir, "README.md"), readme());
  writeMarkdown(path.join(libraryDir, "encounter-checklist.md"), encounterChecklist());
  writeMarkdown(path.join(libraryDir, "exploration-scenes.md"), explorationChecklist());
}

function readme() {
  return `# 凡戴尔的失落矿坑资源库

这套资源用于本项目的跑团应用，提供原创探索背景、战斗底图、遭遇地图 JSON 和 DM 检索清单。它是兼容资源，不复制官方地图、朗读文本、房间原文或官方美术。

## 内容

- 探索场景：${explorationScenes.length} 个，登记在 \`../scenes.json\`
- 战斗场景：${combatScenes.length} 个，地图在 \`../maps/\`
- 探索背景：\`../pictures/Player/exploration/\`
- 战斗底图：\`../pictures/DM/battle/\`
- AI 重绘提示词：\`image-prompts.json\`

## 使用建议

1. 应用读取 \`scenes.json\` 后，开场仍从 \`triboar-trail-road\` 进入。
2. 每个探索场景都带有 \`battleSceneId\` / \`combatSceneId\`，为空时表示主要是社交、线索、陷阱或过渡场景。
3. 当前 PNG 是程序化原创草图，适合先跑通流程；需要更精美图片时，用 \`image-prompts.json\` 中对应提示词重绘后替换同名文件。
4. 地图是抽象战术布局，不是官方地图复刻；如要贴合你桌上的版本，可在地图编辑器里微调墙、门、障碍和网格。`;
}

function encounterChecklist() {
  const lines = ["# 战斗场景清单", ""];
  for (const chapter of Object.values(chapters)) {
    lines.push(`## ${chapter}`, "");
    for (const item of combatScenes.filter((scene) => scene.chapter === chapter)) {
      const monsters = item.monsters.map((monster) => monster.name).join("、");
      lines.push(`- [ ] ${item.name} (\`${item.id}\`)：${monsters}。触发：${item.trigger}`);
    }
    lines.push("");
  }
  return lines.join("\n");
}

function explorationChecklist() {
  const lines = ["# 探索地点清单", ""];
  for (const chapter of Object.values(chapters)) {
    lines.push(`## ${chapter}`, "");
    for (const item of explorationScenes.filter((scene) => scene.chapter === chapter)) {
      const battle = item.battleSceneId ? ` -> \`${item.battleSceneId}\`` : "";
      lines.push(`- ${item.name} (\`${item.id}\`)${battle}`);
    }
    lines.push("");
  }
  return lines.join("\n");
}

function writeProceduralPng(file, seed, kind) {
  const data = new Uint8Array(W * H * 4);
  const palette = paletteFor(kind, seed);
  for (let y = 0; y < H; y += 1) {
    const t = y / (H - 1);
    for (let x = 0; x < W; x += 1) {
      const n = noise(seed, x, y);
      const vignette = 1 - 0.32 * Math.hypot((x / W - 0.5) * 1.5, y / H - 0.5);
      const color = mix(palette.top, palette.bottom, t + n * 0.06).map((v) => clampByte(v * vignette));
      const i = (y * W + x) * 4;
      data[i] = color[0];
      data[i + 1] = color[1];
      data[i + 2] = color[2];
      data[i + 3] = 255;
    }
  }
  decorate(data, seed, kind, palette);
  fs.writeFileSync(file, encodePng(W, H, data));
}

function decorate(data, seed, kind, palette) {
  if (kind.includes("forest") || kind.includes("road") || kind.includes("orchard") || kind.includes("wilderness")) {
    for (let i = 0; i < 42; i += 1) {
      const x = hash(`${seed}-tree-x-${i}`) % W;
      const h = 90 + (hash(`${seed}-tree-h-${i}`) % 210);
      const y = H - h + (hash(`${seed}-tree-y-${i}`) % 140);
      rect(data, x, y, 10 + (i % 6), h, shade(palette.accent, -45), 0.86);
      ellipse(data, x + 6, y - 8, 42 + (i % 4) * 10, 30, shade(palette.accent, 20), 0.52);
    }
    if (kind.includes("road")) {
      polygon(data, [[440, H], [840, H], [710, 330], [570, 330]], [102, 91, 66], 0.78);
    }
  }
  if (kind.includes("cave") || kind.includes("mine") || kind.includes("chasm") || kind.includes("forge") || kind.includes("fungi")) {
    for (let i = 0; i < 30; i += 1) {
      const x = hash(`${seed}-rock-x-${i}`) % W;
      const y = 430 + (hash(`${seed}-rock-y-${i}`) % 260);
      ellipse(data, x, y, 70 + (i % 7) * 18, 30 + (i % 5) * 12, shade(palette.accent, -20), 0.48);
    }
    for (let i = 0; i < 18; i += 1) {
      const x = hash(`${seed}-stal-${i}`) % W;
      polygon(data, [[x, 0], [x + 24, 0], [x + 10, 80 + (hash(`${seed}-stal-h-${i}`) % 180)]], shade(palette.accent, -35), 0.58);
    }
    if (kind.includes("water")) rect(data, 0, 470, W, 90, [40, 87, 101], 0.5);
    if (kind.includes("forge")) ellipse(data, 660, 420, 230, 110, [230, 112, 48], 0.38);
    if (kind.includes("fungi")) {
      for (let i = 0; i < 22; i += 1) ellipse(data, hash(`${seed}-fung-x-${i}`) % W, 490 + (hash(`${seed}-fung-y-${i}`) % 190), 18, 42, [149, 117, 183], 0.72);
    }
  }
  if (kind.includes("town") || kind.includes("shop") || kind.includes("inn") || kind.includes("tavern") || kind.includes("farm") || kind.includes("hall") || kind.includes("office")) {
    for (let i = 0; i < 8; i += 1) {
      const x = 80 + i * 150 + (hash(`${seed}-house-${i}`) % 35);
      const y = 360 + (hash(`${seed}-hy-${i}`) % 80);
      rect(data, x, y, 120, 150, shade(palette.accent, -20), 0.72);
      polygon(data, [[x - 10, y], [x + 60, y - 62], [x + 130, y]], shade(palette.accent, -55), 0.85);
      rect(data, x + 45, y + 58, 30, 60, [58, 44, 36], 0.75);
    }
  }
  if (kind.includes("ruin") || kind.includes("castle") || kind.includes("tower") || kind.includes("crypt") || kind.includes("shrine")) {
    for (let i = 0; i < 12; i += 1) {
      const x = 60 + i * 110;
      const y = 280 + (hash(`${seed}-wall-y-${i}`) % 120);
      rect(data, x, y, 82, 230, shade(palette.accent, -28), 0.68);
      rect(data, x + 8, y + 20, 24, 34, shade(palette.accent, -70), 0.5);
    }
    if (kind.includes("tower")) {
      rect(data, 540, 150, 210, 410, shade(palette.accent, -35), 0.74);
      polygon(data, [[520, 150], [645, 70], [770, 150]], shade(palette.accent, -65), 0.78);
    }
    if (kind.includes("shrine")) ellipse(data, 640, 380, 260, 170, shade(palette.top, 45), 0.28);
  }
}

function paletteFor(kind, seed) {
  const palettes = {
    forest: [[62, 87, 70], [24, 38, 34], [89, 116, 73]],
    cave: [[66, 72, 79], [22, 25, 31], [110, 104, 96]],
    town: [[141, 131, 107], [74, 82, 82], [128, 92, 68]],
    ruin: [[105, 121, 105], [50, 61, 59], [128, 132, 118]],
    mine: [[88, 82, 75], [25, 27, 31], [126, 112, 90]],
    shrine: [[94, 91, 119], [37, 39, 58], [157, 145, 112]]
  };
  let key = "forest";
  if (kind.includes("cave") || kind.includes("cellar") || kind.includes("chasm")) key = "cave";
  if (kind.includes("mine") || kind.includes("forge") || kind.includes("fungi")) key = "mine";
  if (kind.includes("town") || kind.includes("shop") || kind.includes("inn") || kind.includes("tavern") || kind.includes("farm") || kind.includes("office") || kind.includes("hall")) key = "town";
  if (kind.includes("ruin") || kind.includes("castle") || kind.includes("tower") || kind.includes("crypt")) key = "ruin";
  if (kind.includes("shrine") || kind.includes("spirit") || kind.includes("wizard")) key = "shrine";
  const [top, bottom, accent] = palettes[key];
  const shift = (hash(`${seed}-palette`) % 18) - 9;
  return { top: shade(top, shift), bottom: shade(bottom, -shift), accent: shade(accent, shift) };
}

function hash(input) {
  let h = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function noise(seed, x, y) {
  return ((hash(`${seed}:${Math.floor(x / 7)}:${Math.floor(y / 7)}`) & 255) / 255) - 0.5;
}

function mix(a, b, t) {
  const c = Math.max(0, Math.min(1, t));
  return a.map((v, i) => v + (b[i] - v) * c);
}

function shade(color, amount) {
  return color.map((value) => clampByte(value + amount));
}

function clampByte(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function rect(data, x, y, w, h, color, alpha = 1) {
  for (let yy = Math.max(0, Math.floor(y)); yy < Math.min(H, Math.ceil(y + h)); yy += 1) {
    for (let xx = Math.max(0, Math.floor(x)); xx < Math.min(W, Math.ceil(x + w)); xx += 1) blend(data, xx, yy, color, alpha);
  }
}

function ellipse(data, cx, cy, rx, ry, color, alpha = 1) {
  const minX = Math.max(0, Math.floor(cx - rx));
  const maxX = Math.min(W, Math.ceil(cx + rx));
  const minY = Math.max(0, Math.floor(cy - ry));
  const maxY = Math.min(H, Math.ceil(cy + ry));
  for (let y = minY; y < maxY; y += 1) {
    for (let x = minX; x < maxX; x += 1) {
      const dx = (x - cx) / rx;
      const dy = (y - cy) / ry;
      if (dx * dx + dy * dy <= 1) blend(data, x, y, color, alpha);
    }
  }
}

function polygon(data, points, color, alpha = 1) {
  const minY = Math.max(0, Math.floor(Math.min(...points.map((p) => p[1]))));
  const maxY = Math.min(H - 1, Math.ceil(Math.max(...points.map((p) => p[1]))));
  for (let y = minY; y <= maxY; y += 1) {
    const nodes = [];
    for (let i = 0, j = points.length - 1; i < points.length; j = i, i += 1) {
      const [xi, yi] = points[i];
      const [xj, yj] = points[j];
      if ((yi < y && yj >= y) || (yj < y && yi >= y)) nodes.push(Math.floor(xi + ((y - yi) / (yj - yi)) * (xj - xi)));
    }
    nodes.sort((a, b) => a - b);
    for (let i = 0; i < nodes.length; i += 2) {
      for (let x = Math.max(0, nodes[i]); x < Math.min(W, nodes[i + 1]); x += 1) blend(data, x, y, color, alpha);
    }
  }
}

function blend(data, x, y, color, alpha) {
  const i = (y * W + x) * 4;
  data[i] = clampByte(data[i] * (1 - alpha) + color[0] * alpha);
  data[i + 1] = clampByte(data[i + 1] * (1 - alpha) + color[1] * alpha);
  data[i + 2] = clampByte(data[i + 2] * (1 - alpha) + color[2] * alpha);
}

function encodePng(width, height, rgba) {
  const stride = width * 4;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y += 1) {
    raw[y * (stride + 1)] = 0;
    Buffer.from(rgba.buffer, y * stride, stride).copy(raw, y * (stride + 1) + 1);
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", Buffer.concat([u32(width), u32(height), Buffer.from([8, 6, 0, 0, 0])])),
    chunk("IDAT", zlib.deflateSync(raw, { level: 6 })),
    chunk("IEND", Buffer.alloc(0))
  ]);
}

function chunk(type, data) {
  const typeBuffer = Buffer.from(type, "ascii");
  return Buffer.concat([u32(data.length), typeBuffer, data, u32(crc32(Buffer.concat([typeBuffer, data])))]);
}

function u32(value) {
  const out = Buffer.alloc(4);
  out.writeUInt32BE(value >>> 0);
  return out;
}

const crcTable = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(buffer) {
  let c = 0xffffffff;
  for (const byte of buffer) c = crcTable[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

buildLibrary();
console.log(`Built ${explorationScenes.length} exploration scenes and ${combatScenes.length} combat scenes.`);
