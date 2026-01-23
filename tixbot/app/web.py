from __future__ import annotations

from datetime import datetime
from urllib.parse import quote_plus

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, delete

from app.config import load_settings
from app.db import create_engine_and_session, init_db
from app.draw_service import draw_raffle
from app.models import Raffle, RafflePrize, RaffleParticipant
from app.security import verify_admin_link, sign_admin_link
from app.time_utils import now_local, fmt

settings = load_settings()
engine, Session = create_engine_and_session(settings.database_url)

templates = Jinja2Templates(directory="app/templates")

app = FastAPI(title="TixBot Web")


PARTICIPANT_NO_LEN = 8


def _can_manage_raffle(raffle: Raffle, tg_id: int) -> bool:
    """Allow listed admins to manage each other's raffles.

    - Creator can always manage.
    - If ADMIN_IDS is configured, any admin can manage raffles created by another admin.
    """

    if raffle.creator_tg_id == tg_id:
        return True
    if not settings.admin_ids:
        return True
    return (tg_id in settings.admin_ids) and (raffle.creator_tg_id in settings.admin_ids)


def fmt_pn(pn: int | None) -> str | None:
    if pn is None:
        return None
    return f"{int(pn):0{PARTICIPANT_NO_LEN}d}"


def must_token(token: str) -> tuple[str, int]:
    try:
        return verify_admin_link(settings.admin_link_secret, token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


def to_datetime_local_value(dt: datetime | None) -> str:
    """Value for <input type='datetime-local'> (YYYY-MM-DDTHH:MM).

    本项目统一使用【上海时区】的“本地时间”作为逻辑时间（数据库里以 naive datetime 保存）。
    """
    if not dt:
        return ""
    return dt.replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")


def normalize_target_chat_candidates(chat_id: int) -> list[int]:
    """Telegram supergroup ids are often -100xxxxxxxxxx.
    If user provided 2406607330, try both 2406607330 and -1002406607330.
    """
    if chat_id < 0:
        return [chat_id]
    cand = [chat_id]
    try:
        cand.append(int(f"-100{chat_id}"))
    except Exception:
        pass
    out: list[int] = []
    for x in cand:
        if x not in out:
            out.append(x)
    return out


@app.on_event("startup")
async def _startup() -> None:
    await init_db(engine)


@app.get("/health")
async def health():
    return {"ok": True, "tz": settings.tz_name}


@app.get("/admin/raffle/{code}", response_class=HTMLResponse)
async def raffle_edit(code: str, request: Request, token: str, publish_error: str | None = None):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        r = {
            "code": raffle.code,
            "status": raffle.status,
            "target_chat_id": raffle.target_chat_id,
            "title": raffle.title,
            "description": raffle.description,
            "cost_points": raffle.cost_points,
            "draw_mode": raffle.draw_mode,
            "draw_at_local": to_datetime_local_value(raffle.draw_at),
            "min_participants": raffle.min_participants,
            "draw_block_hash": raffle.draw_block_hash,
            "draw_block_height": raffle.draw_block_height,
            "drawn_at": raffle.drawn_at,
        }

    pe = (publish_error or "").strip()
    if not pe and not settings.bot_token:
        pe = "当前未配置 BOT_TOKEN（仅演示后台页面）"

    return templates.TemplateResponse(
        "raffle_edit.html",
        {
            "request": request,
            "title": f"抽奖 {code}",
            "header": "创建/编辑抽奖",
            "subheader": f"时区：{settings.tz_name}（页面选择的时间即上海时间）",
            "r": r,
            "token": token,
            "publish_error": pe,
        },
    )


@app.get("/admin/raffle/{code}/status")
async def raffle_status(code: str, token: str):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        total = await s.scalar(select(func.count()).select_from(RaffleParticipant).where(RaffleParticipant.raffle_id == raffle.id))

    return {
        "code": raffle.code,
        "status": raffle.status,
        "total": int(total or 0),
        "draw_block_hash": raffle.draw_block_hash,
        "draw_block_height": raffle.draw_block_height,
        "drawn_at": fmt(raffle.drawn_at, with_seconds=False),
    }


@app.post("/admin/raffle/{code}")
async def raffle_edit_save(
    code: str,
    token: str,
    title: str = Form(""),
    description: str = Form(""),
    cost_points: int = Form(0),
    draw_mode: str = Form("time"),
    draw_at: str = Form(""),
    min_participants: int = Form(0),
):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    dt = None
    if draw_at.strip():
        try:
            # <input type=datetime-local> gives a naive string; treat as Shanghai local.
            dt = datetime.fromisoformat(draw_at.strip())
        except Exception:
            raise HTTPException(400, "draw_at 格式错误。请使用选择器选择日期与时间")

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        # Once published, the raffle is immutable (and drawn is also immutable).
        if raffle.status != "draft":
            return RedirectResponse(url=f"/admin/raffle/{code}?token={token}", status_code=303)

        raffle.title = title
        raffle.description = description
        raffle.cost_points = int(cost_points or 0)
        raffle.draw_mode = draw_mode
        raffle.draw_at = dt
        raffle.min_participants = int(min_participants or 0)
        raffle.updated_at = now_local()
        await s.commit()

    return RedirectResponse(url=f"/admin/raffle/{code}?token={token}", status_code=303)


@app.post("/admin/raffle/{code}/publish")
async def raffle_publish(code: str, token: str):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    if not settings.bot_token:
        async with Session() as s:
            raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
            if not raffle:
                raise HTTPException(404, "not found")
            if not _can_manage_raffle(raffle, tg_id):
                raise HTTPException(404, "not found")
            if raffle.status != "draft":
                return RedirectResponse(url=f"/admin/raffle/{code}?token={token}", status_code=303)
            raffle.status = "published"
            raffle.updated_at = now_local()
            await s.commit()
        return RedirectResponse(url=f"/admin/raffle/{code}?token={token}", status_code=303)

    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        # Publish is allowed only once.
        if raffle.status != "draft":
            err = quote_plus("该抽奖已发布/结束，无法重复发布或更新置顶消息")
            return RedirectResponse(url=f"/admin/raffle/{code}?token={token}&publish_error={err}", status_code=303)

        bot = Bot(settings.bot_token)
        try:
            raw_target = settings.target_chat_id
            candidates = normalize_target_chat_candidates(raw_target)
            if raffle.target_chat_id and raffle.target_chat_id not in candidates:
                candidates = [raffle.target_chat_id] + candidates

            if raffle.draw_mode == "time" and raffle.draw_at:
                draw_line = f"开奖时间：{raffle.draw_at.strftime('%Y-%m-%d %H:%M')}（上海时间）"
            elif raffle.draw_mode == "threshold" and (raffle.min_participants or 0) > 0:
                draw_line = f"开奖方式：参与人数达到 {raffle.min_participants} 后开奖"
            else:
                draw_line = f"开奖方式：{raffle.draw_mode}"

            # Prize quantity affects winning threshold Y
            rule_tpl = (
                "\n\n中奖规则（透明可验证）\n"
                "1) 取开奖时刻的随机种子：优先使用 drand 公共随机信标（更快更新），失败时回退到比特币最新区块\n"
                "2) 取该随机种子的值（drand randomness 或 BTC 区块哈希）\n"
                "3) 计算 SHA256(种子值 + 抽奖编号 + 你的参与编号)\n"
                "4) 取哈希前16位转十进制作为分数，分数从小到大排序\n"
                "5) 若你排在前 Y（Y=奖品数量总和{y_hint}）即中奖"
            )

            prizes = (
                await s.scalars(
                    select(RafflePrize)
                    .where(RafflePrize.raffle_id == raffle.id)
                    .order_by(RafflePrize.id.asc())
                )
            ).all()
            total_prize_qty = sum(int(p.quantity or 0) for p in prizes)

            y_hint = f"（Y={total_prize_qty}）" if total_prize_qty > 0 else ""
            rule = rule_tpl.format(y_hint=y_hint)
            if prizes:
                prize_lines = ["\n\n🎁奖品信息"]
                for p in prizes:
                    
                    label = None
                    if getattr(p, 'prize_type', None) == 'points':
                        try:
                            label = f"{int(p.points_amount or 0)} 积分"
                        except Exception:
                            label = '积分'
                    elif getattr(p, 'prize_type', None) == 'custom':
                        label = (getattr(p, 'custom_label', None) or p.prize_name)
                    else:
                        label = p.prize_name
                    prize_lines.append(f"- {label} × {int(p.quantity)}")
                prize_lines.append(f"合计：{total_prize_qty} 份")
                prize_block = "\n".join(prize_lines)
            else:
                prize_block = "\n\n🎁奖品信息\n- （未配置）"

            text = (
                f"🎉抽奖开始！\n"
                f"编号：{raffle.code}\n"
                f"标题：{raffle.title or raffle.code}\n"
                f"参与消耗：{raffle.cost_points} 积分\n"
                f"{draw_line}\n\n"
                f"{raffle.description or ''}"
                f"{prize_block}"
                f"{rule}"
            ).strip()

            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="参与抽奖", callback_data=f"join:{raffle.code}")]]
            )

            last_err = ""
            used_chat_id: int | None = None
            msg_id: int | None = None

            # Only publish once: always send a new message (no edits/updates).
            for cid in candidates:
                try:
                    sent = await bot.send_message(chat_id=cid, text=text, reply_markup=kb)
                    used_chat_id = cid
                    msg_id = sent.message_id
                    break
                except Exception as e:
                    last_err = str(e)
                    continue

            if not msg_id or used_chat_id is None:
                err = quote_plus((last_err or "publish failed")[:300])
                return RedirectResponse(
                    url=f"/admin/raffle/{code}?token={token}&publish_error={err}",
                    status_code=303,
                )

            try:
                await bot.pin_chat_message(chat_id=used_chat_id, message_id=msg_id, disable_notification=True)
                raffle.pinned_message_id = msg_id
            except Exception:
                # Pin may fail if the bot has no permission; the raffle can still be published.
                pass

            raffle.status = "published"
            raffle.target_chat_id = used_chat_id
            raffle.published_message_id = msg_id
            if raffle.pinned_message_id is None:
                # Best-effort: if we didn't pin successfully, keep pinned_message_id empty.
                pass
            raffle.updated_at = now_local()
            await s.commit()
        finally:
            # Avoid aiohttp "Unclosed client session" warnings.
            try:
                await bot.session.close()
            except Exception:
                pass

    return RedirectResponse(url=f"/admin/raffle/{code}?token={token}", status_code=303)


