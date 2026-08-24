# 创作情报中枢 · 自媒体工作台（云端自动更新版）

每天北京时间 07:55 自动抓取抖音 / B站 / 小红书真实热榜数据，生成早报推送到微信，并自动更新线上工作台（GitHub Pages）。

## 数据流

```
GitHub Actions（云端定时 07:55）
  ├─ ① cloud/fetch_platform_hot.py  → 抖音热点榜 + 美食榜 + B站美食区排行 + 2 个搜索词（官方API/wbi签名）
  ├─ ② cloud/xhs_fetch_cloud.js     → 小红书「ASMR吃播」「沉浸式吃播」搜索最热（登录态 cookies 注入）
  ├─ ③ cloud/build_daily_cloud.py   → 规则挑选生成 data/daily_hot.json（失败自动写入 alerts）
  ├─ ④ cloud/push_plus_cloud.py     → 推送早报到微信（任何失败也推送失败提醒，铁律）
  └─ ⑤ git commit + push            → main 分支 = GitHub Pages 线上，push 即自动更新
```

## 目录结构

- `index.html` — 单文件工作台（前端运行时自动 fetch `data/daily_hot.json`）
- `data/` — 每日热点数据（workflow 自动更新提交）
- `cloud/` — 云端脚本（抓取/生成/推送）
- `.github/workflows/daily.yml` — 定时任务定义

## 需要的 Secrets

- `PUSH_PLUS_TOKEN` — pushplus 微信推送 token
- `XHS_COOKIES` — 小红书登录态 cookies JSON（失效时需重新导出）

## 手动触发

GitHub 仓库 → Actions → Daily Hot Update → Run workflow

线上地址：`https://070827.github.io/workbench-daily/`
