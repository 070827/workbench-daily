# -*- coding: utf-8 -*-
"""
云端版：微信推送（GitHub Actions）
TOKEN 从环境变量 PUSH_PLUS_TOKEN 读取（存入 GitHub Secret，绝不写入仓库）
morning：基于 data/daily_hot.json 渲染早报（含 alerts 红色警示块）
alert：异常单独推送
"""
import json, sys, urllib.request, datetime, os

PUSH_URL = 'https://www.pushplus.plus/send'

def get_token():
    tok = os.environ.get('PUSH_PLUS_TOKEN', '')
    if not tok:
        print('[ERROR] PUSH_PLUS_TOKEN 环境变量未设置')
        sys.exit(1)
    return tok

def load_daily_hot():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'daily_hot.json')
    if not os.path.exists(p):
        return None
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

def fmt_date(d):
    return '{}月{}日'.format(int(d[5:7]), int(d[8:10]))

def morning_html():
    today_obj = datetime.date.today()
    title = '创作情报中枢 · 早报（{}月{}日）'.format(today_obj.month, today_obj.day)
    daily = load_daily_hot()
    if daily and daily.get('items'):
        hot = sorted(daily['items'], key=lambda x: x.get('heat', 0), reverse=True)[:5]
        track_name = daily.get('trackName', '已选赛道')
        source_tip = '数据来源：云端自动抓取 ' + '、'.join(daily.get('sources', ['抖音', 'B站', '小红书'])) + ' 热点'
    else:
        hot = []
        track_name = '当前赛道'
        source_tip = '数据来源：云端自动抓取（今日无热点数据）'

    content = '<h3>早安，文利</h3>'
    content += '<p>已选定【{}】赛道 · 运营期。今日建议：刷 10 分钟热点 + 存 2-3 条灵感 + 推进 1 个选题。</p>'.format(track_name)
    if daily and daily.get('alerts'):
        content += '<h4 style="color:#D93025">⚠️ 今日数据情况（请留意）</h4><ul>'
        for a in daily['alerts']:
            content += '<li style="color:#D93025">{}</li>'.format(a)
        content += '</ul>'
    if hot:
        content += '<h4>今日热点方向 TOP{}</h4><ol>'.format(len(hot))
        for h in hot:
            content += '<li><b>{}</b>（热度 {}° · {} · {}）<br>{}<br><span style="color:#4A90D9;font-size:12px">💡 可拍：{}</span></li>'.format(
                h['topic'], h.get('heat', '-'), h.get('stage', ''), h.get('platform', ''), h.get('note', ''), h.get('action', ''))
        content += '</ol>'
    else:
        content += '<p style="color:#D93025">今日无热点数据（全部数据源抓取失败），请查看云端运行日志。</p>'
    if daily and daily.get('insights'):
        content += '<h4>趋势洞察</h4><ul>'
        for ins in daily['insights'][:3]:
            content += '<li>{}</li>'.format(ins)
        content += '</ul>'
    content += '<p style="color:#888;font-size:12px">{}。线上工作台已同步更新。</p>'.format(source_tip)
    return title, content

def send(token, title, content):
    payload = {'token': token, 'title': title, 'content': content, 'template': 'html'}
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        PUSH_URL, data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode('utf-8')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'morning'
    token = get_token()
    if mode == 'alert':
        if len(sys.argv) < 4:
            print('Usage: push_plus_cloud.py alert "标题" "内容"')
            sys.exit(1)
        print(send(token, sys.argv[2], sys.argv[3]))
    elif mode == 'morning':
        title, content = morning_html()
        print(send(token, title, content))
    else:
        print('Usage: push_plus_cloud.py <morning|alert "标题" "内容">')
        sys.exit(1)
