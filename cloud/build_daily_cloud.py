# -*- coding: utf-8 -*-
"""
云端版：规则挑选热点 → 生成 daily_hot.json（兼容工作台前端格式）
无 AI 依赖，纯规则 + 模板文案，保证每天稳定产出。
输入：data/platform_hot_raw.json + data/xhs_hot_raw.json
输出：data/daily_hot.json
"""
import json, os, re, datetime, argparse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE), 'data')

def load(name):
    p = os.path.join(DATA_DIR, name)
    if not os.path.exists(p):
        return None
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_wan(s):
    """'1826.7万' / '88.3万' / '312.1万次播放' → 万为单位数值；失败返回 0"""
    if not s:
        return 0
    m = re.search(r'([\d.]+)\s*万', s)
    if m:
        return float(m.group(1))
    m = re.search(r'([\d,]+)', s)
    if m:
        return float(m.group(1).replace(',', '')) / 10000.0
    return 0

def heat_from_wan(wan):
    """万数值 → 0-100 热度"""
    if wan >= 500: return 95
    if wan >= 100: return 88
    if wan >= 50: return 84
    if wan >= 20: return 78
    if wan >= 5: return 72
    if wan >= 1: return 65
    return 60

def fmt_wan(wan):
    if wan >= 10000:
        return f"{wan/10000:.2f}亿"
    if wan >= 100:
        return f"{wan:.0f}万"
    return f"{wan:.1f}万"

def stage_of(heat):
    if heat >= 85: return "上升", "up"
    if heat >= 70: return "成熟", "flat"
    return "上升", "up"

# ---------------- 挑选 ----------------
FOOD_KEYWORDS = ['吃', '美食', '饭', '菜', '面', '汤', '饼', '甜品', '甜点', '奶茶', '咖啡', '蛋糕',
                 '面包', '火锅', '烧烤', '炸', '煎', '煮', '炒', '寿司', '披萨', '汉堡', '冰淇淋',
                 '水果', '零食', '外卖', '探店', '食堂', '早餐', '午餐', '晚餐', '夜宵', '喝', '味',
                 '香', '饿', '饱', '饭张力', '沉浸式', 'ASMR', '吃播', '咀嚼', '解压', '治愈', '甜']

def is_food(title):
    return any(k in title for k in FOOD_KEYWORDS)

def pick_douyin(src):
    """抖音：热点榜 top2（仅保留美食相关）+ 美食榜 top2，按热度文本"""
    picks = []
    for key, tag in [("抖音热点榜", "热点榜"), ("抖音美食榜", "美食榜")]:
        lst = src.get(key) if isinstance(src.get(key), list) else []
        if key == "抖音热点榜":
            lst = [it for it in lst if is_food(it.get('title', ''))]
        ranked = sorted(lst, key=lambda x: parse_wan(x.get('heatText', '')), reverse=True)[:2]
        for i, it in enumerate(ranked):
            wan = parse_wan(it.get('heatText', ''))
            picks.append({
                "raw": it, "platform": "抖音", "sourceKey": key,
                "sourceName": f"抖音·{tag}实时第{i+1}位", "wan": wan,
                "heat": heat_from_wan(wan) + (2 if i == 0 else 0),
            })
    return picks

def pick_bili(src):
    """B站：美食区排行 top2 + 两个搜索词各 top1"""
    picks = []
    rank = src.get("B站美食区排行榜") if isinstance(src.get("B站美食区排行榜"), list) else []
    for i, it in enumerate(sorted(rank, key=lambda x: x.get('play', 0), reverse=True)[:2]):
        wan = it.get('play', 0) / 10000.0
        picks.append({
            "raw": it, "platform": "B站", "sourceKey": "B站美食区排行榜",
            "sourceName": f"B站·美食区排行榜第{i+1}位", "wan": wan,
            "heat": heat_from_wan(wan) + (2 if i == 0 else 0),
        })
    for key, tag in [("B站搜索_ASMR吃播_近30天按播放", "ASMR吃播搜索"), ("B站搜索_沉浸式吃播_近30天按播放", "沉浸式吃播搜索")]:
        lst = src.get(key) if isinstance(src.get(key), list) else []
        if lst:
            it = sorted(lst, key=lambda x: x.get('play', 0), reverse=True)[0]
            wan = it.get('play', 0) / 10000.0
            picks.append({
                "raw": it, "platform": "B站", "sourceKey": key,
                "sourceName": f"B站·{tag}第1名", "wan": wan,
                "heat": heat_from_wan(wan),
            })
    return picks

def pick_xhs(src):
    """小红书：两个关键词最热 top 合并后按点赞取 top3"""
    if not src or src.get('error'):
        return [], src.get('error') if src else '小红书数据缺失'
    merged = []
    for key, lst in (src.get('sources') or {}).items():
        if isinstance(lst, list):
            merged.extend(lst)
    errors = []
    for key, v in (src.get('sources') or {}).items():
        if isinstance(v, dict) and v.get('error'):
            errors.append(v['error'])
    merged.sort(key=lambda x: parse_wan(x.get('likes', '')), reverse=True)
    picks = []
    for i, it in enumerate(merged[:3]):
        wan = parse_wan(it.get('likes', ''))
        picks.append({
            "raw": it, "platform": "小红书", "sourceKey": key,
            "sourceName": f"小红书·搜索最热第{i+1}位", "wan": wan,
            "heat": heat_from_wan(wan) + (2 if i == 0 else 0),
        })
    return picks, ('；'.join(errors) if errors else None)

