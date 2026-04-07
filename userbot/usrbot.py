import os
import random
import smtplib
import re
import json
from datetime import datetime, timedelta, date
from email.mime.text import MIMEText
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import mysql.connector
from mysql.connector import Error
import ipaddress
import requests
import string
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import BotCommand, BotCommandScopeChat, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
import asyncio


load_dotenv()

# 配置（不变）
TG_DB_CONFIG = {
    'host': os.getenv('TG_DB_HOST'),
    'port': int(os.getenv('TG_DB_PORT', 3306)),
    'user': os.getenv('TG_DB_USER'),
    'password': os.getenv('TG_DB_PASSWORD'),
    'database': os.getenv('TG_DB_NAME')
}
WHMCS_DB_CONFIG = {
    'host': os.getenv('WHMCS_DB_HOST'),
    'port': int(os.getenv('WHMCS_DB_PORT', 3306)),
    'user': os.getenv('WHMCS_DB_USER'),
    'password': os.getenv('WHMCS_DB_PASSWORD'),
    'database': os.getenv('WHMCS_DB_NAME')
}
TG_TOKEN = os.getenv('TG_TOKEN')

# SMTP 配置（不变）
SMTP_SERVER = 'sg-smtp.qcloudmail.com'
SMTP_PORT = 465
SMTP_USER = os.getenv('SMTP_USER', 'tgbot@stormhost.net')
SMTP_PASS = os.getenv('SMTP_PASS', 'hjhD7XNEdgS2')
EMAIL_REGEX = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')

# 对话状态
UNBIND_CONFIRM = range(1)
SELECT_OPTION, CONFIRM, SELECT_NAT_SERVICE = range(3)

UNBIND_CONFIRM = 1
EXCHANGE_SELECT = 2
EXCHANGE_CONFIRM = 3
EXCHANGE_NAT_SELECT = 4

CHANGE_EMAIL_CONFIRM = 10
CHANGE_EMAIL_WAIT_CODE = 11


# 私聊主菜单键盘（放在文件全局或函数外）
MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
    [KeyboardButton("📅签到"), KeyboardButton("👤个人"), KeyboardButton("📝日志")]
    ],
    resize_keyboard=True,          # 自动调整大小，推荐开启
    one_time_keyboard=False,       # 不自动隐藏
    is_persistent=True,            # 持久显示（v20+ 支持，强烈推荐）
    input_field_placeholder="选择操作"  # 输入框提示文字（可选）
)

def get_tg_db():
    return mysql.connector.connect(**TG_DB_CONFIG)

def get_whmcs_db():
    return mysql.connector.connect(**WHMCS_DB_CONFIG)

def is_bound(tg_id: int) -> tuple | None:
    try:
        with get_tg_db() as db:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT whmcs_client_id, email, points FROM users WHERE tg_id = %s",
                    (tg_id,)
                )
                return cursor.fetchone()
    except Error as e:
        print(f"is_bound DB Error: {e}")
        return None

def clean_expired_discount_codes():
    try:
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute("""
                    SELECT id, whmcs_promo_id
                    FROM user_discount_codes
                    WHERE expires_at < NOW() OR used = 1
                """)
                expired = cursor_tg.fetchall()
                if expired:
                    with get_whmcs_db() as db_whmcs:
                        with db_whmcs.cursor() as cursor_whmcs:
                            expired_ids = []
                            for row in expired:
                                promo_id = row[1]
                                if promo_id:
                                    cursor_whmcs.execute("DELETE FROM tblpromotions WHERE id = %s", (promo_id,))
                                expired_ids.append(row[0])
                            if expired_ids:
                                placeholders = ','.join(['%s'] * len(expired_ids))
                                cursor_tg.execute(f"DELETE FROM user_discount_codes WHERE id IN ({placeholders})", expired_ids)
                        db_whmcs.commit()
                db_tg.commit()
    except Error as e:
        print(f"清理过期折扣码失败: {e}")

def is_nat_service(row: dict) -> bool:
    if row.get('product_name') and 'NAT' in row['product_name'].upper():
        return True
    ip = row.get('dedicatedip')
    if ip:
        try:
            if ipaddress.ip_address(ip).is_private:
                return True
        except:
            pass
    server_json = row.get('server_object')
    if server_json:
        try:
            data = json.loads(server_json) if isinstance(server_json, str) else server_json
            if data.get('network', {}).get('interfaces', [{}])[0].get('isNat', False):
                return True
            if data.get('hypervisor', {}).get('group', {}).get('id') == 6:
                return True
        except:
            pass
    return False

