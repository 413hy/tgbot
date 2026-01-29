from __future__ import annotations

from datetime import datetime

from app.time_utils import now_local

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


# SQLite only auto-increments reliably for INTEGER PRIMARY KEY.
# Use a dialect variant so the same models work on MySQL (BIGINT) and SQLite (INTEGER).
BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class TgUser(Base):
    __tablename__ = "tg_users"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    points: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Synced from external `tgbot`.`user` table when the user participates
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whmcs_client_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_local)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_local)


class TgChat(Base):
    __tablename__ = "tg_chats"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_local)


class UserChatContext(Base):
    __tablename__ = "user_chat_context"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_local)


class Raffle(Base):
    __tablename__ = "raffles"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    creator_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    join_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="button")

    cost_points: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    # SQLAlchemy JSON works for MySQL/SQLite/Postgres. On MySQL it maps to JSON type.
    required_chats: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    min_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    draw_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="time")
    draw_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    min_participants: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    published_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pinned_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    draw_pinned_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    draw_block_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    draw_block_height: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    drawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    next_participant_no: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_local)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_local)

    prizes: Mapped[list["RafflePrize"]] = relationship(back_populates="raffle", cascade="all, delete-orphan")
    participants: Mapped[list["RaffleParticipant"]] = relationship(back_populates="raffle", cascade="all, delete-orphan")


Index("idx_raffles_creator", Raffle.creator_tg_id)
Index("idx_raffles_target_chat", Raffle.target_chat_id)


class RafflePrize(Base):
    __tablename__ = "raffle_prizes"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    raffle_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("raffles.id", ondelete="CASCADE"), nullable=False)

    # 奖品类型：积分 / VPS / NAT机 / 优惠码 / 自定义
    # points:      自动加积分（写入 tgbot.prize_wins 时 auto_credit=1）
    # vps/nat/discount_code/custom: 只记录，手动发放
    prize_type: Mapped[str] = mapped_column(String(16), nullable=False, default="custom")

    # 展示名称（非积分/或自定义时存自定义名称）
    prize_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # 数量（该奖品发放份数）
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 积分奖：每份积分数量（仅 prize_type=points 有效）
    points_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # 自定义奖：自定义名称（可选，通常与 prize_name 相同）
    custom_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    raffle: Mapped[Raffle] = relationship(back_populates="prizes")


Index("idx_prizes_raffle", RafflePrize.raffle_id)


class RaffleParticipant(Base):
    __tablename__ = "raffle_participants"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    raffle_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("raffles.id", ondelete="CASCADE"), nullable=False)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    participant_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="joined")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_local)

    # Receipt message in group after user confirms participation.
    receipt_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    receipt_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    receipt_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    hash_hex: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    #开奖后写入（显示在参与者页 score 列）
    win_prize: Mapped[str | None] = mapped_column(String(255), nullable=True)
    win_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raffle: Mapped[Raffle] = relationship(back_populates="participants")


Index("idx_participants_raffle", RaffleParticipant.raffle_id)
Index("idx_participants_score", RaffleParticipant.raffle_id, RaffleParticipant.score)


class PointsLedger(Base):
    __tablename__ = "points_ledger"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_local)


Index("idx_ledger_tg", PointsLedger.tg_id)
Index("idx_ledger_ref", PointsLedger.ref_type, PointsLedger.ref_code)


class ChatUserStats(Base):
    __tablename__ = "chat_user_stats"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index("idx_stats_chat", ChatUserStats.chat_id)
Index("idx_stats_user", ChatUserStats.tg_id)
