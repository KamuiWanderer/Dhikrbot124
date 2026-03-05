import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import telethon
from datetime import date
from telethon import events
from config import SUBMISSION_COOLDOWN_SECONDS, ABSOLUTE_MILESTONES, MILESTONE_PERCENTAGES, OWNER_ID
from db import queries as q
from keyboards.builder import (
    kb_member_menu, kb_task_list, kb_task_view,
    kb_settings, kb_visibility, kb_notifications, kb_reminder_time,
    kb_stats_view, kb_contrib_confirm,
    btn, row, markup
)
from utils.messages import (
    msg_task_view, msg_stats_card, msg_leaderboard,
    msg_category_stats, msg_contribution_warning,
    MSG_VISIBILITY, MSG_NOTIFICATIONS, MSG_REMINDER_TIME, fmt_num, h
)
from utils.announcements import announce_milestone, announce_task_ended

_cooldowns: dict = {}


def register(client):

    # ── /stats command ───────────────────────────────────────
    @client.on(events.NewMessage(pattern="/stats"))
    async def cmd_stats(event):
        uid = event.sender_id
        user = await q.get_user(uid)
        if not user:
            await event.respond("Please register first with /start", parse_mode="html")
            return
        text = await _build_stats(uid, user)
        # If in group, send to DM and notify
        if not event.is_private:
            await _send_stats_dm(client, uid, text)
            await event.respond("📊 Stats sent to your DM.", parse_mode="html")
        else:
            # Already in DM — just show inline, no redirect loop
            await event.respond(text, parse_mode="html")

    # ── Menu callbacks ───────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"menu:.*"))
    async def menu_callback(event):
        uid = event.sender_id
        data = event.data.decode()
        user = await q.get_user(uid)
        if not user:
            await event.answer("Please register first with /start", alert=True)
            return
        is_admin_user = uid == OWNER_ID or await q.is_admin(uid)
        await event.answer()

        if data == "menu:main":
            try:
                await event.edit("What would you like to do?",
                                 parse_mode="html",
                                 buttons=kb_member_menu(is_admin=is_admin_user))
            except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                pass

        elif data == "menu:tasks":
            active = await q.get_active_tasks()
            if not active:
                try:
                    await event.edit("📿 No active tasks right now. Check back later! 🌙",
                                     parse_mode="html",
                                     buttons=kb_member_menu(is_admin=is_admin_user))
                except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                    pass
            else:
                await event.edit("📿 <b>Active Tasks</b> — tap one to contribute:",
                                 parse_mode="html", buttons=kb_task_list(active))

        elif data == "menu:stats":
            text = await _build_stats_v2(uid, scope="user", period="all")
            await event.edit(
                text,
                parse_mode="html",
                buttons=kb_stats_view(scope="user", period="all")
            )

        elif data.startswith("stats:scope:"):
            scope = data.split(":")[2]
            text = await _build_stats_v2(uid, scope=scope, period="all")
            await event.edit(
                text,
                parse_mode="html",
                buttons=kb_stats_view(scope=scope, period="all")
            )

        elif data.startswith("stats:period:"):
            parts = data.split(":")
            period = parts[2]
            scope = parts[3]
            text = await _build_stats_v2(uid, scope=scope, period=period)
            await event.edit(
                text,
                parse_mode="html",
                buttons=kb_stats_view(scope=scope, period=period)
            )

        elif data == "menu:settings":
            await event.edit("⚙️ <b>Settings</b>", parse_mode="html",
                             buttons=kb_settings(user))

    # ── Task callbacks ───────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"task:.*"))
    async def task_callback(event):
        uid = event.sender_id
        data = event.data.decode()
        parts = data.split(":")
        action  = parts[1]
        task_id = parts[2] if len(parts) > 2 else None
        user = await q.get_user(uid)
        if not user:
            await event.answer("Please register first.", alert=True)
            return
        await event.answer()

        if action == "view" and task_id:
            task = await q.get_task(task_id)
            if not task or task["status"] not in ("active","paused"):
                is_admin_user = uid == OWNER_ID or await q.is_admin(uid)
                await event.edit("❌ This task is no longer available.",
                                 parse_mode="html",
                                 buttons=kb_member_menu(is_admin=is_admin_user))
                return
            user_total = await q.get_user_task_total(task_id, uid)
            user_daily = await q.get_user_daily_total(task_id, uid)
            
            remaining = None
            if task.get("target"):
                remaining = max(0, task["target"] - task["total_count"])

            # Show intention reminder once before first contribution
            if user_total == 0 and task.get("intention_reminder"):
                await event.edit(
                    f"🤲 <b>Before you begin:</b>\n\n<blockquote>{h(task['intention_reminder'])}</blockquote>",
                    parse_mode="html")
                await client.send_message(
                    uid,
                    msg_task_view(task, user_total, user_daily),
                    parse_mode="html",
                    buttons=kb_task_view(task, user_total, remaining=remaining)
                )
                return
            await event.edit(msg_task_view(task, user_total, user_daily),
                             parse_mode="html",
                             buttons=kb_task_view(task, user_total, remaining=remaining))

        elif action == "lb" and task_id:
            task = await q.get_task(task_id)
            if not task or not task.get("leaderboard_visible", True):
                await event.answer("Leaderboard is disabled for this task.", alert=True)
                return
            lb_rows = await q.get_task_leaderboard(task_id)
            users_map = {}
            for r in lb_rows:
                u = await q.get_user(r["_id"])
                if u:
                    users_map[r["_id"]] = u
            viewer_rank  = await q.get_user_rank(task_id, uid)
            viewer_total = await q.get_user_task_total(task_id, uid)
            text = msg_leaderboard(task, lb_rows, users_map, uid, viewer_rank, viewer_total)
            await event.edit(text, parse_mode="html",
                             buttons=markup(row(btn("⬅️ Back", f"task:view:{task_id}", "primary"))))

        elif action == "media" and task_id:
            task = await q.get_task(task_id)
            if not task or not task.get("media"):
                await event.answer("No media attached.", alert=True)
                return
            for m in task["media"]:
                if m["type"] in ("image","video","audio"):
                    await client.send_file(uid, m["file_id"])
                elif m["type"] == "youtube":
                    await client.send_message(uid,
                        f"▶️ <a href=\"{m.get('url')}\">{m.get('title','YouTube Video')}</a>",
                        parse_mode="html")

    # ── Contributions ─────────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"contrib:.*"))
    async def contrib_callback(event):
        uid = event.sender_id
        data = event.data.decode()
        parts = data.split(":")
        task_id    = parts[1]
        amount_str = parts[2]
        user = await q.get_user(uid)
        if not user:
            await event.answer("Please register first.", alert=True)
            return
        if user.get("is_banned"):
            await event.answer("You are not allowed to use this bot.", alert=True)
            return
        task = await q.get_task(task_id)
        if not task or task["status"] != "active":
            await event.answer("This task is no longer active.", alert=True)
            return

        if amount_str == "custom":
            await q.set_state(uid, "contrib:custom", data={"task_id": task_id})
            await event.answer()
            await event.respond(
                f"✍️ How many <b>{task['dhikr_text']}</b> would you like to submit?",
                parse_mode="html")
            return

        if amount_str == "conf":
            # Handle confirmation
            task_id = parts[2]
            amount = int(parts[3])
            task = await q.get_task(task_id)
            await _process_contribution(event, uid, task, task_id, amount, client)
            return

        amount = int(amount_str)
        
        # Check for big values confirmation
        if amount >= 500:
            await event.edit(msg_contribution_warning(amount),
                             parse_mode="html",
                             buttons=kb_contrib_confirm(task_id, amount))
            return

        now = time.time()
        user_cd = _cooldowns.setdefault(uid, {})
        last = user_cd.get(task_id, 0)
        if now - last < SUBMISSION_COOLDOWN_SECONDS:
            remaining = int(SUBMISSION_COOLDOWN_SECONDS - (now - last)) + 1
            await event.answer(f"⏳ Please wait {remaining}s.", alert=False)
            return
        user_cd[task_id] = now
        await event.answer()
        await _process_contribution(event, uid, task, task_id, amount, client)

    # ── Text input handler (contrib custom + settings) ───────
    @client.on(events.NewMessage())
    async def member_text_input(event):
        if not event.is_private:
            return
        uid = event.sender_id
        state_doc = await q.get_state(uid)
        if not state_doc:
            return
        state  = state_doc["state"]
        wizard = state_doc["data"]

        if state == "contrib:custom":
            task_id = wizard.get("task_id")
            text = event.raw_text.strip()
            if not text.isdigit() or int(text) <= 0:
                await event.respond("❌ Please enter a positive number.", parse_mode="html")
                return
            task = await q.get_task(task_id)
            if not task or task["status"] != "active":
                await event.respond("❌ That task is no longer active.", parse_mode="html")
                await q.clear_state(uid)
                return
            
            amount = int(text)
            # Check for big values confirmation
            if amount >= 500:
                await event.respond(msg_contribution_warning(amount),
                                 parse_mode="html",
                                 buttons=kb_contrib_confirm(task_id, amount))
                return

            await q.clear_state(uid)
            await _process_contribution(event, uid, task, task_id, amount, client)

        elif state == "settings:custom_time":
            import re
            text = event.raw_text.strip()
            if re.match(r"^\d{2}:\d{2}$", text):
                await q.update_user(uid, reminder_time=text)
                await q.clear_state(uid)
                user = await q.get_user(uid)
                await event.respond(
                    f"✅ Reminder time set to <b>{text}</b>",
                    parse_mode="html",
                    buttons=kb_settings(user)
                )
            else:
                await event.respond(
                    "❌ Invalid format. Use <b>HH:MM</b> e.g. <code>21:30</code>",
                    parse_mode="html")

    # ── Settings callbacks ────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"settings:.*"))
    async def settings_callback(event):
        uid = event.sender_id
        data = event.data.decode()
        user = await q.get_user(uid)
        if not user:
            await event.answer("Please register first.", alert=True)
            return
        state_doc = await q.get_state(uid)
        state  = (state_doc["state"] if state_doc else "") or ""
        wizard = (state_doc["data"]  if state_doc else {}) or {}
        await event.answer()

        if data == "settings:visibility":
            await q.set_state(uid, "settings:visibility")
            await event.edit(MSG_VISIBILITY, parse_mode="html", buttons=kb_visibility())

        elif data == "settings:notifications":
            selected = set()
            if user.get("notify_tasks"):       selected.add("tasks")
            if user.get("notify_endings"):     selected.add("endings")
            if user.get("notify_leaderboard"): selected.add("leaderboard")
            if user.get("notify_reminders"):   selected.add("reminders")
            await q.set_state(uid, "settings:notifications",
                              data={"notifications_selected": list(selected)})
            await event.edit(MSG_NOTIFICATIONS, parse_mode="html",
                             buttons=kb_notifications(selected))

        elif data == "settings:reminder":
            await q.set_state(uid, "settings:reminder")
            await event.edit(MSG_REMINDER_TIME, parse_mode="html",
                             buttons=kb_reminder_time())

    # ── Settings: reuse reg:vis and reg:notif callbacks in settings context
    @client.on(events.CallbackQuery(pattern=b"reg:vis:.*"))
    async def settings_vis_callback(event):
        uid = event.sender_id
        state_doc = await q.get_state(uid)
        if not state_doc or state_doc["state"] != "settings:visibility":
            return   # let registration handler handle it
        await event.answer()
        vis = event.data.decode().split(":")[2]
        await q.update_user(uid, visibility=vis)
        await q.clear_state(uid)
        user = await q.get_user(uid)
        await event.edit("✅ <b>Visibility updated!</b>", parse_mode="html",
                         buttons=kb_settings(user))

    @client.on(events.CallbackQuery(pattern=b"reg:notif:.*"))
    async def settings_notif_callback(event):
        uid = event.sender_id
        state_doc = await q.get_state(uid)
        if not state_doc or state_doc["state"] != "settings:notifications":
            return   # let registration handler handle it
        data = event.data.decode()
        wizard = state_doc["data"]
        await event.answer()

        if data == "reg:notif:confirm":
            selected = set(wizard.get("notifications_selected", []))
            await q.update_user(uid,
                notify_tasks      ="tasks"       in selected,
                notify_endings    ="endings"     in selected,
                notify_leaderboard="leaderboard" in selected,
                notify_reminders  ="reminders"   in selected,
            )
            await q.clear_state(uid)
            user = await q.get_user(uid)
            await event.edit("✅ <b>Notifications updated!</b>", parse_mode="html",
                             buttons=kb_settings(user))
        else:
            key = data.split(":")[2]
            selected = set(wizard.get("notifications_selected", []))
            selected.discard(key) if key in selected else selected.add(key)
            await q.update_state_data(uid, notifications_selected=list(selected))
            await event.edit(MSG_NOTIFICATIONS, parse_mode="html",
                             buttons=kb_notifications(selected))

    @client.on(events.CallbackQuery(pattern=b"reg:time:.*"))
    async def settings_time_callback(event):
        uid = event.sender_id
        state_doc = await q.get_state(uid)
        if not state_doc or state_doc["state"] != "settings:reminder":
            return  # registration handler handles reg:reminder_time state
        data = event.data.decode()
        t = data.split(":", 2)[2]
        await event.answer()
        if t == "custom":
            await q.set_state(uid, "settings:custom_time")
            await event.edit("✍️ Enter your reminder time in <b>HH:MM</b> format:",
                             parse_mode="html")
        elif t == "skip":
            await q.update_user(uid, reminder_time=None, notify_reminders=False)
            await q.clear_state(uid)
            user = await q.get_user(uid)
            await event.edit("✅ <b>Daily reminder removed.</b>", parse_mode="html",
                             buttons=kb_settings(user))
        else:
            await q.update_user(uid, reminder_time=t)
            await q.clear_state(uid)
            user = await q.get_user(uid)
            await event.edit(f"✅ Reminder set to <b>{t}</b>", parse_mode="html",
                             buttons=kb_settings(user))


