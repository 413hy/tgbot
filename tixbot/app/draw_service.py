from __future__ import annotations

from dataclasses import dataclass
import json
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import time

import httpx
from sqlalchemy import select, text

from app.models import Raffle, RaffleParticipant, RafflePrize, TgUser
from app.raffle_logic import score_for
from app.time_utils import now_local, tz_name as cfg_tz_name


@dataclass(frozen=True)
class EntropyInfo:
    """Randomness source used for the draw.

    source:
      - "drand": League of Entropy public randomness beacon (updates frequently)
      - "btc":   Bitcoin latest block hash
    """

    source: str
    value: str
    ref_num: int | None = None


def now_shanghai(tz_name: str = "Asia/Shanghai") -> datetime:
    """Backward compatible helper.

    The project stores naive datetimes and treats them as local time in TZ_NAME.
    """
    # Prefer the configured TZ_NAME env if caller passes default.
    if tz_name == "Asia/Shanghai":
        # use configured TZ_NAME if set
        os_tz = cfg_tz_name()
        try:
            tz_name = os_tz
        except Exception:
            pass
    # now_local already uses TZ_NAME; keep signature for older callers.
    if tz_name == cfg_tz_name():
        return now_local()
    tz = ZoneInfo(tz_name)
    return datetime.now(tz).replace(tzinfo=None, microsecond=0)


async def fetch_latest_entropy() -> EntropyInfo:
    """Fetch draw entropy.

    优先使用 drand 公共随机信标（更新频率高，适合定时开奖即时触发）：
      - https://api.drand.sh/public/latest
      - https://api2.drand.sh/public/latest
      - https://api3.drand.sh/public/latest
      - https://drand.cloudflare.com/public/latest

    失败时回退到 Bitcoin 最新区块（Blockstream / blockchain.info）。

    优先使用 Blockstream Esplora API（公开、稳定、返回纯文本）：
      - https://blockstream.info/api/blocks/tip/hash
      - https://blockstream.info/api/blocks/tip/height

    失败时回退到 blockchain.info 的 JSON 接口：
      - https://blockchain.info/latestblock
    """
    headers = {
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": "tixbot/1.0",
    }
    ts = int(time.time())

    async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True) as client:
        # 0) drand (fast-updating public randomness)
        drand_endpoints = [
            "https://api.drand.sh/public/latest",
            "https://api2.drand.sh/public/latest",
            "https://api3.drand.sh/public/latest",
            "https://drand.cloudflare.com/public/latest",
        ]
        for url in drand_endpoints:
            try:
                r = await client.get(url)
                r.raise_for_status()
                j = r.json()
                rnd = j.get("round")
                randomness = (j.get("randomness") or "").strip()
                if randomness and len(randomness) >= 32:
                    try:
                        ref = int(rnd) if rnd is not None else None
                    except Exception:
                        ref = None
                    return EntropyInfo(source="drand", value=randomness, ref_num=ref)
            except Exception:
                continue

        # 1) Bitcoin via Blockstream tip
        try:
            h_resp = await client.get("https://blockstream.info/api/blocks/tip/hash")
            h_resp.raise_for_status()
            block_hash = h_resp.text.strip()

            ht_resp = await client.get("https://blockstream.info/api/blocks/tip/height")
            ht_resp.raise_for_status()
            height_txt = ht_resp.text.strip()
            height = int(height_txt)

            if block_hash and len(block_hash) >= 10:
                return EntropyInfo(source="btc", value=block_hash, ref_num=height)
        except Exception:
            pass

        # 2) blockchain.info latestblock (add a cache-busting query param)
        resp = await client.get(f"https://blockchain.info/latestblock?cors=true&_={ts}")
        resp.raise_for_status()
        data = resp.json()
        block_hash = str(data.get("hash") or "").strip()
        height = data.get("height")
        if not block_hash:
            raise RuntimeError("无法获取随机种子")
        return EntropyInfo(source="btc", value=block_hash, ref_num=int(height) if height is not None else None)