def get_user_vps_info(
    whmcs_client_id: int,
    tg_id: int,
    email: str,
    points: int | None = None
) -> str:
    try:
        with get_whmcs_db() as db:
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT
                        h.id AS hosting_id,
                        h.dedicatedip AS ip,
                        h.regdate AS create_date,
                        h.nextduedate AS next_due,
                        h.domainstatus AS status,
                        h.domain AS name,
                        p.name AS product_name,
                        vf.server_object AS server_json
                    FROM tblhosting h
                    LEFT JOIN tblproducts p ON h.packageid = p.id
                    LEFT JOIN mod_virtfusion_direct vf ON vf.service_id = h.id
                    WHERE h.userid = %s
                    ORDER BY h.id
                """, (whmcs_client_id,))
                rows = cursor.fetchall()

        total_vps = len(rows)
        active_count = sum(1 for row in rows if row['status'] == 'Active')

        header_lines = [
            f"👤 Telegram ID: {tg_id}",
            f"📧 邮箱: {email}",
            f"💎 当前积分: {points if points is not None else '查询中'}",
            f"🖥️ Active VPS 总数: {active_count}",
        ]
        header = "\n".join(header_lines) + "\n-------------------------------------\n"

        if total_vps == 0:
            return header + "∅ 暂无 VPS 服务记录"

        infos = []
        for row in rows:
            if row['status'] != 'Active':
                continue
            is_nat = is_nat_service(row)
            nat_tag = " (NAT 机)" if is_nat else ""
            ip = row['ip'] or 'N/A'
            infos.append(
                f"服务 ID: {row['hosting_id']} (状态: {row['status']}){nat_tag}\n"
                f"产品类型: {row['product_name'] or 'N/A'}\n"
                f"IP: {ip}\n"
                f"开通日期: {row['create_date'] or 'N/A'}\n"
                f"到期日期: {row['next_due'] or 'N/A'}"
            )

        if not infos:
            return header + "暂无 Active 状态的 VPS 服务"

        return header + "\n\n".join(infos)

    except Exception as e:
        print(f"get_user_vps_info Error: {e}")
        return f"⚠️ 获取 VPS 信息失败：{str(e)}"

def send_verification_email(email: str, code: str):
    msg = MIMEText(f"您的 StormHost TG 验证码: {code}\n有效期 10 分钟。")
    msg['Subject'] = 'StormHost TG 验证'
    msg['From'] = SMTP_USER
    msg['To'] = email
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"SMTP Error: {e}")

# ───────────── 所有命令处理函数（必须在 main() 之前） ─────────────

async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    tg_id = update.effective_user.id
    args = context.args

    if chat_type != "private":
        # 群聊：回复提示，并调度删除（用户命令 + bot 提示）
        reply_msg = await update.message.reply_text(
            "⚠️ 该功能涉及邮箱和验证码等隐私信息，仅限私聊使用。\n"
            "请私聊机器人 @stormuser_bot 操作。"
        )
        # 加删除调度（和 sign 一致）
        await _schedule_group_cleanup(context, update, reply_msg)
        return

    # 以下是私聊正常绑定逻辑（不变）
    bound = is_bound(tg_id)
    if bound:
        _, email, _ = bound
        info = get_user_vps_info(bound[0], tg_id, email, points=bound[2])
        await update.message.reply_text(f"✅ 您已绑定账户。\n\n{info}")
        return

    if not args:
        await update.message.reply_text("⌨️ 请输入: /bind 您的邮箱")
        return

    email = args[0].strip().lower()
    if not EMAIL_REGEX.match(email):
        await update.message.reply_text("❌ 请输入正确的邮箱格式")
        return

    try:
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute("SELECT tg_id FROM users WHERE email = %s", (email,))
                existing_tg = cursor_tg.fetchone()
                if existing_tg:
                    if existing_tg[0] == tg_id:
                        await update.message.reply_text("您已经绑定过这个邮箱了，请直接使用 /user 查看")
                    else:
                        await update.message.reply_text(
                            f"⚠️ 该邮箱 {email} 已经被其他 Telegram 账号绑定。"
                        )
                    return

        with get_whmcs_db() as db_whmcs:
            with db_whmcs.cursor() as cursor_whmcs:
                cursor_whmcs.execute("SELECT id FROM tblclients WHERE email = %s", (email,))
                row = cursor_whmcs.fetchone()
                client_id = row[0] if row else None

        if not client_id:
            await update.message.reply_text(
                "🔍 未找到该邮箱，请先到 <a href=\"https://billing.stormhost.net/\">官网</a> 注册账号",
                parse_mode="HTML"
            )
            return

        code = ''.join(random.choices('0123456789', k=6))
        expires = datetime.now() + timedelta(minutes=10)
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute("DELETE FROM verification_codes WHERE tg_id = %s", (tg_id,))
                cursor_tg.execute("""
                    INSERT INTO verification_codes (tg_id, email, code, expires_at)
                    VALUES (%s, %s, %s, %s)
                """, (tg_id, email, code, expires))
            db_tg.commit()

        send_verification_email(email, code)
        await update.message.reply_text(
            f"📩 验证码已发送到您的邮箱 {email}，有效期 10 分钟。\n"
            "请使用 `/verify 验证码` 完成绑定"
        )

    except Exception as e:
        print(f"bind error: {e}")
        await update.message.reply_text("⚠️ 处理失败，请稍后重试")

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type != "private":
        reply_msg = await update.message.reply_text(
            "⚠️ 该功能涉及验证码和绑定信息，仅限私聊使用。\n"
            "请私聊 @stormuser_bot 机器人操作。"
        )
        await _schedule_group_cleanup(context, update, reply_msg)
        return

    tg_id = update.effective_user.id
    args = context.args
    bound = is_bound(tg_id)
    if bound:
        _, email, points = bound
        info = get_user_vps_info(bound[0], tg_id, email, points=points)
        await update.message.reply_text(f"✅ 您已绑定账户。\n\n{info}")
        return
    if not args:
        await update.message.reply_text("⌨️ 请输入: /verify 验证码")
        return
    code = args[0]
    try:
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute("""
                    SELECT email FROM verification_codes
                    WHERE tg_id = %s AND code = %s AND expires_at > NOW()
                """, (tg_id, code))
                row = cursor_tg.fetchone()
                if not row:
                    await update.message.reply_text("❌ 验证码错误或已过期，请重新使用 /bind 获取")
                    return
                email = row[0]
        with get_whmcs_db() as db_whmcs:
            with db_whmcs.cursor() as cursor_whmcs:
                cursor_whmcs.execute("SELECT id FROM tblclients WHERE email = %s", (email,))
                client_row = cursor_whmcs.fetchone()
                client_id = client_row[0] if client_row else None
                if not client_id:
                    await update.message.reply_text("⚠️ 该邮箱未在官网注册，请检查")
                    return
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute("SELECT 1 FROM users WHERE email = %s", (email,))
                if cursor_tg.fetchone():
                    await update.message.reply_text("⚠️ 该邮箱已被其他账号绑定，无法重复绑定")
                    return
                cursor_tg.execute("""
                    INSERT INTO users (tg_id, whmcs_client_id, email, points)
                    VALUES (%s, %s, %s, 0)
                """, (tg_id, client_id, email))
                cursor_tg.execute("DELETE FROM verification_codes WHERE tg_id = %s", (tg_id,))
            db_tg.commit()
        info = get_user_vps_info(client_id, tg_id, email, points=0)
        await update.message.reply_text(f"🎉 验证成功！账户已成功绑定。\n\n{info}")
    except Exception as e:
        print(f"verify error: {e}")
        await update.message.reply_text("⚠️ 处理失败，请稍后重试")

async def unbind_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type != "private":
        reply_msg = await update.message.reply_text(
            "⚠️ 解除绑定涉及隐私信息，仅限私聊使用。\n"
            "请私聊 @stormuser_bot 机器人操作。"
        )
        await _schedule_group_cleanup(context, update, reply_msg)
        return ConversationHandler.END

    tg_id = update.effective_user.id
    bound = is_bound(tg_id)
    if not bound:
        await update.message.reply_text("⚠️ 您还未绑定账号哦")
        return ConversationHandler.END
    _, email, _ = bound
    context.user_data['unbind_email'] = email
    await update.message.reply_text(
        f"⚠️ 您确定要解除绑定吗？\n\n"
        f"解除后将无法使用积分、签到、兑换等功能，所有积分将会清零。\n"
        f"Telegram ID: {tg_id}\n"
        f"邮箱: {email}\n\n"
        f"回复 **确认** / 是 / yes / y / 1 继续解除\n"
        f"回复其他内容或输入 /cancel 取消操作",
        parse_mode='Markdown'
    )
    return UNBIND_CONFIRM

async def unbind_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    # 如果上下文不是 unbind 流程，直接退出（防止被 exchange 误抢）
    if 'unbind_email' not in context.user_data:
        return ConversationHandler.END

    # 取消逻辑（更宽松匹配）
    if text in ('取消', 'no', 'n', '否', '不', 'cancel', '退出') or text not in ('确认', '是', 'yes', 'y', '1'):
        await update.message.reply_text("已取消解除绑定操作")
        context.user_data.clear()
        return ConversationHandler.END

    tg_id = update.effective_user.id
    email = context.user_data.get('unbind_email')
    if not email:
        await update.message.reply_text("⚠️ 操作异常，请重新 /unbind")
        context.user_data.clear()
        return ConversationHandler.END

    try:
        with get_tg_db() as db:
            with db.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE tg_id = %s", (tg_id,))
            db.commit()

        await update.message.reply_text(
            f"🔓 **绑定已成功解除**！\n\n"
            f"Telegram ID: {tg_id}\n"
            f"邮箱: {email}\n\n"
            f"如需重新绑定，请使用 /bind 您的邮箱 命令。",
            parse_mode='Markdown'
        )
    except Error as e:
        print(f"unbind error: {e}")
        await update.message.reply_text("⚠️ 解除失败，请稍后重试或联系管理员")

    context.user_data.clear()
    return ConversationHandler.END

async def unbind_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("已取消解除绑定操作")
    context.user_data.clear()
    return ConversationHandler.END

async def user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    bound = is_bound(tg_id)
    if not bound:
        reply_msg = await update.message.reply_text("⚠️ 您还未绑定账号，请先 /bind 邮箱")
        await _schedule_group_cleanup(context, update, reply_msg)
        return
    client_id, email, points = bound
    chat_type = update.effective_chat.type
    if chat_type == "private":
        # 私聊：完整信息（不变）
        info = get_user_vps_info(client_id, tg_id, email, points=points)
        await update.message.reply_text(f"📋 账户信息\n\n{info}")
    else:
        # 群组：简化版 + 调度删除
        reply_msg = await update.message.reply_text(  # ← 这里必须先赋值给 reply_msg
            f"📋 您的积分信息\n\n"
            f"💎 当前积分: {points}\n"
            f"👤 Telegram ID: {tg_id}\n\n"
            "⚠️ 邮箱、VPS详情等隐私信息仅在私聊可见\n"
            "请私聊 @stormuser_bot 机器人使用 /user 查看完整信息"
        )
        # 现在 reply_msg 已定义，可以安全调用清理函数
        await _schedule_group_cleanup(context, update, reply_msg)



async def sign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    bound = is_bound(tg_id)
    if not bound:
        reply_msg = await update.message.reply_text("⚠️ 您还未绑定账号，请先 /bind 邮箱")
        await _schedule_group_cleanup(context, update, reply_msg)
        return
    _, email, _ = bound
    today = datetime.now().date()

    try:
        with get_tg_db() as db:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM sign_logs WHERE tg_id = %s AND DATE(sign_date) = %s",
                    (tg_id, today)
                )
                already_signed = cursor.fetchone() is not None

                if already_signed:
                    cursor.execute("SELECT points FROM users WHERE tg_id = %s", (tg_id,))
                    total_points = cursor.fetchone()[0]
                    chat_type = update.effective_chat.type
                    if chat_type == "private":
                        await update.message.reply_text(
                            f"📅 今日已签到，请明天再来~\n\n"
                            f"💎 当前总积分：{total_points}\n"
                            f"👤 Telegram ID: {tg_id}\n"
                            f"📧 邮箱: {email}"
                        )
                    else:
                        # 群聊重复签到：也需要回复 + 删除
                        reply_msg = await update.message.reply_text(
                            f"📅 今日已签到，请明天再来~\n\n"
                            f"💎 当前总积分：{total_points}\n"
                            f"👤 Telegram ID: {tg_id}"
                        )
                        # 下面统一调度删除（和成功分支一样）
                        await _schedule_group_cleanup(context, update, reply_msg)
                    return

                # 第一次签到逻辑
                points_added = random.randint(4, 10)
                cursor.execute(
                    "UPDATE users SET points = points + %s WHERE tg_id = %s",
                    (points_added, tg_id)
                )
                cursor.execute(
                    "INSERT INTO sign_logs (tg_id, points_added) VALUES (%s, %s)",
                    (tg_id, points_added)
                )
                db.commit()
                cursor.execute("SELECT points FROM users WHERE tg_id = %s", (tg_id,))
                total_points = cursor.fetchone()[0]

        # 获取每日语录
        try:
            resp = requests.get(
                "https://cn.apihz.cn/api/yiyan/api.php?id=10011784&key=311ec792c156839f82ef11edbfab4684",
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 200 and data.get("msg"):
                daily_quote = data["msg"]
            else:
                daily_quote = "保持好心情，明天又是元气满满的一天！"

        except Exception:
            daily_quote = "保持好心情哦~"


        chat_type = update.effective_chat.type
        if chat_type == "private":
            await update.message.reply_text(
                f"✅ 签到成功！+{points_added} 积分\n"
                f"💎 当前总积分：{total_points}\n\n"
                f"👤 ID: {tg_id}\n"
                f"📧 邮箱: {email}\n\n"
                f"💬 {daily_quote}"
            )
        else:
            # 群聊成功签到
            reply_msg = await update.message.reply_text(
                f"✅ 签到成功！+{points_added} 积分\n"
                f"💎 当前总积分：{total_points}\n\n"
                f"👤 ID: {tg_id}\n\n"
                f"💬 {daily_quote}"
            )
            # 统一调度删除
            await _schedule_group_cleanup(context, update, reply_msg)

    except Error as e:
        print(f"sign error: {e}")
        await update.message.reply_text("⚠️ 签到失败，请稍后重试")

async def exchange_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type != "private":
        bot_username = (await context.bot.get_me()).username
        reply_msg = await update.message.reply_text(
            f"⚠️ 兑换操作涉及积分扣除和隐私信息，仅限私聊使用。\n"
            f"请私聊机器人：@{bot_username}"
        )
        # await _schedule_group_cleanup(context, update, reply_msg)  # 你原有代码，保留
        return ConversationHandler.END

    tg_id = update.effective_user.id
    bound = is_bound(tg_id)
    if not bound:
        await update.message.reply_text("⚠️ 您还未绑定账号，请先 /bind 邮箱")
        return ConversationHandler.END

    _, email, points = bound

    try:
        with get_tg_db() as db:
            with db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT id, name, points_required, type, details
                    FROM exchange_options
                    WHERE is_active = 1
                    ORDER BY points_required ASC
                """)
                options = cursor.fetchall()

        if not options:
            await update.message.reply_text("📦 当前暂无可兑换选项")
            return ConversationHandler.END

        lines = []
        for i, opt in enumerate(options, 1):
            detail_str = ""
            try:
                parsed = json.loads(opt['details']) if isinstance(opt['details'], str) else opt['details']
            except:
                parsed = {}

            if opt['type'] == 'nat_renew':
                days = parsed.get('days', '?')
                detail_str = f"续期 {days} 天"
            elif opt['type'] == 'discount_code':
                amount = parsed.get('amount', 1)
                detail_str = f"{amount} 美元优惠"

            lines.append(f"{i}. ({opt['points_required']} 积分) {opt['name']} - {detail_str}")

        # 1. 提前计算 join 结果，将 \n 放在 f-string 外部
        joined_lines = '\n'.join(lines)

        # 2. 后续 f-string 直接引用临时变量，避免 {} 内出现 \
        text = (
            f"💎 当前积分：{points}\n\n"
            f"🎁 可兑换选项（回复序号选择）：\n"
            f"{joined_lines}\n\n"
            f"回复序号继续，或回复任意非数字内容 /cancel 取消操作"
        )
        
        await update.message.reply_text(text)
        context.user_data['exchange_options'] = options
        return SELECT_OPTION

    except Error as e:
        print(f"exchange_start error: {e}")
        await update.message.reply_text("⚠️ 查询失败，请稍后重试")
        return ConversationHandler.END