@app.get("/admin/raffle/{code}/prizes", response_class=HTMLResponse)
async def raffle_prizes(code: str, request: Request, token: str):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        prizes = (
            await s.scalars(select(RafflePrize).where(RafflePrize.raffle_id == raffle.id).order_by(RafflePrize.id.desc()))
        ).all()

    return templates.TemplateResponse(
        "raffle_prizes.html",
        {
            "request": request,
            "title": f"奖品 {code}",
            "header": "配置奖品",
            "subheader": "数量合计 = 中奖人数 Y",
            "code": code,
            "token": token,
            "prizes": prizes,
            "raffle_status": raffle.status,
        },
    )


@app.post("/admin/raffle/{code}/prizes/add")
async def prizes_add(
    code: str,
    token: str,
    prize_type: str = Form("custom"),
    prize_name: str = Form(""),
    custom_label: str = Form(""),
    points_amount: int | None = Form(None),
    quantity: int = Form(1),
):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    prize_type = (prize_type or "custom").strip()
    allowed = {"points", "vps", "nat", "discount_code", "custom"}
    if prize_type not in allowed:
        raise HTTPException(400, "bad prize_type")

    qty = max(1, int(quantity or 1))

    # Normalize fields by type
    name = (prize_name or "").strip()
    cust = (custom_label or "").strip()

    if prize_type == "points":
        if points_amount is None:
            raise HTTPException(400, "points_amount required")
        pa = int(points_amount)
        if pa <= 0:
            raise HTTPException(400, "points_amount must be > 0")
        name = "积分"
        cust = None
    elif prize_type == "custom":
        if not cust:
            raise HTTPException(400, "custom_label required")
        name = cust
        pa = None
    else:
        if not name:
            raise HTTPException(400, "prize_name required")
        pa = None
        cust = None

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        # Once published, the raffle is immutable.
        if raffle.status != "draft":
            return RedirectResponse(url=f"/admin/raffle/{code}/prizes?token={token}", status_code=303)

        p = RafflePrize(
            raffle_id=raffle.id,
            prize_type=prize_type,
            prize_name=name,
            quantity=qty,
            points_amount=pa,
            custom_label=cust,
        )
        s.add(p)
        await s.commit()

    return RedirectResponse(url=f"/admin/raffle/{code}/prizes?token={token}", status_code=303)