def mention_html(tg_id: int, username: str | None, first_name: str | None = None) -> str:
    """Safe HTML mention."""
    if username:
        display = "@" + username.lstrip("@")
    else:
        display = first_name or f"用户{tg_id}"
    return f"<a href=\"tg://user?id={tg_id}\">{escape(display)}</a>"




def prize_label(prize: RafflePrize) -> str:
    """Human label for prize (used in TG text / winners / prize_wins)."""
    ptype = getattr(prize, "prize_type", None)
    if ptype == "points":
        try:
            return f"{int(getattr(prize, 'points_amount', 0) or 0)} 积分"
        except Exception:
            return "积分"
    if ptype == "custom":
        return (getattr(prize, "custom_label", None) or prize.prize_name)
    return prize.prize_name



async def write_prize_wins_to_tgbot(TGBotSession, raffle_code: str, raffle_title: str, winners_info: list[dict], drawn_at) -> tuple[bool, str]:
    """Write winners into tgbot.prize_wins.

    - 积分奖：prize_type='points' 且 auto_credit=1（依赖你在 tgbot.prize_wins 上的触发器自动给 tgbot.users.points 加分）
    - 其它奖：只记录，status=pending

    说明：为了幂等，使用 (raffle_code, win_rank) 的唯一键做 upsert。
    """
    if TGBotSession is None:
        return True, ""
    if not winners_info:
        return True, ""

    try:
        async with TGBotSession() as s:
            for w in winners_info:
                tg_id = int(w.get("tg_id"))
                # Snapshot user fields from tgbot.users (optional)
                email = None
                whmcs = None
                try:
                    res = await s.execute(text("SELECT email, whmcs_client_id FROM users WHERE tg_id=:tg_id LIMIT 1"), {"tg_id": tg_id})
                    row = res.first()
                    if row:
                        email = row[0]
                        whmcs = row[1]
                except Exception:
                    pass

                prize_type = (w.get("prize_type") or "other")
                prize_name = (w.get("prize_name") or "")[:255] or "(未命名奖品)"
                quantity = int(w.get("quantity") or 1)
                points_amount = w.get("points_amount")

                auto_credit = 1 if prize_type == "points" else 0
                status = "fulfilled" if auto_credit else "pending"
                fulfilled_at = drawn_at if auto_credit else None

                meta = {"source": "tixbot", "raffle_code": raffle_code}
                if w.get("custom_label"):
                    meta["custom_label"] = w.get("custom_label")
                meta_json = json.dumps(meta, ensure_ascii=False)

                params = {
                    "raffle_code": raffle_code,
                    "raffle_title": raffle_title,
                    "tg_id": tg_id,
                    "email": email,
                    "whmcs_client_id": whmcs,
                    "win_rank": int(w.get("win_rank") or 0),
                    "participant_no": str(w.get("participant_no") or ""),
                    "prize_type": prize_type,
                    "prize_name": prize_name,
                    "quantity": quantity,
                    "points_amount": points_amount,
                    "status": status,
                    "auto_credit": auto_credit,
                    "note": "tixbot raffle draw",
                    "meta": meta_json,
                    "created_at": drawn_at,
                    "fulfilled_at": fulfilled_at,
                }

                sql = text(
                    """
                    INSERT INTO prize_wins (
                      raffle_code, raffle_title, user_id, tg_id, email, whmcs_client_id,
                      win_rank, participant_no,
                      prize_type, prize_name, quantity, points_amount,
                      status, auto_credit, note, meta,
                      created_at, fulfilled_at
                    ) VALUES (
                      :raffle_code, :raffle_title, NULL, :tg_id, :email, :whmcs_client_id,
                      :win_rank, :participant_no,
                      :prize_type, :prize_name, :quantity, :points_amount,
                      :status, :auto_credit, :note, CAST(:meta AS JSON),
                      :created_at, :fulfilled_at
                    )
                    ON DUPLICATE KEY UPDATE
                      raffle_title = VALUES(raffle_title),
                      tg_id = VALUES(tg_id),
                      email = VALUES(email),
                      whmcs_client_id = VALUES(whmcs_client_id),
                      participant_no = VALUES(participant_no),
                      prize_type = VALUES(prize_type),
                      prize_name = VALUES(prize_name),
                      quantity = VALUES(quantity),
                      points_amount = VALUES(points_amount),
                      status = VALUES(status),
                      auto_credit = VALUES(auto_credit),
                      note = VALUES(note),
                      meta = VALUES(meta),
                      created_at = VALUES(created_at),
                      fulfilled_at = VALUES(fulfilled_at)
                    """
                )
                await s.execute(sql, params)

            await s.commit()

        return True, ""
    except Exception as e:
        return False, f"写入 tgbot.prize_wins 失败：{e}"