async def exchange_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # 如果不是数字（或 cancel），视为取消
    if not text.isdigit() or text in ('cancel', '取消', '退出', 'q', 'quit'):
        await update.message.reply_text("已取消兑换操作")
        context.user_data.clear()
        return ConversationHandler.END

    try:
        choice = int(text)
    except ValueError:
        await update.message.reply_text("🔢 请输入正确的序号（数字）")
        return SELECT_OPTION
    options = context.user_data.get('exchange_options', [])
    if not (1 <= choice <= len(options)):
        await update.message.reply_text(f"❌ 无效选项，请输入 1-{len(options)}")
        return SELECT_OPTION
    selected = options[choice - 1]
    context.user_data['selected_exchange'] = selected
    tg_id = update.effective_user.id
    bound = is_bound(tg_id)
    client_id, _, _ = bound
    if selected['type'] == 'nat_renew':
        try:
            with get_whmcs_db() as db:
                with db.cursor(dictionary=True) as cursor:
                    cursor.execute("""
                        SELECT
                            h.id AS hosting_id,
                            h.domain AS name,
                            h.dedicatedip,
                            p.name AS product_name,
                            vf.server_object
                        FROM tblhosting h
                        LEFT JOIN tblproducts p ON h.packageid = p.id
                        LEFT JOIN mod_virtfusion_direct vf ON vf.service_id = h.id
                        WHERE h.userid = %s
                          AND h.domainstatus = 'Active'
                    """, (client_id,))
                    nat_services = []
                    for row in cursor.fetchall():
                        if is_nat_service(row):
                            nat_services.append((row['hosting_id'], row['name']))
        except Exception as e:
            print(f"查询 NAT 服务 error: {e}")
            await update.message.reply_text("⚠️ 查询 NAT 服务失败，请稍后重试")
            context.user_data.clear()
            return ConversationHandler.END
        if len(nat_services) == 0:
            await update.message.reply_text("⚠️ 您还没有 Active NAT 服务哦。")
            context.user_data.clear()
            return ConversationHandler.END
        elif len(nat_services) == 1:
            context.user_data['selected_nat_id'] = nat_services[0][0]
            confirm_text = (
                f"您选择了：{selected['name']}\n"
                f"消耗积分：{selected['points_required']}\n"
                f"将续期服务 ID: {nat_services[0][0]} \n\n"
                f"确认兑换？回复：是 / y / yes / 1 \n"
                f"回复其他内容取消操作"
            )
            await update.message.reply_text(confirm_text)
            return CONFIRM
        else:
            service_list = "\n".join([f"- ID {sid} " for sid, name in nat_services])
            await update.message.reply_text(
                f"您有 {len(nat_services)} 台 NAT 服务，请输入要续期的服务 ID：\n\n{service_list}\n\n"
                f"回复数字 ID 继续，或 /cancel 取消"
            )
            context.user_data['nat_services'] = nat_services
            return SELECT_NAT_SERVICE
    else:
        confirm_text = (
            f"您选择了：{selected['name']}\n"
            f"消耗积分：{selected['points_required']}\n\n"
            f"确认兑换？回复：是 / y / yes / 1 \n"
            f"回复其他内容取消操作"
        )
        await update.message.reply_text(confirm_text)
        return CONFIRM