# ---------------- 文案模板 ----------------
def make_item(p, today):
    raw = p["raw"]; plat = p["platform"]; wan = p["wan"]
    heat, trend = stage_of(p["heat"])
    title = raw.get("title", "").strip('《》"')
    if plat == "抖音":
        note = f"抖音实时榜单抓取（{today}），热度 {fmt_wan(wan)}次播放。高播放说明该标题句式/选题方向正吃流量，情绪化表达是抖音美食区标配。"
        action = "套用同款标题句式与选题方向，内容保持奶油清新风，封面突出食物最诱人瞬间，发布时间选 19:00-22:00 晚高峰。"
    elif plat == "B站":
        author = raw.get("author", "")
        pub = raw.get("pubdate", "")
        note = f"B站官方数据（{author or 'UP主'}，{pub or today} 发布），播放 {fmt_wan(wan)}。该内容在榜单/搜索的头部位置说明选题或系列化打法有效。"
        action = "参考其选题方向，B站吃播吃「系列化+人设」，可用「奶油小厨娘」固定角色做系列化更新，每周固定 3-4 条。"
    else:
        author = raw.get("author", "")
        note = f"小红书搜索最热结果（{author or '作者'}，{today} 抓取），点赞 {fmt_wan(wan)}。小红书吃视觉统一性与情绪价值，颜色系列化/双人沉浸式是顶级流量形态。"
        action = "对标该笔记的视觉方向，做白色系/奶油系沉浸式吃播系列化更新，标题带「沉浸式/治愈系/奶油系」关键词。"
    unit = "播放" if plat != "小红书" else "点赞"
    topic = f"【{plat}真实数据】「{title[:40]}」{fmt_wan(wan)}{unit}：{note.split('。')[0].split('，')[0][:30]}"
    return {
        "topic": topic,
        "heat": min(98, p["heat"]),
        "stage": heat,
        "trend": trend,
        "platform": plat,
        "note": note,
        "action": action,
        "source": raw.get("link", "") or raw.get("source", ""),
        "sourceName": p["sourceName"],
        "date": raw.get("pubdate", "") or today,
    }

def make_insights(picks, today):
    ins = []
    dy = [p for p in picks if p["platform"] == "抖音"]
    bl = [p for p in picks if p["platform"] == "B站"]
    xh = [p for p in picks if p["platform"] == "小红书"]
    if dy:
        top = dy[0]
        ins.append(f"【抖音】今日美食区头部内容「{top['raw'].get('title','')[:24]}」热度 {fmt_wan(top['wan'])}，情绪化标题与互动句式仍是流量密码，可优先拆解标题结构。")
    if bl:
        top = bl[0]
        ins.append(f"【B站】「{top['raw'].get('title','')[:24]}」播放 {fmt_wan(top['wan'])} 居榜首位，系列化+日更仍是 B 站吃播头部打法，建议错位做奶油清新系形成差异化。")
    if xh:
        top = xh[0]
        ins.append(f"【小红书】「{top['raw'].get('title','')[:24]}」点赞 {fmt_wan(top['wan'])} 居搜索最热位，视觉统一性与情绪价值是小红书吃播核心，白色系/奶油系方向已验证有真实流量。")
    ins.append("【视频号】无公开接口未收录，你在微信刷到爆款吃播随手转发或截图给我，我会记录进工作台。")
    return ins

# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(DATA_DIR, 'daily_hot.json'))
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    plat = load('platform_hot_raw.json') or {}
    xhs = load('xhs_hot_raw.json') or {}

    alerts = []
    # 抖音/B站错误检测
    for k, v in (plat.get('sources') or {}).items():
        if isinstance(v, dict) and v.get('error'):
            alerts.append(f"{k} 抓取失败：{v['error']}（今日已跳过该源）")

    picks = []
    picks += pick_douyin(plat.get('sources') or {})
    picks += pick_bili(plat.get('sources') or {})
    xhs_picks, xhs_err = pick_xhs(xhs)
    picks += xhs_picks
    if xhs_err:
        alerts.append(f"小红书数据未更新：{xhs_err}。今日早报仅含抖音+B站数据，可在电脑开机时让 WorkBuddy 重新导出登录态（对 AI 说「小红书重新登录」）。")

    if not picks:
        # 极端情况：全部失败也要生成文件并推送
        alerts.append('今日全部数据源抓取失败，早报无热点内容，请检查云端网络或稍后手动触发。')

    # 按热度排序，控制总量 ≤ 11 条
    picks.sort(key=lambda x: x['heat'], reverse=True)
    picks = picks[:11]
    items = [make_item(p, today) for p in picks]

    daily = {
        "date": today,
        "track": "eatASMR",
        "trackName": "演绎类吃播 ASMR",
        "sources": ["抖音", "B站", "小红书", "视频号"],
        "items": items,
        "insights": make_insights(picks, today),
        "updatedAt": now + "+08:00",
        "searchNote": f"数据来源（{now} 云端自动抓取，100%平台原生真实数据）：①抖音热点榜+美食榜——tophub 聚合站实时榜单，douyin.com 原生视频直链+真实播放量；②B站美食区排行榜+「ASMR吃播」「沉浸式吃播」近30天按播放搜索——B站官方API（wbi签名）；③小红书「ASMR吃播」「沉浸式吃播」搜索最热——登录态 cookies 注入浏览器抓取，xiaohongshu.com 笔记直链+真实点赞数。视频号无公开接口未收录。本文件由 GitHub Actions 云端定时自动生成（规则挑选，非AI解读）。",
        "alerts": alerts,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(daily, f, ensure_ascii=False, indent=2)
    print(f"已生成: {args.out} | {len(items)} 条热点 | alerts: {len(alerts)}")
    for a in alerts:
        print('  [ALERT]', a)

if __name__ == "__main__":
    main()