@app.post("/admin/raffle/{code}/prizes/delete")
async def prizes_delete(code: str, token: str, prize_id: int = Form(...)):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        # Once published, the raffle is immutable.
        if raffle.status != "draft":
            return RedirectResponse(url=f"/admin/raffle/{code}/prizes?token={token}", status_code=303)

        await s.execute(delete(RafflePrize).where(RafflePrize.id == prize_id, RafflePrize.raffle_id == raffle.id))
        await s.commit()

    return RedirectResponse(url=f"/admin/raffle/{code}/prizes?token={token}", status_code=303)


@app.get("/admin/raffle/{code}/participants", response_class=HTMLResponse)
async def raffle_participants(code: str, request: Request, token: str):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        total = await s.scalar(select(func.count()).select_from(RaffleParticipant).where(RaffleParticipant.raffle_id == raffle.id))
        users = (
            await s.scalars(
                select(RaffleParticipant)
                .where(RaffleParticipant.raffle_id == raffle.id)
                .order_by(RaffleParticipant.id.desc())
                .limit(200)
            )
        ).all()

    return templates.TemplateResponse(
        "raffle_participants.html",
        {
            "request": request,
            "title": f"参与者 {code}",
            "header": "参与者",
            "subheader": "页面会自动刷新显示最新状态（中奖/未中）",
            "code": code,
            "token": token,
            "total": int(total or 0),
            "users": users,
        },
    )