async def select_nat_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        service_id = int(text)
    except ValueError:
        await update.message.reply_text("请输入正确的服务 ID（数字）")
        return SELECT_NAT_SERVICE
    nat_services = context.user_data.get('nat_services', [])
    valid_ids = [sid for sid, _ in nat_services]
    if service_id not in valid_ids:
        await update.message.reply_text(f"无效的服务 ID，请从列表中选择：{valid_ids}")
        return SELECT_NAT_SERVICE
    context.user_data['selected_nat_id'] = service_id
    selected = context.user_data['selected_exchange']
    confirm_text = (
        f"您选择了：{selected['name']}\n"
        f"消耗积分：{selected['points_required']}\n"
        f"续期服务 ID: {service_id}\n\n"
        f"确认兑换？回复：是 / y / yes / 1 \n"
        f"回复其他内容取消操作"
    )
    await update.message.reply_text(confirm_text)
    return CONFIRM

async def exchange_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    # 如果上下文不是兑换流程，直接退出（防止被 unbind 误抢）
    if 'selected_exchange' not in context.user_data:
        return ConversationHandler.END

    if text not in ('是', 'y', 'yes', '确认', '1'):
        await update.message.reply_text("已取消兑换操作")
        context.user_data.clear()
        return ConversationHandler.END

    selected = context.user_data.get('selected_exchange')
    if not selected:
        await update.message.reply_text("兑换流程异常，请重新 /exchange")
        return ConversationHandler.END

    tg_id = update.effective_user.id
    bound = is_bound(tg_id)
    if not bound:
        await update.message.reply_text("绑定信息异常，请重新 /user 检查")
        return ConversationHandler.END
    client_id, email, current_points = bound
    points_deducted = selected['points_required']
    selected_nat_id = None
    if selected['type'] == 'nat_renew':
        selected_nat_id = context.user_data.get('selected_nat_id')
        if not selected_nat_id:
            await update.message.reply_text("续期流程异常：未选择服务 ID")
            context.user_data.clear()
            return ConversationHandler.END
    if current_points < points_deducted:
        await update.message.reply_text(
            f"积分不足！需要 {points_deducted}，您当前只有 {current_points} 分"
        )
        context.user_data.clear()
        return ConversationHandler.END
    try:
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute(
                    "UPDATE users SET points = points - %s WHERE tg_id = %s",
                    (points_deducted, tg_id)
                )
                details = selected.get('details', '{}')
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except json.JSONDecodeError:
                        details = {}
                if not isinstance(details, dict):
                    details = {}
                code = None
                whmcs_promo_id = None
                new_due_date_str = None
                cancelled_invoice_count = 0
                if selected['type'] == 'discount_code':
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
                    expires_at = datetime.now() + timedelta(days=30)
                    expires_date = expires_at.date().strftime('%Y-%m-%d')
                    start_date = datetime.now().date().strftime('%Y-%m-%d')
                    with get_whmcs_db() as db_whmcs:
                        with db_whmcs.cursor() as cursor_whmcs:
                            cursor_whmcs.execute("""
                                INSERT INTO tblpromotions (
                                    code, type, recurring, value, cycles, appliesto, requires,
                                    requiresexisting, startdate, expirationdate, maxuses, uses,
                                    lifetimepromo, applyonce, newsignups, existingclient, onceperclient,
                                    recurfor, upgrades, upgradeconfig, notes
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                code,
                                'Fixed Amount',
                                0,
                                1.00,
                                '',
                                '1,2,3,4,5,6,27,7,8,9,10,11,12,22,23,24,25,13,14,21,26,A1',
                                '',
                                0,
                                start_date,
                                expires_date,
                                1,
                                0,
                                0,
                                0,
                                0,
                                0,
                                1,
                                0,
                                0,
                                'a:4:{s:5:"value";s:4:"0.00";s:4:"type";s:13:"configoptions";s:12:"discounttype";s:10:"Percentage";s:13:"configoptions";s:0:"";}',
                                f"TG Bot 生成 - 用户 {tg_id} - 1美元优惠 - 有效期至 {expires_date}"
                            ))
                            db_whmcs.commit()
                            whmcs_promo_id = cursor_whmcs.lastrowid
                    cursor_tg.execute("""
                        INSERT INTO user_discount_codes
                        (tg_id, option_id, code, whmcs_promo_id, expires_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (tg_id, selected['id'], code, whmcs_promo_id, expires_at))
                if selected['type'] == 'nat_renew':
                    days = int(details.get('days', 30))
                    with get_whmcs_db() as db_whmcs:
                        with db_whmcs.cursor() as cursor_whmcs:
                            cursor_whmcs.execute(
                                "SELECT nextduedate FROM tblhosting WHERE id = %s AND userid = %s",
                                (selected_nat_id, client_id)
                            )
                            result = cursor_whmcs.fetchone()
                            if not result:
                                raise ValueError(f"服务 ID {selected_nat_id} 不存在或不属于此用户")
                            current_due = result[0]
                            try:
                                if current_due is None:
                                    raise ValueError("nextduedate 为 NULL")
                                if isinstance(current_due, datetime):
                                    current_due_date = current_due.date()
                                elif isinstance(current_due, date):
                                    current_due_date = current_due
                                elif isinstance(current_due, str):
                                    date_part = current_due.split()[0]
                                    current_due_date = datetime.strptime(date_part, '%Y-%m-%d').date()
                                else:
                                    raise ValueError(f"未知的 nextduedate 类型: {type(current_due).__name__}")
                            except Exception as parse_err:
                                raise ValueError(f"日期解析失败: {str(parse_err)} (原始值: {current_due!r})")
                            new_due_date = current_due_date + timedelta(days=days)
                            new_due_date_str = new_due_date.strftime('%Y-%m-%d')
                            cursor_whmcs.execute(
                                "UPDATE tblhosting SET nextduedate = %s WHERE id = %s",
                                (new_due_date_str, selected_nat_id)
                            )
                            if cursor_whmcs.rowcount != 1:
                                raise RuntimeError(f"更新 nextduedate 失败，影响行数: {cursor_whmcs.rowcount}")

                            cursor_whmcs.execute("""
                                SELECT DISTINCT ii.invoiceid
                                FROM tblinvoiceitems ii
                                INNER JOIN tblinvoices i ON i.id = ii.invoiceid
                                WHERE ii.type = 'Hosting'
                                  AND ii.relid = %s
                                  AND i.userid = %s
                                  AND i.status = 'Unpaid'
                            """, (selected_nat_id, client_id))
                            invoice_ids = [row[0] for row in cursor_whmcs.fetchall()]

                            if invoice_ids:
                                placeholders = ','.join(['%s'] * len(invoice_ids))
                                cursor_whmcs.execute(
                                    f"UPDATE tblinvoices SET status = 'Cancelled' WHERE id IN ({placeholders})",
                                    invoice_ids
                                )
                                cancelled_invoice_count = cursor_whmcs.rowcount
                            db_whmcs.commit()
                details_json = json.dumps(details, ensure_ascii=False)
                cursor_tg.execute("""
                    INSERT INTO exchange_logs
                    (tg_id, points_deducted, item_name, details)
                    VALUES (%s, %s, %s, %s)
                """, (tg_id, points_deducted, selected['name'], details_json))
            db_tg.commit()
            with db_tg.cursor() as cursor:
                cursor.execute("SELECT points FROM users WHERE tg_id = %s", (tg_id,))
                new_points = cursor.fetchone()[0]
        reply = (
            f"兑换成功！已扣除 {points_deducted} 积分\n"
            f"当前剩余积分：{new_points}\n"
            f"项目：{selected['name']}\n"
            f"Telegram ID: {tg_id}\n"
            f"邮箱: {email}\n"
        )
        if selected['type'] == 'discount_code':
            reply += f"\n您的专属折扣码: {code}\n"
            reply += "此码仅限您使用一次，有效期 30 天。\n"
            reply += "请在官网结账时输入使用！"
        elif selected['type'] == 'nat_renew':
            days = details.get('days', 30)
            reply += f"\n已为服务 ID {selected_nat_id} 续期 {days} 天"
            if new_due_date_str:
                reply += f"\n新到期日期：{new_due_date_str}"
            if cancelled_invoice_count > 0:
                reply += f"\n已自动取消相关未支付账单：{cancelled_invoice_count} 张"
            else:
                reply += "\n未发现需要取消的未支付账单"
        await update.message.reply_text(reply)
    except Exception as e:
        print(f"exchange_confirm error: {e}")
        await update.message.reply_text("兑换失败，请联系管理员（错误已记录）")
    context.user_data.clear()
    return ConversationHandler.END

async def exchange_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 已取消兑换")
    context.user_data.clear()
    return ConversationHandler.END

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    bound = is_bound(tg_id)
    if not bound:
        reply_msg = await update.message.reply_text("⚠️ 您还未绑定账号，请先 /bind 邮箱")
        await _schedule_group_cleanup(context, update, reply_msg)
        return

    _, email, _ = bound
    one_month_ago = datetime.now() - timedelta(days=30)

    # 映射（可按你喜好调整文案）
    prize_type_cn = {
        "points": "积分",
        "vps": "VPS",
        "nat": "NAT",
        "discount_code": "优惠码",
        "other": "其他",
    }

    try:
        with get_tg_db() as db:
            with db.cursor() as cursor:
                # 1) 签到记录
                cursor.execute("""
                    SELECT sign_date, points_added
                    FROM sign_logs
                    WHERE tg_id = %s AND sign_date > %s
                    ORDER BY sign_date DESC
                """, (tg_id, one_month_ago))
                signs = [f"{d.strftime('%Y-%m-%d %H:%M')}: +{p}" for d, p in cursor.fetchall()]

                # 2) 兑换记录（私聊展示）
                cursor.execute("""
                    SELECT exchange_date, points_deducted, item_name
                    FROM exchange_logs
                    WHERE tg_id = %s AND exchange_date > %s
                    ORDER BY exchange_date DESC
                """, (tg_id, one_month_ago))
                exs = [f"{d.strftime('%Y-%m-%d %H:%M')}: -{p} ({name})" for d, p, name in cursor.fetchall()]

                # 3) 中奖记录（私聊展示）
                cursor.execute("""
                    SELECT
                        created_at,
                        prize_type,
                        prize_name,
                        quantity,
                        points_amount,
                        status,
                        raffle_title,
                        raffle_code,
                        win_rank,
                        participant_no
                    FROM prize_wins
                    WHERE tg_id = %s AND created_at > %s
                    ORDER BY created_at DESC
                """, (tg_id, one_month_ago))

                prizes = []
                for (created_at, ptype, pname, qty, ppoints, pstatus,
                     rtitle, rcode, rank, pno) in cursor.fetchall():

                    ts = created_at.strftime('%Y-%m-%d %H:%M')
                    type_show = prize_type_cn.get(ptype, str(ptype))

                    extra_parts = []
                    if rank is not None:
                        extra_parts.append(f"第{rank}名")
                    if pno:
                        extra_parts.append(f"编号{pno}")
                    if rtitle:
                        extra_parts.append(f"抽奖：{rtitle}")
                    elif rcode:
                        extra_parts.append(f"抽奖：{rcode}")

                    # points 类型：优先展示 points_amount
                    if ptype == "points" and ppoints is not None:
                        main = f"{ppoints} 积分"
                    else:
                        main = pname
                        if qty and int(qty) != 1:
                            main += f" x{qty}"

                    extra = f"（{'，'.join(extra_parts)}）" if extra_parts else ""
                    prizes.append(f"{ts}: 🎉 中奖[{type_show}] {main}{extra}")

        newline = '\n'
        chat_type = update.effective_chat.type

        if chat_type == "private":
            text = (
                f"📜 近 30 天记录\n\n"
                f"👤 ID: {tg_id}\n"
                f"📧 邮箱: {email}\n"
                "----------------------------------------\n"
                f"📅 签到记录:\n{newline.join(signs) if signs else '无'}\n\n"
                f"🎁 兑换记录:\n{newline.join(exs) if exs else '无'}\n\n"
                f"🏆 中奖记录:\n{newline.join(prizes) if prizes else '无'}"
            )
        else:
            text = (
                f"📜 近 30 天签到记录\n\n"
                f"👤 ID: {tg_id}\n"
                "----------------------------------------\n"
                f"📅 签到记录:\n{newline.join(signs) if signs else '无'}\n\n"
                "⚠️ 兑换/中奖等详细信息仅在私聊 @stormuser_bot 可见"
            )

        reply_msg = await update.message.reply_text(text)

        # 你原来是无论私聊/群聊都删；如果你只想群聊删，把下面两行包一层 if chat_type != "private":
        await _schedule_group_cleanup(context, update, reply_msg)

    except Error as e:
        print(f"logs error: {e}")
        await update.message.reply_text("⚠️ 查询失败，请稍后重试")




async def changemail_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    tg_id = update.effective_user.id
    args = context.args

    if chat_type != "private":
        reply_msg = await update.message.reply_text(
            "⚠️ 换绑邮箱涉及隐私信息，仅限私聊使用。\n请私聊 @stormuser_bot 操作。"
        )
        await _schedule_group_cleanup(context, update, reply_msg)
        return ConversationHandler.END

    bound = is_bound(tg_id)
    if not bound:
        await update.message.reply_text("⚠️ 您还未绑定账号，请先使用 /bind 邮箱 进行绑定。")
        return ConversationHandler.END

    old_client_id, old_email, points = bound

    if not args:
        await update.message.reply_text("⌨️ 用法：/changemail 新邮箱\n例如：/changemail abc@example.com")
        return ConversationHandler.END

    new_email = args[0].strip().lower()
    if not EMAIL_REGEX.match(new_email):
        await update.message.reply_text("❌ 邮箱格式不正确，请重新输入：/changemail 新邮箱")
        return ConversationHandler.END

    if new_email == old_email.lower():
        await update.message.reply_text("ℹ️ 新邮箱与当前邮箱相同，无需换绑。")
        return ConversationHandler.END

    # TG库：新邮箱是否已经被别人绑定
    try:
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute("SELECT tg_id FROM users WHERE email = %s", (new_email,))
                row = cursor_tg.fetchone()
                if row and row[0] != tg_id:
                    await update.message.reply_text("⚠️ 该邮箱已被其他 Telegram 账号绑定，无法换绑。")
                    return ConversationHandler.END
    except Exception as e:
        print(f"changemail_start tgdb error: {e}")
        await update.message.reply_text("⚠️ 系统繁忙，请稍后再试。")
        return ConversationHandler.END

    # WHMCS：新邮箱必须存在客户账号
    try:
        with get_whmcs_db() as db_whmcs:
            with db_whmcs.cursor() as cursor_whmcs:
                cursor_whmcs.execute("SELECT id FROM tblclients WHERE email = %s", (new_email,))
                row = cursor_whmcs.fetchone()
                new_client_id = row[0] if row else None

        if not new_client_id:
            await update.message.reply_text(
                "🔍 该邮箱未在官网找到账号，请先在官网注册/确认邮箱正确后再换绑：\n"
                "https://billing.stormhost.net/"
            )
            return ConversationHandler.END

    except Exception as e:
        print(f"changemail_start whmcs error: {e}")
        await update.message.reply_text("⚠️ 查询失败，请稍后重试。")
        return ConversationHandler.END

    # 进入确认阶段
    context.user_data["changemail_old_email"] = old_email
    context.user_data["changemail_new_email"] = new_email
    context.user_data["changemail_new_client_id"] = new_client_id

    await update.message.reply_text(
        "⚠️ 请确认换绑邮箱：\n\n"
        f"当前邮箱：{old_email}\n"
        f"新邮箱：{new_email}\n\n"
        "确认继续？回复：是 / y / yes / 1\n"
        "取消请输入：取消 / no / n / /cancel"
    )
    return CHANGE_EMAIL_CONFIRM


async def changemail_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().lower()

    # 防止被其它会话误抢
    if "changemail_new_email" not in context.user_data:
        return ConversationHandler.END

    cancel_words = {"取消", "no", "n", "否", "不", "cancel", "退出", "/cancel", "q", "quit"}
    ok_words = {"是", "y", "yes", "确认", "1"}

    if text in cancel_words or text not in ok_words:
        await update.message.reply_text("已取消换绑操作。")
        context.user_data.pop("changemail_old_email", None)
        context.user_data.pop("changemail_new_email", None)
        context.user_data.pop("changemail_new_client_id", None)
        return ConversationHandler.END

    tg_id = update.effective_user.id
    new_email = context.user_data["changemail_new_email"]

    # 生成验证码并入库（10分钟）
    code = "".join(random.choices("0123456789", k=6))
    expires = datetime.now() + timedelta(minutes=10)

    try:
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute("DELETE FROM change_email_codes WHERE tg_id = %s", (tg_id,))
                cursor_tg.execute(
                    "INSERT INTO change_email_codes (tg_id, new_email, code, expires_at) VALUES (%s, %s, %s, %s)",
                    (tg_id, new_email, code, expires)
                )
            db_tg.commit()

        send_verification_email(new_email, code)

        await update.message.reply_text(
            f"📩 验证码已发送到新邮箱：{new_email}（10 分钟有效）\n"
            "请使用：/changemailverify 验证码  完成换绑\n"
            "示例：/changemailverify 123456"
        )
        return CHANGE_EMAIL_WAIT_CODE

    except Exception as e:
        print(f"changemail_confirm error: {e}")
        await update.message.reply_text("⚠️ 发送验证码失败，请稍后重试。")
        context.user_data.clear()
        return ConversationHandler.END


async def changemail_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type != "private":
        reply_msg = await update.message.reply_text(
            "⚠️ 该功能涉及隐私信息，仅限私聊使用。\n请私聊 @stormuser_bot 操作。"
        )
        await _schedule_group_cleanup(context, update, reply_msg)
        return ConversationHandler.END

    tg_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text("⌨️ 用法：/changemailverify 验证码\n例如：/changemailverify 123456")
        return CHANGE_EMAIL_WAIT_CODE

    code = args[0].strip()
    if not code.isdigit() or len(code) not in (4, 5, 6, 7, 8):
        await update.message.reply_text("❌ 验证码格式不正确，请重新输入：/changemailverify 123456")
        return CHANGE_EMAIL_WAIT_CODE

    bound = is_bound(tg_id)
    if not bound:
        await update.message.reply_text("⚠️ 您还未绑定账号，无法换绑。请先 /bind 邮箱。")
        context.user_data.clear()
        return ConversationHandler.END

    old_client_id, old_email, points = bound

    try:
        # 校验验证码
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute(
                    "SELECT new_email FROM change_email_codes WHERE tg_id=%s AND code=%s AND expires_at > NOW()",
                    (tg_id, code)
                )
                row = cursor_tg.fetchone()
                if not row:
                    await update.message.reply_text("❌ 验证码错误或已过期，请重新 /changemail 新邮箱 获取验证码。")
                    return CHANGE_EMAIL_WAIT_CODE

                new_email = row[0]

        # WHMCS 查新邮箱对应 client_id
        with get_whmcs_db() as db_whmcs:
            with db_whmcs.cursor() as cursor_whmcs:
                cursor_whmcs.execute("SELECT id FROM tblclients WHERE email=%s", (new_email,))
                c_row = cursor_whmcs.fetchone()
                new_client_id = c_row[0] if c_row else None

        if not new_client_id:
            await update.message.reply_text("⚠️ 新邮箱在官网未找到账号，请确认邮箱是否正确。")
            return ConversationHandler.END

        # 防止新邮箱已被别人绑定（再次校验，避免竞态）
        with get_tg_db() as db_tg:
            with db_tg.cursor() as cursor_tg:
                cursor_tg.execute("SELECT tg_id FROM users WHERE email=%s", (new_email,))
                u_row = cursor_tg.fetchone()
                if u_row and u_row[0] != tg_id:
                    await update.message.reply_text("⚠️ 该邮箱已被其他账号绑定，无法换绑。")
                    return ConversationHandler.END

                # 更新绑定（保留积分）
                cursor_tg.execute(
                    "UPDATE users SET email=%s, whmcs_client_id=%s WHERE tg_id=%s",
                    (new_email, new_client_id, tg_id)
                )
                cursor_tg.execute("DELETE FROM change_email_codes WHERE tg_id=%s", (tg_id,))
            db_tg.commit()

        await update.message.reply_text(
            "✅ 换绑成功！\n\n"
            f"Telegram ID: {tg_id}\n"
            f"旧邮箱：{old_email}\n"
            f"新邮箱：{new_email}\n"
            f"💎 积分已保留：{points}\n\n"
            "可使用 /user 查看最新信息。"
        )

    except Exception as e:
        print(f"changemail_verify error: {e}")
        await update.message.reply_text("⚠️ 换绑失败，请稍后重试或联系管理员。")

    context.user_data.clear()
    return ConversationHandler.END


async def changemail_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("已取消换绑操作。")
    context.user_data.pop("changemail_old_email", None)
    context.user_data.pop("changemail_new_email", None)
    context.user_data.pop("changemail_new_client_id", None)
    return ConversationHandler.END




async def unbound_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ 您还未绑定账号，请先使用 /bind 邮箱 进行绑定")

async def clean_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # 直接判断是否为群组（group 或 supergroup）
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("此命令仅在群组中使用")
        return

    # 可选：限制只有群管理员能用
    admins = await chat.get_administrators()
    if user.id not in [admin.user.id for admin in admins]:
        await update.message.reply_text("只有群管理员可以使用此命令")
        return

    try:
        await context.bot.set_my_commands(
            commands=[
                BotCommand("sign", "群内签到领积分"),
                BotCommand("user", "查看用户积分信息"),
                BotCommand("logs", "查看我的近30天记录"),
            ],
            scope=BotCommandScopeChat(chat_id=chat.id),
            language_code="zh"
        )

        await update.message.reply_text(
            "✅ 已成功重置本群的命令菜单。\n\n"
        )

    except Exception as e:
        print(f"clean_commands error: {e}")
        await update.message.reply_text(f"操作失败：{str(e)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("请私聊 @stormuser_bot 使用 /start")
        return

    # 获取每日语录
    try:
        resp = requests.get(
            "https://cn.apihz.cn/api/yiyan/api.php?id=10011784&key=311ec792c156839f82ef11edbfab4684",
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") == 200 and data.get("msg"):
            daily_quote = data["msg"]
        else:
            daily_quote = "保持好心情，明天又是元气满满的一天！"

    except Exception:
        daily_quote = "保持好心情哦~"


    # 欢迎文本 + 语录
    welcome_text = (
        f"💬{daily_quote}\n\n"
    )

    # 内联键盘
    keyboard = [
        [
            InlineKeyboardButton("🌐 官网", url="https://stormhost.net/"),
            InlineKeyboardButton("👥 群组", url="https://t.me/stormhost_group"),
            InlineKeyboardButton("🔔 通知", url="https://t.me/stormhost_notice"),
        ],
        [
            InlineKeyboardButton("👑 老板", url="https://t.me/pzyta_network"),
            InlineKeyboardButton("🛎️ 客服", url="https://t.me/stormhosthy_bot"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)


    # 可选：再发一条带底部菜单的提示
    await update.message.reply_text(
        welcome_text,
        reply_markup=MAIN_MENU_KEYBOARD
    )
    await update.message.reply_text(
        f"""✨ 欢迎使用 StormHost！ ✨
稳定 · 高速 · 高性价比的海外云服务商
🤖 官方 TG 机器人：@stormuser_bot

🚀 核心产品
US VPS · 美国西雅图（CU4837）
https://stormhost.net/store/vps-us-sea
斯巴达同款 CU4837 线路 · 中国大陆优化
自带 20Gbps DDoS 防御
👉 适合建站 / 节点 / 跑脚本 / 游戏服务器
📡 Looking Glass：
SEA-LG：http://193.218.200.131:8800/

US VPS · 美国洛杉矶（CU4837）
https://stormhost.net/store/vps-us-lax
洛杉矶 CU4837 优化线路 · 面向中国大陆
自带 5Gbps DDoS 防御
👉 高速稳定，回国延迟低
📡 Looking Glass：
LAX-LG：http://204.194.52.5:8800/


🎁 福利 & 优惠
🎟 长期 9 折优惠码：STHKVM10
👉 适用于 SEA / LAX 任意产品

每日签到积分系统
每日签到可获得 4–10 积分
积分可用于 NAT 续期 / 优惠码兑换

📌 NAT 续期补贴说明
若下个月前 7 天签到后积分仍 未满 100，
可联系 老板 / 客服的传话筒 / 提交工单，
👉 可补至 100 积分（差额 ≤ 30 积分），用于 NAT 续期。

⚡ 快速上手（TG 机器人 @stormuser_bot）
→ /bind 绑定官网账号
→ /sign 每日签到领积分
→ /user 查看 VPS 与积分
→ /exchange 积分兑换福利

🌐 官网：https://stormhost.net/
💬 交流群：https://t.me/stormhost_group""",
        reply_markup=reply_markup,
    )



async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    text = update.message.text.strip()

    # 如果在兑换或解绑会话中，跳过处理，让 ConversationHandler 接管
    if (
        context.user_data.get('selected_exchange')
        or context.user_data.get('unbind_email')
        or context.user_data.get('changemail_new_email')
    ):
        print("[DEBUG] 在 Conversation 中，跳过 handle_menu_text")
        return

    if text in ("📅签到", "签到", "sign", "qiandao"):  # 宽松匹配
        await sign(update, context)
    elif text in ("👤个人", "user"):
        await user(update, context)
    elif text in ("📝日志", "logs"):
        await logs(update, context)
    else:
        await update.message.reply_text(
            "请选择下面的菜单按钮哦～",
            reply_markup=MAIN_MENU_KEYBOARD
        )


async def handle_group_sign_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return

    text = (update.message.text or "").strip()
    if text != "签到":
        return

    await sign(update, context)


messages_to_delete = {}  # 如果不用了可以删掉

async def schedule_delete(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list[int]):
    await asyncio.sleep(300)  # 生产改回 300

    bot = context.bot
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            err = str(e).lower()
            if "not found" in err:
                pass
            elif "rights" in err or "permission" in err or "forbidden" in err:
                print(f"[PERMISSION-ERROR] 无删除权限！chat={chat_id} msg={msg_id} → {e}")
                print("   → 请确认 bot 是管理员且有「删除消息」权限")
            else:
                print(f"[DELETE-ERROR] {msg_id} 失败: {e}")

async def _schedule_group_cleanup(context: ContextTypes.DEFAULT_TYPE, update: Update, reply_msg):
    chat_id = update.effective_chat.id
    user_msg_id = context.chat_data.pop('pending_delete_user_msg_id', update.message.message_id)
    bot_msg_id = reply_msg.message_id
    to_delete = [user_msg_id, bot_msg_id]

    async def delayed_delete():
        await asyncio.sleep(300)  # 生产用 300s

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=user_msg_id)
        except Exception as e:
            if "forbidden" in str(e).lower() or "rights" in str(e).lower():
                print(f"[PERMISSION-ERROR] 用户命令删除失败: {e}")

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=bot_msg_id)
        except Exception as e:
            if "forbidden" in str(e).lower() or "rights" in str(e).lower():
                print(f"[PERMISSION-ERROR] bot 回复删除失败: {e}")

    context.application.create_task(delayed_delete())

async def sensitive_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return

    message = update.message
    if not message or not message.text or not message.text.strip().startswith('/'):
        return

    command_text = message.text.split(maxsplit=1)[0].lower()
    sensitive_cmds = ['/sign', '/user', '/logs', '/exchange', '/bind', '/verify', '/unbind', '/changemail', '/changemailverify']

    if not any(command_text.startswith(cmd) for cmd in sensitive_cmds):
        return

    context.chat_data['pending_delete_user_msg_id'] = message.message_id



def main():
    app = Application.builder().token(TG_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.COMMAND & filters.Regex(r'^/(sign|user|logs|exchange|bind|verify|unbind|changemail|changemailverify)'),
            sensitive_command_handler
        ),
        group=-100   # 比默认的 CommandHandler 更早执行
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('bind', bind))
    app.add_handler(CommandHandler('verify', verify))
    app.add_handler(CommandHandler('user', user))
    app.add_handler(CommandHandler('sign', sign))
    app.add_handler(CommandHandler('logs', logs))
    app.add_handler(CommandHandler('clean', clean_commands))

    # 先注册 unbind（优先级更高）
    unbind_handler = ConversationHandler(
        entry_points=[CommandHandler('unbind', unbind_start)],
        states={
            UNBIND_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, unbind_confirm),
                CommandHandler('cancel', unbind_cancel),
            ],
        },
        fallbacks=[CommandHandler('cancel', unbind_cancel)],
        allow_reentry=True,
        name="unbind_conversation",   # 加 name 方便调试
        persistent=False,
    )
    app.add_handler(unbind_handler)


    # changemail 会话（建议放在 unbind/exchange 之前或之后都行，但要注意 handle_menu_text 的跳过逻辑）
    changemail_handler = ConversationHandler(
        entry_points=[CommandHandler("changemail", changemail_start)],
        states={
            CHANGE_EMAIL_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, changemail_confirm),
                CommandHandler("cancel", changemail_cancel),
            ],
            CHANGE_EMAIL_WAIT_CODE: [
                CommandHandler("changemailverify", changemail_verify),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text("⌨️ 请使用：/changemailverify 验证码")),
                CommandHandler("cancel", changemail_cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", changemail_cancel)],
        allow_reentry=True,
        name="changemail_conversation",
        persistent=False,
    )
    app.add_handler(changemail_handler)

    # 同时也允许直接走命令（不在会话里也能验证）
    app.add_handler(CommandHandler("changemailverify", changemail_verify))



    # 再注册 exchange
    exchange_handler = ConversationHandler(
        entry_points=[CommandHandler('exchange', exchange_start)],
        states={
            SELECT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, exchange_select)],
            SELECT_NAT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_nat_service)],
            CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, exchange_confirm),
                CommandHandler('cancel', exchange_cancel),
            ],
        },
        fallbacks=[CommandHandler('cancel', exchange_cancel)],
        allow_reentry=True,
        name="exchange_conversation",  # 加 name
        persistent=False,
    )
    app.add_handler(exchange_handler)

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_menu_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        handle_group_sign_text
    ))

    unbound_cmds = ['user', 'sign', 'exchange', 'logs', 'unbind']
    for cmd in unbound_cmds:
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(f'^/{cmd}$'), unbound_handler))

    scheduler = BackgroundScheduler()
    scheduler.add_job(clean_expired_discount_codes, 'cron', hour=3)
    scheduler.start()

    print("Bot 已启动...")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == '__main__':
    main()