# ── Helpers ───────────────────────────────────────────────────

async def _build_stats_v2(uid, scope="user", period="all"):
    from datetime import date
    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()
    year_start = date.today().replace(month=1, day=1).isoformat()
    
    start_date = None
    end_date = None
    
    if period == "today":
        start_date = today
        end_date = today
    elif period == "month":
        start_date = month_start
    elif period == "year":
        start_date = year_start
        
    if scope == "user":
        stats = await q.get_user_category_stats(uid, start_date, end_date)
    else:
        stats = await q.get_global_category_stats(start_date, end_date)
        
    return msg_category_stats(stats, scope, period)

async def _build_stats(uid, user):
    today       = date.today().isoformat()
    year_start  = date.today().replace(month=1, day=1).isoformat()
    month_start = date.today().replace(day=1).isoformat()
    grand   = await q.get_grand_total()
    yearly  = await q.get_yearly_total()
    monthly = await q.get_monthly_total()
    daily   = await q.get_daily_total()
    u_life  = user.get("lifetime_count", 0)
    u_year  = await q.get_user_period_total(uid, year_start)
    u_month = await q.get_user_period_total(uid, month_start)
    u_today = await q.get_user_period_total(uid, today, today)
    active  = await q.get_active_tasks()
    members = await q.get_user_count()
    return msg_stats_card(grand, yearly, monthly, daily,
                          u_life, u_year, u_month, u_today,
                          user.get("streak", 0), len(active), members)

