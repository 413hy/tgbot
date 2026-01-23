from __future__ import annotations

import asyncio
import time
import secrets
from datetime import datetime, timedelta
from html import escape

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import delete, select, text, func
from sqlalchemy.exc import IntegrityError

from app.config import load_settings
from app.db import create_engine_and_session, init_db
from app.draw_service import draw_raffle, mention_html
from app.models import PointsLedger, Raffle, RaffleParticipant, TgUser
from app.security import sign_admin_link
from app.time_utils import now_local


settings = load_settings()
engine, Session = create_engine_and_session(settings.database_url)
tgbot_engine, TGBotSession = create_engine_and_session(settings.tgbot_database_url)

router = Router()


# 固定长度的随机参与编号（建议 8 位，冲突概率更低）
PARTICIPANT_NO_LEN = 8


def _format_participant_no(pn: int) -> str:
    return f"{int(pn):0{PARTICIPANT_NO_LEN}d}"


def _gen_participant_no() -> int:
    """Generate a fixed-length random integer.

    We keep it numeric for hashing, but always display with zero padding.
    """
    if PARTICIPANT_NO_LEN <= 1:
        return secrets.randbelow(10)
    base = 10 ** (PARTICIPANT_NO_LEN - 1)
    return secrets.randbelow(9 * base) + base


async def _auto_draw_loop(bot: Bot) -> None:
    """Auto-draw worker.

    - 定时开奖：当 draw_at <= 当前上海时间时自动开奖
    - 人数达标开奖：当 joined 人数 >= min_participants 时自动开奖

    说明：这是一个轻量级轮询（默认 5 秒），适合单群单机部署。
    """
    last_err_at: dict[str, int] = {}
    while True:
        try:
            now = now_local()
            due_codes: list[str] = []

            async with Session() as s:
                # time-based
                due_time = (
                    await s.scalars(
                        select(Raffle.code)
                        .where(
                            Raffle.status == "published",
                            Raffle.draw_mode == "time",
                            Raffle.draw_at.is_not(None),
                            Raffle.draw_at <= now,
                        )
                        .limit(20)
                    )
                ).all()
                due_codes.extend([str(x) for x in due_time])

                # threshold-based
                thresh = (
                    await s.scalars(
                        select(Raffle)
                        .where(
                            Raffle.status == "published",
                            Raffle.draw_mode == "threshold",
                            Raffle.min_participants.is_not(None),
                            Raffle.min_participants > 0,
                        )
                        .limit(20)
                    )
                ).all()

                for r in thresh:
                    joined = await s.scalar(
                        select(func.count())
                        .select_from(RaffleParticipant)
                        .where(RaffleParticipant.raffle_id == r.id, RaffleParticipant.status == "joined")
                    )
                    if int(joined or 0) >= int(r.min_participants or 0):
                        due_codes.append(str(r.code))

            # de-dup while keeping order
            seen = set()
            ordered: list[str] = []
            for c in due_codes:
                if c and c not in seen:
                    seen.add(c)
                    ordered.append(c)

            for code in ordered[:20]:
                try:
                    ok, msg = await draw_raffle(Session, settings.tz_name, code, bot=bot, TGBotSession=TGBotSession)
                    if not ok:
                        # Only log occasionally to avoid spam.
                        now_ts = int(time.time())
                        if now_ts - int(last_err_at.get(code, 0)) >= 60:
                            last_err_at[code] = now_ts
                            print(f"[tixbot][auto_draw] skip {code}: {msg}")
                except Exception as e:
                    now_ts = int(time.time())
                    if now_ts - int(last_err_at.get(code, 0)) >= 60:
                        last_err_at[code] = now_ts
                        print(f"[tixbot][auto_draw] error {code}: {e}")

        except Exception as e:
            # avoid crashing the loop
            print(f"[tixbot][auto_draw] loop error: {e}")

        await asyncio.sleep(5)


