# 14-taximeter（打车计价）

Taximeter — 起步价 + 里程价 + 低速时长费（夜间加价系数）

## 启动

```bash
docker compose up --build
```

| 入口 | 地址 |
| --- | --- |
| 前端 | http://localhost:4300 |
| API | http://localhost:9300 |

## 主链

录行程里程与低速时长 → 拆解车费 → 行程单

## 打表预览与落表

- `POST /api/fare`：只读试算，不签发令牌、不写记录（行程详情等只读场景）。
- `POST /api/fare/preview`：只读预览，返回时效令牌与到期时刻（默认 60 秒，`PREVIEW_TOKEN_TTL_SECONDS` 可调），不增加记录条数；每次预览签发新令牌，旧令牌立即失效。
- `POST /api/fare/commit`：落表。须携带未过期、未使用、未被取代的令牌，且公里、低速、夜间及起步/里程/低速/应付均与预览一致才写入记录；令牌过期、缺失、已使用或不一致均拒绝且不增记录。每个令牌只能落表一次。

## 技术栈

Python 3.12 + FastAPI + SQLite；Vue 3 + Vite + Nginx。
