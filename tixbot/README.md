# TixBot (Telegram 抽奖机器人) - Skeleton

这是一个能跑起来的最小可用版本：
- Bot：aiogram v3（长轮询）
- 后台：FastAPI + Jinja2
- DB：MySQL（生产）/ SQLite（本地演示）

## 1) 安装依赖

```bash
cd tixbot
pip install -r requirements.txt
```

## 2) 配置环境变量

```bash
cp .env.example .env
```

- 生产 MySQL：
  - 把 `.env` 里的 `DATABASE_URL` 改为：
    `mysql+asyncmy://user:pass@127.0.0.1:3306/tixbot?charset=utf8mb4`
  - 配置积分数据库（读取/扣减积分的主库）：
    `TGBOT_DATABASE_URL=mysql+asyncmy://user:pass@127.0.0.1:3306/tgbot?charset=utf8mb4`
    （兼容旧环境变量：`TG_DATABASE_URL`）
  - 固定发布群：
    `TARGET_CHAT_ID=2406607330`（也可以直接填 -100...）
  - 先执行 `sql/mysql_schema.sql` 建表

### 数据库升级（如果你是从旧版本更新）

v11 起，为了实现“开奖后 1 天再删除参与成功消息 / 开奖后 3 天自动取消置顶”，
需要在 `raffle_participants` 增加 3 个字段：

```sql
USE tixbot;
ALTER TABLE raffle_participants
  ADD COLUMN receipt_chat_id BIGINT NULL AFTER joined_at,
  ADD COLUMN receipt_message_id BIGINT NULL AFTER receipt_chat_id,
  ADD COLUMN receipt_deleted_at DATETIME(3) NULL AFTER receipt_message_id;
```
- 本地演示：默认用 SQLite（不需要额外服务）

## 3) 启动后台页面

```bash
uvicorn app.web:app --host 0.0.0.0 --port 8000
```

打开：
- 健康检查：`/health`
- 演示数据：`/dev/seed`（会返回 admin_url）

## 4) 启动 Bot（需要 Telegram Bot Token）

```bash
python -m app.bot
```

流程（简化版，仅两个指令）：
  - 私聊 `/tixnew`：创建抽奖（草稿），机器人返回后台管理链接
  - 私聊 `/tixedit`：管理你创建的抽奖（查看状态/打开后台/删除）
  - 在后台点击「发布到群并置顶」后才会发到固定群
  - 后台里可更新置顶消息、配置奖品、查看参与者，并可「立即开奖」
  - 若抽奖设置了“定时开奖 / 人数达标开奖”，只要 bot 进程在运行，会自动触发开奖并在群里发送中奖通知