async def _delete_cmd_message(msg: Message, bot: Bot) -> None:
    """Best-effort delete to 'hide' admin commands in groups."""
    try:
        await bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
    except Exception:
        pass


def _admin_kb(admin_url: str, prizes_url: str, parts_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="打开管理后台", url=admin_url)],
            [
                InlineKeyboardButton(text="配置奖品", url=prizes_url),
                InlineKeyboardButton(text="参与者", url=parts_url),
            ],
        ]
    )


def _is_creator(user_id: int) -> bool:
    # Only the specified tg_id(s) can use commands.
    return (not settings.admin_ids) or (user_id in settings.admin_ids)


def _can_manage_raffle(raffle: Raffle, tg_id: int) -> bool:
    """Allow listed admins to manage each other's raffles."""
    if raffle.creator_tg_id == tg_id:
        return True
    if not settings.admin_ids:
        return True
    return (tg_id in settings.admin_ids) and (raffle.creator_tg_id in settings.admin_ids)


def _target_chat_candidates(raw_chat_id: int) -> list[int]:
    # Many people store supergroup ids without the -100 prefix (e.g. 2406607330).
    # We'll try both.
    if raw_chat_id < 0:
        return [raw_chat_id]
    try:
        return [raw_chat_id, int(f"-100{raw_chat_id}")]
    except Exception:
        return [raw_chat_id]