async def _send_stats_dm(client, user_id, text):
    try:
        await client.send_message(
            user_id, text,
            parse_mode="html",
            noforwards=True,
        )
    except Exception:
        pass

async def _process_contribution(event, uid, task, task_id, amount, client):
    # Cap at remaining target
    if task.get("target"):
        remaining_target = task["target"] - task.get("total_count", 0)
        if amount > remaining_target:
            amount = remaining_target
    
    if amount <= 0:
        return await event.answer("Task is already complete!", alert=True)

    if task.get("daily_limit_per_user"):
        daily_total = await q.get_user_daily_total(task_id, uid)
        remaining_daily = task["daily_limit_per_user"] - daily_total
        if remaining_daily <= 0:
            msg = "📅 You've completed your portion for today — JazakAllahu Khairan. 🌙\nCome back tomorrow!"
            try:
                await event.answer(msg, alert=True)
            except Exception:
                await event.respond(msg, parse_mode="html")
            return
        amount = min(amount, remaining_daily)

    old_total = task.get("total_count", 0)
    await q.add_contribution(task_id, uid, amount)
    new_total = old_total + amount

    # Refresh task view
    task = await q.get_task(task_id)  # get updated
    user_total = await q.get_user_task_total(task_id, uid)
    user_daily = await q.get_user_daily_total(task_id, uid)
    
    remaining_view = None
    if task.get("target"):
        remaining_view = max(0, task["target"] - task["total_count"])
    
    text = msg_task_view(task, user_total, user_daily)
    kb = kb_task_view(task, user_total, remaining=remaining_view)
    
    try:
        if isinstance(event, events.CallbackQuery):
            await event.edit(text, parse_mode="html", buttons=kb)
        else:
            await event.respond(text, parse_mode="html", buttons=kb)
    except telethon.errors.rpcerrorlist.MessageNotModifiedError:
        pass

    announced = set(task.get("milestone_announced", []))
    if task.get("target"):
        # Safety check: if target reached, end task
        if new_total >= task["target"] and task["status"] == "active":
            await q.end_task(task_id)
            task["status"] = "ended"
            await announce_task_ended(client, task)
        
        # Milestone announcements
        for pct in MILESTONE_PERCENTAGES:
            if pct not in announced:
                threshold = int(task["target"] * pct / 100)
                if new_total >= threshold:
                    await q.add_milestone_announced(task_id, pct)
                    task["total_count"] = new_total
                    await announce_milestone(client, task, pct)
                    # Note: pct==100 case is now covered by the safety check above
    else:
        for abs_m in ABSOLUTE_MILESTONES:
            if abs_m not in announced and old_total < abs_m <= new_total:
                await q.add_milestone_announced(task_id, abs_m)
                task["total_count"] = new_total
                await announce_milestone(client, task, abs_m)

    task = await q.get_task(task_id) or task
    user_total = await q.get_user_task_total(task_id, uid)
    user_daily = await q.get_user_daily_total(task_id, uid)
    confirmation = (
        f"✅ <b>+{fmt_num(amount)} {task['dhikr_text']}</b> recorded!\n\n"
        + msg_task_view(task, user_total, user_daily)
    )
    try:
        await event.edit(confirmation, parse_mode="html",
                         buttons=kb_task_view(task, user_total))
    except Exception:
        await event.respond(confirmation, parse_mode="html",
                            buttons=kb_task_view(task, user_total))