@app.get("/admin/raffle/{code}/participants/data")
async def raffle_participants_data(code: str, token: str):
    raffle_code, tg_id = must_token(token)
    if raffle_code != code:
        raise HTTPException(401, "bad token")

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            raise HTTPException(404, "not found")
        if not _can_manage_raffle(raffle, tg_id):
            raise HTTPException(404, "not found")

        total = await s.scalar(select(func.count()).select_from(RaffleParticipant).where(RaffleParticipant.raffle_id == raffle.id))
        users = (
            await s.scalars(
                select(RaffleParticipant)
                .where(RaffleParticipant.raffle_id == raffle.id)
                .order_by(RaffleParticipant.id.desc())
                .limit(200)
            )
        ).all()

    return JSONResponse(
        {
            "total": int(total or 0),
            "users": [
                {
                    "tg_id": int(u.tg_id),
                    "username": u.username,
                    "status": u.status,
                    "participant_no": fmt_pn(int(u.participant_no)) if u.participant_no is not None else None,
                    "joined_at": fmt(u.joined_at, with_seconds=True),
                    "score": int(u.score) if u.score is not None else None,
                    "win_prize": u.win_prize,
                    "win_rank": u.win_rank,
                }
                for u in users
            ],
        }
    )


# ============ DEV-only helper: seed a raffle so you can see pages running without Telegram ============
@app.get("/dev/seed")
async def dev_seed():
    async with Session() as s:
        code = f"L{int(datetime.utcnow().timestamp()*1000)}"
        r = Raffle(
            code=code,
            creator_tg_id=123456789,
            target_chat_id=-1001234567890,
            title="演示抽奖",
            description="这是一个用于验证后台页面是否能正常打开的演示抽奖。",
            required_chats=[],
        )
        s.add(r)
        await s.commit()

    token = sign_admin_link(settings.admin_link_secret, code, 123456789, ttl_seconds=24 * 3600)
    return {
        "raffle_code": code,
        "admin_url": f"{settings.base_url}/admin/raffle/{code}?token={token}",
        "prizes_url": f"{settings.base_url}/admin/raffle/{code}/prizes?token={token}",
        "participants_url": f"{settings.base_url}/admin/raffle/{code}/participants?token={token}",
    }