def _raffle_keyboard(code: str) -> InlineKeyboardMarkup:
    """Keyboard for the published raffle message in the group.

    We keep it simple: a single "参与抽奖" button.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="参与抽奖", callback_data=f"join:{code}")]]
    )


def _join_confirm_kb(code: str, owner_tg_id: int, cost: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅确认参加（扣{cost}积分）", callback_data=f"jconfirm:{code}:{owner_tg_id}")],
            [InlineKeyboardButton(text="❌取消", callback_data=f"jcancel:{code}:{owner_tg_id}")],
        ]
    )


def _raffle_text(r: Raffle) -> str:
    draw_line = ""
    if r.draw_mode == "time" and r.draw_at:
        # 本项目数据库中时间均视为【上海本地时间】
        draw_line = f"开奖时间：{r.draw_at.strftime('%Y-%m-%d %H:%M')}（上海时间）"
    elif r.draw_mode == "threshold" and (r.min_participants or 0) > 0:
        draw_line = f"开奖方式：参与人数达到 {r.min_participants} 后开奖"
    else:
        draw_line = f"开奖方式：{r.draw_mode}"

    rule = (
        "\n\n中奖规则（透明可验证）\n"
        "1) 取开奖时刻的随机种子：优先使用 drand 公共随机信标（更快更新），失败时回退到比特币最新区块\n"
        "2) 取该随机种子的值（drand randomness 或 BTC 区块哈希）\n"
        "3) 计算 SHA256(种子值 + 抽奖编号 + 你的参与编号)\n"
        "4) 取哈希前16位转十进制作为分数，分数从小到大排序\n"
        "5) 若你排在前 Y（Y=奖品数量总和）即中奖"
    )

    base = (
        f"🎉抽奖开始！\n"
        f"编号：{r.code}\n"
        f"标题：{r.title or r.code}\n"
        f"参与消耗：{r.cost_points} 积分\n"
        f"{draw_line}\n\n"
        f"{r.description or ''}"
    ).strip()

    return f"{base}{rule}".strip()


async def _tgbot_get_user(tg_id: int) -> dict | None:
    if not settings.tgbot_database_url:
        return None
    async with TGBotSession() as s:
        # Some deployments have an internal numeric primary key (id). We'll try to read it,
        # but gracefully fall back if the column doesn't exist.
        try:
            q = "SELECT id, tg_id, points, email, whmcs_client_id FROM `users` WHERE tg_id=:tg_id"
            row = (await s.execute(text(q), {"tg_id": tg_id})).mappings().first()
        except Exception:
            q = "SELECT tg_id, points, email, whmcs_client_id FROM `users` WHERE tg_id=:tg_id"
            row = (await s.execute(text(q), {"tg_id": tg_id})).mappings().first()
        return dict(row) if row else None


async def _tgbot_deduct_points(tg_id: int, cost: int) -> dict | None:
    """Atomically deduct points in tg DB. Returns updated user dict on success, None on insufficient/not found."""
    if cost <= 0:
        return await _tgbot_get_user(tg_id)

    async with TGBotSession() as s:
        # Atomic conditional update
        res = await s.execute(
            text(
                "UPDATE `users` SET points = points - :cost "
                "WHERE tg_id=:tg_id AND points >= :cost"
            ),
            {"tg_id": tg_id, "cost": cost},
        )
        if res.rowcount == 0:
            await s.rollback()
            return None
        # Read updated row
        try:
            q = "SELECT id, tg_id, points, email, whmcs_client_id FROM `users` WHERE tg_id=:tg_id"
            row = (await s.execute(text(q), {"tg_id": tg_id})).mappings().first()
        except Exception:
            q = "SELECT tg_id, points, email, whmcs_client_id FROM `users` WHERE tg_id=:tg_id"
            row = (await s.execute(text(q), {"tg_id": tg_id})).mappings().first()
        await s.commit()
        return dict(row) if row else None


async def _sync_local_user(
    tg_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    ext: dict | None,
) -> None:
    async with Session() as s:
        u = await s.scalar(select(TgUser).where(TgUser.tg_id == tg_id))
        if not u:
            u = TgUser(tg_id=tg_id)
            s.add(u)
        u.username = username
        u.first_name = first_name
        u.last_name = last_name
        if ext:
            if ext.get("points") is not None:
                u.points = int(ext["points"])
            u.email = ext.get("email")
            u.whmcs_client_id = ext.get("whmcs_client_id")
        u.updated_at = now_local()
        await s.commit()


def _format_pn(pn: int | None) -> str:
    if pn is None:
        return "-"
    # Always display as fixed-length number to match the generation rule.
    return f"{int(pn):0{PARTICIPANT_NO_LEN}d}"


async def _post_draw_cleanup_loop(bot: Bot) -> None:
    """After-draw housekeeping.

    - Delete per-user "参与成功" receipts **1 day after** the raffle is drawn
    - Unpin the raffle message **3 days after** the raffle is drawn

    NOTE: We store receipt message ids in DB so this survives restarts.
    """
    while True:
        try:
            now = now_local()
            delete_before = now - timedelta(days=1)
            unpin_before = now - timedelta(days=3)

            # 1) Delete receipts (batch)
            async with Session() as s:
                # Join with raffle to ensure it's drawn
                rows = (
                    await s.execute(
                        select(RaffleParticipant, Raffle)
                        .join(Raffle, RaffleParticipant.raffle_id == Raffle.id)
                        .where(
                            Raffle.status == "drawn",
                            Raffle.drawn_at.is_not(None),
                            Raffle.drawn_at <= delete_before,
                            RaffleParticipant.receipt_message_id.is_not(None),
                            RaffleParticipant.receipt_chat_id.is_not(None),
                            RaffleParticipant.receipt_deleted_at.is_(None),
                        )
                        .limit(50)
                    )
                ).all()

                for part, raffle in rows:
                    chat_id = int(part.receipt_chat_id or 0)
                    mid = int(part.receipt_message_id or 0)
                    if chat_id and mid:
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=mid)
                        except Exception:
                            # Message may already be gone; still mark as deleted.
                            pass
                    part.receipt_deleted_at = now
                if rows:
                    await s.commit()

            # 2) Unpin old raffle messages
            async with Session() as s:
                raffles = (
                    await s.scalars(
                        select(Raffle)
                        .where(
                            Raffle.status == "drawn",
                            Raffle.drawn_at.is_not(None),
                            Raffle.drawn_at <= unpin_before,
                            Raffle.pinned_message_id.is_not(None),
                            Raffle.target_chat_id.is_not(None),
                        )
                        .limit(20)
                    )
                ).all()
                for r in raffles:
                    cid = int(r.target_chat_id)
                    mid = int(r.pinned_message_id or 0)
                    try:
                        # Try unpin specific message first
                        try:
                            await bot.unpin_chat_message(chat_id=cid, message_id=mid)
                        except Exception:
                            await bot.unpin_chat_message(chat_id=cid)
                    except Exception:
                        pass
                    r.pinned_message_id = None
                if raffles:
                    await s.commit()

        except Exception as e:
            print(f"[tixbot][cleanup] loop error: {e}")

        await asyncio.sleep(30)


@router.message(Command("start"))
async def start(msg: Message):
    if msg.chat.type != "private":
        return
    # 普通用户不需要私聊机器人；仅允许指定管理员在私聊使用管理指令。
    if not _is_creator(msg.from_user.id):
        return
    await msg.reply("已启动。创建抽奖用 /tixnew ，管理抽奖用 /tixedit。")


@router.message(Command("tixnew"))
async def tixnew(msg: Message, bot: Bot):
    # Hide /tixnew in groups: delete silently.
    if msg.chat.type != "private":
        await _delete_cmd_message(msg, bot)
        return

    tg_id = msg.from_user.id
    if not _is_creator(tg_id):
        return await msg.reply("❌你不是允许创建抽奖的指定用户。")

    code = f"L{int(time.time() * 1000)}"
    # Default values (can be edited in web)
    title = f"抽奖 {code}"
    description = "请点击按钮参与抽奖。"

    # Create raffle in DB (draft). Publishing is ONLY done from the web "发布" button.
    async with Session() as s:
        r = Raffle(
            code=code,
            creator_tg_id=tg_id,
            target_chat_id=settings.target_chat_id,
            title=title,
            description=description,
            required_chats=[],
            status="draft",
        )
        s.add(r)
        await s.commit()

    token = sign_admin_link(settings.admin_link_secret, code, tg_id)
    admin_url = f"{settings.base_url}/admin/raffle/{code}?token={token}"
    prizes_url = f"{settings.base_url}/admin/raffle/{code}/prizes?token={token}"
    parts_url = f"{settings.base_url}/admin/raffle/{code}/participants?token={token}"

    await msg.reply(
        f"✅创建成功，编号：{code}\n\n请在后台完善内容与奖品，然后点击『发布到群并置顶』。",
        reply_markup=_admin_kb(admin_url, prizes_url, parts_url),
    )


@router.message(Command("tixedit"))
async def tixedit(msg: Message):
    if msg.chat.type != "private":
        # Hide /tixedit in groups: delete silently.
        # (Bot needs delete permission; if not available, it will just do nothing.)
        await _delete_cmd_message(msg, msg.bot)
        return

    tg_id = msg.from_user.id
    if not _is_creator(tg_id):
        return await msg.reply("❌无权限。")

    async with Session() as s:
        q = select(Raffle).order_by(Raffle.id.desc()).limit(30)
        # Admins can view/manage each other's raffles.
        if settings.admin_ids:
            q = q.where(Raffle.creator_tg_id.in_(list(settings.admin_ids)))
        else:
            q = q.where(Raffle.creator_tg_id == tg_id)
        rows = (await s.scalars(q)).all()

    if not rows:
        return await msg.reply("暂无可管理的抽奖。")

    kb = []
    for r in rows:
        title = r.title or r.code
        creator_tip = f"{r.creator_tg_id}" if (settings.admin_ids and r.creator_tg_id != tg_id) else ""
        suffix = f" ({r.status})" + (f" · {creator_tip}" if creator_tip else "")
        kb.append([InlineKeyboardButton(text=f"{title}{suffix}", callback_data=f"tixedit:{r.code}")])

    await msg.reply("选择要管理的抽奖：", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.message(Command("tixclean"))
async def tixclean(msg: Message, bot: Bot):
    """清理历史抽奖记录（仅管理员私聊）。

    用法：
      - /tixclean        -> 删除你创建的所有已开奖(drawn)抽奖及其参与/奖品记录
      - /tixclean all    -> 删除你创建的全部抽奖（包括草稿/已发布/已开奖）

    说明：
    - 仅影响 tixbot 本库数据，不会删除 tgbot.users 积分账户。
    - points_ledger 中关联该抽奖(ref_type='raffle')的扣分流水也会一并清理。
    """

    # Hide in groups
    if msg.chat.type != "private":
        await _delete_cmd_message(msg, bot)
        return

    tg_id = msg.from_user.id
    if not _is_creator(tg_id):
        return await msg.reply("❌无权限。")

    arg = (msg.text or "").split(maxsplit=1)
    mode = arg[1].strip().lower() if len(arg) > 1 else ""
    wipe_all = mode in {"all", "--all"}

    async with Session() as s:
        q = select(Raffle.id, Raffle.code).where(Raffle.creator_tg_id == tg_id)
        if not wipe_all:
            q = q.where(Raffle.status == "drawn")
        rows = (await s.execute(q)).all()
        if not rows:
            return await msg.reply("没有可清理的抽奖记录。" if not wipe_all else "你还没有创建任何抽奖。")

        ids = [int(r[0]) for r in rows]
        codes = [str(r[1]) for r in rows]

        # Clean ledger first
        await s.execute(
            delete(PointsLedger).where(
                PointsLedger.ref_type == "raffle",
                PointsLedger.ref_code.in_(codes),
            )
        )

        # Clean raffles (CASCADE will remove prizes/participants)
        await s.execute(delete(Raffle).where(Raffle.id.in_(ids)))
        await s.commit()

    tip = "（包含草稿/已发布/已开奖）" if wipe_all else "（仅已开奖）"
    await msg.reply(f"✅已清理 {len(ids)} 个抽奖记录 {tip}。")


@router.callback_query(F.data.startswith("tixedit:"))
async def tixedit_item(cb: CallbackQuery):
    code = cb.data.split(":", 1)[1]
    tg_id = cb.from_user.id
    if not _is_creator(tg_id):
        return await cb.answer("无权限", show_alert=True)

    async with Session() as s:
        r = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not r or not _can_manage_raffle(r, tg_id):
            return await cb.answer("找不到该抽奖或无权限", show_alert=True)
        total = await s.scalar(
            select(func.count()).select_from(RaffleParticipant).where(RaffleParticipant.raffle_id == r.id)
        )

    token = sign_admin_link(settings.admin_link_secret, code, tg_id)
    admin_url = f"{settings.base_url}/admin/raffle/{code}?token={token}"

    if r.draw_mode == "time" and r.draw_at:
        draw_line = f"开奖时间：{r.draw_at.strftime('%Y-%m-%d %H:%M')}（上海时间）"
    elif r.draw_mode == "threshold" and (r.min_participants or 0) > 0:
        draw_line = f"开奖方式：人数达到 {r.min_participants} 后开奖"
    else:
        draw_line = f"开奖方式：{r.draw_mode}"

    text = (
        f"编号：{r.code}\n"
        f"标题：{r.title or '(未设置)'}\n"
        f"状态：{r.status}\n"
        f"参与人数：{int(total or 0)}\n"
        f"参与消耗：{r.cost_points} 积分\n"
        f"{draw_line}\n"
        f"目标群：{r.target_chat_id}\n"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️编辑（后台）", url=admin_url)],
            [InlineKeyboardButton(text="🗑删除该抽奖", callback_data=f"tixdel:{r.code}")],
        ]
    )
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("tixdel:"))
async def tixdelete_item(cb: CallbackQuery):
    code = cb.data.split(":", 1)[1]
    tg_id = cb.from_user.id
    if not _is_creator(tg_id):
        return await cb.answer("无权限", show_alert=True)

    # Best-effort: if a published message exists, try deleting it in the target group.
    published_chat_id = None
    published_message_id = None

    async with Session() as s:
        r = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not r or not _can_manage_raffle(r, tg_id):
            return await cb.answer("找不到该抽奖或无权限", show_alert=True)
        published_chat_id = int(r.target_chat_id) if r.target_chat_id else None
        published_message_id = int(r.published_message_id) if r.published_message_id else None
        await s.execute(delete(Raffle).where(Raffle.id == r.id))
        await s.commit()

    if published_chat_id and published_message_id:
        try:
            for cid in _target_chat_candidates(published_chat_id):
                try:
                    await cb.bot.delete_message(chat_id=cid, message_id=published_message_id)
                    break
                except Exception:
                    continue
        except Exception:
            pass

    await cb.answer("已删除", show_alert=False)
    try:
        await cb.message.answer(f"✅已删除抽奖：{code}")
    except Exception:
        pass


@router.callback_query(F.data.startswith("join:"))
async def join_request(cb: CallbackQuery):
    """Group-only join flow.

    Telegram 的同一条群消息无法为不同用户显示“私有”的内嵌键盘。
    为避免多人同时点击导致键盘互相覆盖，本项目采用：
    - 群置顶抽奖消息保持一个“参与抽奖”按钮
    - 用户点击后，机器人在群里回复一条“确认参加/取消”的确认消息（仅该用户可确认）
    全流程都在群内完成，不需要私聊。
    """
    if not cb.message:
        return await cb.answer("无效消息", show_alert=False)

    code = cb.data.split(":", 1)[1]
    user = cb.from_user

    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            return await cb.answer("抽奖不存在", show_alert=False)
        if raffle.status == "draft":
            return await cb.answer("该抽奖尚未发布", show_alert=False)
        if raffle.status == "drawn":
            return await cb.answer("该抽奖已结束（已开奖）", show_alert=False)
        if raffle.status != "published":
            return await cb.answer(f"该抽奖当前状态：{raffle.status}", show_alert=False)
        cost = int(raffle.cost_points or 0)
        title = raffle.title or raffle.code

        existing = await s.scalar(
            select(RaffleParticipant).where(RaffleParticipant.raffle_id == raffle.id, RaffleParticipant.tg_id == user.id)
        )
        if existing:
            if existing.status == "joined":
                return await cb.answer(
                    f"你已参与过，编号：{_format_participant_no(existing.participant_no)}", show_alert=False
                )
            return await cb.answer("你的参与请求正在处理中，请在确认消息里操作。", show_alert=False)

    ext = await _tgbot_get_user(user.id)
    if not ext:
        await _sync_local_user(user.id, user.username, user.first_name, user.last_name, None)
        return await cb.answer("未找到积分账户（tgbot.users）。请先在积分系统注册/同步。", show_alert=False)

    await _sync_local_user(user.id, user.username, user.first_name, user.last_name, ext)

    points = int(ext.get("points") or 0)
    email = ext.get("email") or "-"
    whmcs = ext.get("whmcs_client_id")
    uid = ext.get("id")

    display = escape(user.full_name or user.first_name or ("@" + user.username if user.username else str(user.id)))
    who = f"<a href=\"tg://user?id={user.id}\">{display}</a>"

    lines = [
        f"{who} 请确认是否参加抽奖：<b>{escape(title)}</b>",
        "",
        f"TGID：<code>{ext.get('tg_id')}</code>",
    ]
    if whmcs is not None:
        lines.append(f"WHMCS：<code>{whmcs}</code>")
    lines += [
        f"当前总积分：<b>{points}</b>",
        f"本次将消耗：<b>{cost}</b>",
    ]

    text_html = "\n".join(lines)

    try:
        await cb.bot.send_message(
            chat_id=cb.message.chat.id,
            reply_to_message_id=cb.message.message_id,
            text=text_html,
            parse_mode="HTML",
            reply_markup=_join_confirm_kb(code, user.id, cost),
            disable_web_page_preview=True,
        )
    except Exception:
        # Fallback: just answer
        return await cb.answer("请稍后再试", show_alert=False)

    return await cb.answer("请在下方确认参加或取消", show_alert=False)


@router.callback_query(F.data.startswith("jconfirm:"))
async def join_confirm(cb: CallbackQuery):
    # jconfirm:<code>:<owner_tg_id>
    parts = cb.data.split(":")
    code = parts[1] if len(parts) > 1 else ""
    owner_tg_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
    user = cb.from_user
    if owner_tg_id is not None and user.id != owner_tg_id:
        return await cb.answer("这不是你的确认按钮。", show_alert=False)

    # Step 1: reserve a participant row in local DB (avoid double-deduction on rapid clicks)
    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code).with_for_update())
        if not raffle:
            return await cb.answer("抽奖不存在", show_alert=False)
        if raffle.status == "draft":
            return await cb.answer("该抽奖尚未发布", show_alert=False)
        if raffle.status == "drawn":
            return await cb.answer("该抽奖已结束（已开奖）", show_alert=False)
        if raffle.status != "published":
            return await cb.answer(f"该抽奖当前状态：{raffle.status}", show_alert=False)

        existing = await s.scalar(
            select(RaffleParticipant).where(RaffleParticipant.raffle_id == raffle.id, RaffleParticipant.tg_id == user.id)
        )
        if existing:
            if existing.status == "joined":
                return await cb.answer(
                    f"你已参与过，编号：{_format_participant_no(existing.participant_no)}", show_alert=False
                )
            # pending/other
            return await cb.answer("参与请求正在处理中，请稍后再试。", show_alert=False)

        # Reserve a random participant number (fixed length). Retry on collision.
        last_err: Exception | None = None
        for _ in range(20):
            pn = _gen_participant_no()
            p = RaffleParticipant(
                raffle_id=raffle.id,
                tg_id=user.id,
                username=user.username,
                participant_no=pn,
                status="pending",
                hash_hex=f"pending:{int(time.time())}",
            )
            s.add(p)
            try:
                await s.commit()
                break
            except IntegrityError as e:
                await s.rollback()
                last_err = e
                # If the user row already exists (double click race), just inform.
                ex2 = await s.scalar(
                    select(RaffleParticipant).where(
                        RaffleParticipant.raffle_id == raffle.id, RaffleParticipant.tg_id == user.id
                    )
                )
                if ex2 and ex2.status == "joined":
                    return await cb.answer(
                        f"你已参与过，编号：{_format_participant_no(ex2.participant_no)}", show_alert=False
                    )
                continue
        else:
            # Too many collisions; very unlikely.
            return await cb.answer("系统繁忙，请稍后重试。", show_alert=False)

    # Step 2: deduct points in external DB
    cost = 0
    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        cost = int(raffle.cost_points or 0) if raffle else 0

    if cost > 0:
        ext = await _tgbot_deduct_points(user.id, cost)
        if not ext:
            # rollback local pending record
            async with Session() as s:
                raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
                if raffle:
                    await s.execute(
                        delete(RaffleParticipant).where(
                            RaffleParticipant.raffle_id == raffle.id, RaffleParticipant.tg_id == user.id, RaffleParticipant.status == "pending"
                        )
                    )
                    await s.commit()
            # show current points if we can read
            ext2 = await _tgbot_get_user(user.id)
            cur = int(ext2.get("points") or 0) if ext2 else 0
            return await cb.answer(f"积分不足：{cur}/{cost}（未扣分）", show_alert=False)
    else:
        ext = await _tgbot_get_user(user.id)

    # Step 3: finalize local participant + ledger + sync local user
    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code))
        if not raffle:
            return await cb.answer("抽奖不存在", show_alert=False)
        part = await s.scalar(
            select(RaffleParticipant).where(RaffleParticipant.raffle_id == raffle.id, RaffleParticipant.tg_id == user.id)
        )
        if not part:
            # Extremely rare (local row removed). Do not re-deduct; just ask retry.
            await _sync_local_user(user.id, user.username, user.first_name, user.last_name, ext)
            return await cb.answer("参与记录丢失，请重新点击确认参与。", show_alert=False)

        part.status = "joined"
        part.username = user.username
        part.hash_hex = part.hash_hex or ""
        part.joined_at = now_local()
        # Store receipt message info for post-draw cleanup (delete 1 day after draw)
        try:
            if cb.message:
                part.receipt_chat_id = int(cb.message.chat.id)
                part.receipt_message_id = int(cb.message.message_id)
        except Exception:
            pass
        if ext and ext.get("points") is not None:
            await _sync_local_user(user.id, user.username, user.first_name, user.last_name, ext)

        if cost > 0:
            s.add(
                PointsLedger(
                    tg_id=user.id,
                    delta=-cost,
                    reason="join_raffle",
                    ref_type="raffle",
                    ref_code=raffle.code,
                )
            )
        await s.commit()

    # Build confirmation text (in group), mention user, remove buttons.
    remaining = None
    if ext and ext.get("points") is not None:
        remaining = int(ext.get("points") or 0)

    who = mention_html(user.id, user.username, user.first_name)
    msg_text = f"✅参与成功！{who}，你的编号：<code>{escape(_format_participant_no(part.participant_no))}</code>"
    if cost > 0 and remaining is not None:
        msg_text += f"\n消耗 <b>{cost}</b> 积分，当前总积分：<b>{remaining}</b>"

    try:
        await cb.message.edit_text(msg_text, parse_mode="HTML", reply_markup=None, disable_web_page_preview=True)
    except Exception:
        pass

    return await cb.answer("已确认参加", show_alert=False)


@router.callback_query(F.data.startswith("jcancel:"))
async def join_cancel(cb: CallbackQuery):
    # jcancel:<code>:<owner_tg_id>
    parts = cb.data.split(":")
    code = parts[1] if len(parts) > 1 else ""
    owner_tg_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
    if owner_tg_id is not None and cb.from_user.id != owner_tg_id:
        return await cb.answer("这不是你的取消按钮。", show_alert=False)
    try:
        await cb.message.edit_text("已取消参与。", reply_markup=None)
    except Exception:
        pass
    return await cb.answer("已取消", show_alert=False)


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN 未配置。请在 .env 中填写 BOT_TOKEN")
    if not settings.tgbot_database_url:
        raise RuntimeError("TGBOT_DATABASE_URL 未配置。请在 .env 中填写积分数据库连接")

    print("[tixbot] BASE_URL=", settings.base_url)
    print("[tixbot] TARGET_CHAT_ID=", settings.target_chat_id)
    print("[tixbot] TGBOT_DATABASE_URL=", settings.tgbot_database_url)
    print("[tixbot] TZ_NAME=", settings.tz_name)

    bot = Bot(settings.bot_token)

    # Hide commands in groups (client-side) by clearing group scopes,
    # and only expose /tixnew /tixedit /tixclean in private chats.
    try:
        await bot.set_my_commands([], scope=BotCommandScopeDefault())
        await bot.set_my_commands([], scope=BotCommandScopeAllGroupChats())
        await bot.set_my_commands([], scope=BotCommandScopeAllChatAdministrators())
        await bot.set_my_commands(
            [
                BotCommand(command="tixnew", description="创建抽奖（仅管理员）"),
                BotCommand(command="tixedit", description="管理我创建的抽奖"),
                BotCommand(command="tixclean", description="清理历史抽奖记录（仅管理员）"),
            ],
            scope=BotCommandScopeAllPrivateChats(),
        )
    except Exception:
        # Not critical; command menu setup may fail if the bot has no access yet.
        pass
    await init_db(engine)

    # Background loops
    asyncio.create_task(_auto_draw_loop(bot))
    asyncio.create_task(_post_draw_cleanup_loop(bot))

    dp = Dispatcher()
    dp.include_router(router)
    try:
        await dp.start_polling(bot)
    finally:
        # Avoid "Unclosed client session" warnings from aiohttp.
        try:
            await bot.session.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