async def draw_raffle(Session, tz_name: str, code: str, bot=None, TGBotSession=None) -> tuple[bool, str]:
    """Compute draw result, persist to DB, and optionally announce to Telegram.

    Returns (ok, message)."""

    # 1) Lock raffle row and compute results
    async with Session() as s:
        raffle = await s.scalar(select(Raffle).where(Raffle.code == code).with_for_update())
        if not raffle:
            return False, "抽奖不存在"
        if raffle.status == "drawn":
            return False, "该抽奖已结束"
        if raffle.status != "published":
            return False, "抽奖未发布，无法开奖"

        prizes = (
            await s.scalars(
                select(RafflePrize).where(RafflePrize.raffle_id == raffle.id).order_by(RafflePrize.id.asc())
            )
        ).all()
        total_prizes = sum(int(p.quantity or 0) for p in prizes)
        if total_prizes <= 0:
            return False, "未配置奖品数量，无法开奖"

        participants = (
            await s.scalars(
                select(RaffleParticipant)
                .where(RaffleParticipant.raffle_id == raffle.id, RaffleParticipant.status == "joined")
                .order_by(RaffleParticipant.id.asc())
            )
        ).all()
        if not participants:
            return False, "暂无参与者，无法开奖"

        entropy = await fetch_latest_entropy()

        # Debug log (avoid spamming the same line every few seconds)
        try:
            global _LAST_DRAW_LOG  # type: ignore
        except Exception:
            _LAST_DRAW_LOG = {}
        try:
            now_ts = int(time.time())
            last = int(_LAST_DRAW_LOG.get(str(raffle.code), 0))
            if now_ts - last >= 60:
                _LAST_DRAW_LOG[str(raffle.code)] = now_ts
                ref = entropy.ref_num
                ref_str = f"ref={ref}" if ref is not None else "ref=?"
                print(
                    f"[tixbot] draw raffle={raffle.code} source={entropy.source} {ref_str} value={entropy.value[:16]}..."
                )
        except Exception:
            pass

        # score all
        for p in participants:
            h, sc = score_for(entropy.value, raffle.code, int(p.participant_no))
            p.hash_hex = h
            p.score = int(sc)

        participants.sort(key=lambda x: (x.score or 0, x.participant_no))

        winners = participants[: min(total_prizes, len(participants))]
        winner_ids = {w.id for w in winners}

        # assign prizes sequentially (by unit) and capture winners_info for external prize_wins
        prize_units: list[RafflePrize] = []
        for prize in prizes:
            qty = int(prize.quantity or 0)
            if qty <= 0:
                continue
            for _ in range(qty):
                prize_units.append(prize)

        winners_info: list[dict] = []
        idx = 0
        for prize in prize_units:
            if idx >= len(winners):
                break
            w = winners[idx]
            w.status = "won"
            w.win_rank = idx + 1
            w.win_prize = prize_label(prize)

            ptype = getattr(prize, "prize_type", None) or "other"
            # map custom -> other (tgbot.prize_wins enum has 'other')
            tgbot_ptype = "other" if ptype == "custom" else ptype
            pa = None
            if ptype == "points":
                try:
                    pa = int(getattr(prize, "points_amount", 0) or 0)
                except Exception:
                    pa = 0

            winners_info.append(
                {
                    "tg_id": int(w.tg_id),
                    "participant_no": str(w.participant_no),
                    "win_rank": int(w.win_rank),
                    "prize_type": tgbot_ptype,
                    "prize_name": prize_label(prize),
                    "quantity": 1,
                    "points_amount": pa,
                    "custom_label": getattr(prize, "custom_label", None),
                }
            )

            idx += 1

        winner_ids = {w.id for w in winners[:idx]}

        for p in participants:
            if p.id not in winner_ids:
                p.status = "lost"
                p.win_prize = None
                p.win_rank = None

        raffle.draw_block_hash = entropy.value
        raffle.draw_block_height = entropy.ref_num
        raffle.drawn_at = now_shanghai(tz_name)
        raffle.status = "drawn"
        raffle.updated_at = raffle.drawn_at

        await s.commit()

        raffle_id = int(raffle.id)
        target_chat_id = int(raffle.target_chat_id)
        title = raffle.title or raffle.code
        drawn_at = raffle.drawn_at
        entropy_value = entropy.value
        entropy_ref = entropy.ref_num
        entropy_source = entropy.source

    # 2) Build announcement text (outside lock)
    tgbot_warn = ""
    ok_tg, warn_tg = await write_prize_wins_to_tgbot(TGBotSession, code, title, winners_info, drawn_at)
    if not ok_tg and warn_tg:
        tgbot_warn = warn_tg

    if bot is None:
        return True, "开奖完成（未发送 TG 通知）" + (f"；{tgbot_warn}" if tgbot_warn else "")

    # Load display names from tg_users (best-effort)
    async with Session() as s:
        rows = (
            await s.scalars(
                select(RaffleParticipant)
                .where(RaffleParticipant.raffle_id == raffle_id)
            )
        ).all()
        # map tg_id -> (username, first_name)
        user_map: dict[int, tuple[str | None, str | None]] = {}
        urows = (
            await s.scalars(select(TgUser).where(TgUser.tg_id.in_([r.tg_id for r in rows])))
        ).all()
        for u in urows:
            user_map[int(u.tg_id)] = (u.username, u.first_name)

        winners_rows = [r for r in rows if r.status == "won"]
        winners_rows.sort(key=lambda x: (x.win_rank or 10**9, x.score or 0))

    lines = []
    for w in winners_rows:
        uname, fname = user_map.get(int(w.tg_id), (w.username, None))
        who = mention_html(int(w.tg_id), uname, fname)
        prize = w.win_prize or "(未命名奖品)"
        lines.append(f"{w.win_rank or '-'}）{who} — {escape(prize)}")

    winners_text = "\n".join(lines) if lines else "（无）"

    if entropy_source == "drand":
        seed_title = "随机信标(drand)"
        seed_ref = f"round：<code>{entropy_ref}</code>\n" if entropy_ref is not None else ""
    else:
        seed_title = "比特币区块"
        seed_ref = f"区块高度：<code>{entropy_ref}</code>\n" if entropy_ref is not None else ""

    msg = (
        f"🎊 抽奖已开奖（上海时间 {drawn_at.strftime('%Y-%m-%d %H:%M')}）\n"
        f"抽奖：{escape(title)}\n"
        f"编号：{escape(code)}\n\n"
        f"随机种子来源：{seed_title}\n"
        + seed_ref
        + f"种子值：<code>{escape(entropy_value)}</code>\n\n"
        f"中奖通知（请尽快兑奖）：\n{winners_text}\n\n"
        "验证方式：score = hexdec(SHA256(种子值 + 抽奖编号 + 参与编号) 前16位)，score 越小排名越靠前。"
    )

    try:
        await bot.send_message(
            chat_id=target_chat_id,
            text=msg,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        return True, f"开奖完成，但 TG 通知发送失败：{e}"

    return True, "开奖完成并已发送中奖通知" + (f"；{tgbot_warn}" if tgbot_warn else "")
