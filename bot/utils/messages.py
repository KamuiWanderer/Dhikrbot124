import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

def fmt_num(n):
    return f"{n:,}"

def progress_bar(current, target, length=10):
    if not target:
        return ""
    pct = min(current / target, 1.0)
    filled = int(pct * length)
    return f"[{'█'*filled}{'░'*(length-filled)}] {pct*100:.1f}%"

def task_type_label(t):
    return {"count":"🔢 Count-Based","time":"⏱ Time-Based",
            "recurring":"🔄 Recurring","emergency":"🚨 Emergency"}.get(t, t)

def status_label(s):
    return {"active":"🟢 Active","paused":"⏸ Paused","ended":"🔴 Ended"}.get(s, s)

def ends_at_fmt(task):
    ends = task.get("ends_at")
    if not ends:
        if task.get("target"):
            return "Until target reached"
        return "Until manually ended"
    if isinstance(ends, datetime):
        return ends.strftime("%d %b %Y, %H:%M UTC")
    return str(ends)

def h(text):
    """Escape HTML special chars."""
    return str(text).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# ── REGISTRATION ─────────────────────────────────────────────

MSG_WELCOME = (
    "<blockquote>بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيم</blockquote>\n\n"
    "🌙 <b>Welcome to the Dhikr Bot</b>\n\n"
    "This bot lets our community do <b>collective dhikr</b> together.\n"
    "Every count you submit is added to the community's shared total.\n\n"
    "Let's set up your account — takes less than a minute. 🤲"
)

MSG_VISIBILITY = (
    "👁 <b>How should you appear in this community?</b>\n\n"
    "🟢 <b>Public</b> — your username shows on leaderboards\n"
    "🟡 <b>Anonymous</b> — you appear as <i>Servant_XXXX</i>\n"
    "⚫ <b>Ghost</b> — fully invisible, only Allah sees your count\n"
    "\n<i>You can change this later in Settings.</i>"
)

MSG_NOTIFICATIONS = (
    "🔔 <b>Notifications</b> — tap to toggle, then confirm:\n\n"
    "• <b>New tasks</b> — when a new dhikr task starts\n"
    "• <b>Task endings</b> — when a task finishes\n"
    "• <b>Leaderboard</b> — ranking updates\n"
    "• <b>Reminder</b> — daily nudge at your chosen time"
)

MSG_REMINDER_TIME = (
    "⏰ <b>Daily Reminder Time</b>\n\n"
    "The bot will DM you at this time when tasks are active.\n"
    "<i>Tap Skip if you don't want a reminder.</i>"
)

MSG_CUSTOM_TIME = (
    "✍️ Type your reminder time in <b>HH:MM</b> format (24hr).\n"
    "Example: <code>21:30</code>"
)

MSG_INTENTION = (
    "<blockquote>Every dhikr you submit here is for Allah alone.\n"
    "Not for the leaderboard. Not for the count.\n"
    "Let your niyyah be sincere.</blockquote>\n\n"
    "Tap below when you're ready. 🤲"
)

MSG_GROUP_START = (
    "وَعَلَيْكُمُ السَّلَام وَرَحْمَةُ اللَّهِ 🌙\n\n"
    "To join our community dhikr, open the bot in your DM:"
)

def msg_registration_complete(user):
    vis = {"public":"🟢 Public","anonymous":"🟡 Anonymous","ghost":"⚫ Ghost"}
    notifs = []
    if user.get("notify_tasks"):       notifs.append("New task announcements")
    if user.get("notify_endings"):     notifs.append("Task endings")
    if user.get("notify_leaderboard"): notifs.append("Leaderboard updates")
    if user.get("notify_reminders"):   notifs.append(f"Daily reminder at {h(user.get('reminder_time','—'))}")
    notif_text = "\n".join(f"  • {n}" for n in notifs) if notifs else "  • None selected"
    return (
        f"✅ <b>Registration complete — BismiLlah!</b>\n\n"
        f"👁 Visibility: {vis.get(user['visibility'],'—')}\n"
        f"🔔 Notifications:\n{notif_text}\n\n"
        f"<i>Change anything anytime from ⚙️ Settings.</i>\n\n"
        f"<blockquote>May Allah accept every dhikr you make here. 🌙</blockquote>"
    )

# ── TASK DISPLAY ─────────────────────────────────────────────

def msg_task_view(task, user_total, user_daily):
    lines = [f"📿 <b>{h(task['title'])}</b>\n"]
    lines.append(f"<i>Dhikr:</i> <b>{h(task['dhikr_text'])}</b>\n")
    if task.get("description"):
        lines.append(f"{h(task['description'])}\n")
    if task.get("reference"):
        lines.append(f"<blockquote>📖 {h(task['reference'])}</blockquote>\n")
    lines.append("📊 <b>Community Progress:</b>")
    if task.get("target"):
        lines.append(f"{fmt_num(task['total_count'])} / {fmt_num(task['target'])} {h(task['dhikr_text'])}")
        lines.append(progress_bar(task['total_count'], task['target']))
    else:
        lines.append(f"<b>{fmt_num(task['total_count'])}</b> {h(task['dhikr_text'])}")
    lines.append(f"\n👤 <b>Your contribution:</b> {fmt_num(user_total)}")
    if task.get("daily_limit_per_user"):
        remaining = max(0, task["daily_limit_per_user"] - user_daily)
        lines.append(f"📅 Today: {fmt_num(user_daily)} / {fmt_num(task['daily_limit_per_user'])} (Remaining: {fmt_num(remaining)})")
    lines.append(f"\n⏰ Ends: {ends_at_fmt(task)}")
    lines.append(f"Status: {status_label(task['status'])}")
    return "\n".join(lines)

def msg_task_announcement(task):
    lines = [
        "🌟 <b>New Dhikr Task Started!</b>\n",
        f"📿 <b>{h(task['title'])}</b>",
        f"<i>Dhikr:</i> <b>{h(task['dhikr_text'])}</b>\n",
    ]
    if task.get("intention_reminder"):
        lines.append(f"<blockquote>🤲 {h(task['intention_reminder'])}</blockquote>\n")
    if task.get("description"):
        lines.append(f"{h(task['description'])}\n")
    if task.get("reference"):
        lines.append(f"<blockquote>📖 {h(task['reference'])}</blockquote>\n")
    if task.get("target"):
        lines.append(f"🎯 Target: <b>{fmt_num(task['target'])} {h(task['dhikr_text'])}</b>")
    lines.append(f"⏰ Until: {ends_at_fmt(task)}")
    lines.append(f"Type: {task_type_label(task['type'])}\n")
    lines.append("➡️ Open the bot: /start")
    return "\n".join(lines)

def msg_task_ended(task, final_count):
    return (
        f"🏁 <b>Task Ended: {h(task['title'])}</b>\n\n"
        f"الحمد لله — <b>{fmt_num(final_count)} {h(task['dhikr_text'])}</b> submitted by our community.\n\n"
        f"جزاكم الله خيرًا to everyone who participated.\n"
        f"May every count be accepted. 🤲"
    )

def msg_milestone(task, milestone, count):
    if isinstance(milestone, int) and milestone <= 100:
        text = f"{milestone}% of our goal"
    else:
        text = f"{fmt_num(int(milestone))} {h(task['dhikr_text'])}"
    return (
        f"🎉 <b>الحمد لله! Milestone Reached!</b>\n\n"
        f"📿 <b>{h(task['title'])}</b>\n"
        f"We have reached <b>{text}</b>!\n\n"
        f"<blockquote>Current total: <b>{fmt_num(count)} {h(task['dhikr_text'])}</b></blockquote>\n\n"
        f"Keep going — every count matters. 🌙"
    )

def msg_emergency_task(task):
    return (
        f"🚨 <b>EMERGENCY DU'A — Please Join Now</b>\n\n"
        f"📿 <b>{h(task['title'])}</b>\n"
        f"<i>Dhikr:</i> <b>{h(task['dhikr_text'])}</b>\n\n"
        f"{h(task.get('description',''))}\n\n"
        f"Open the bot: /start\n\n"
        f"<blockquote>May Allah answer every du'a. 🤲</blockquote>"
    )

# ── STATS ─────────────────────────────────────────────────────

def msg_category_stats(stats, scope="user", period="all"):
    scope_label = "Your" if scope == "user" else "Global"
    period_label = {
        "today": "Today",
        "week": "This Week",
        "month": "This Month",
        "year": "This Year",
        "all": "All Time"
    }.get(period, "All Time")
    
    lines = [f"📊 <b>{scope_label} Dhikr Stats ({period_label})</b>\n"]
    
    if not stats:
        lines.append("<i>No contributions yet for this period.</i>")
        return "\n".join(lines)
    
    # Hierarchical grouping: Year -> Month -> Dhikr
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    current_year = None
    current_month = None
    
    for s in stats:
        year = s["_id"]["year"]
        month = s["_id"]["month"]
        dhikr = s["_id"]["dhikr_text"]
        total = s["total"]
        
        if year != current_year:
            lines.append(f"\n📅 <b>Year {year}</b>")
            current_year = year
            current_month = None
            
        if month != current_month:
            lines.append(f"  🗓 <b>{months[month]}</b>")
            current_month = month
            
        lines.append(f"    ▫️ {h(dhikr)}: <b>{fmt_num(total)}</b>")
        
    return "\n".join(lines)

def msg_new_user_owner(user):
    return (
        f"👤 <b>New User Joined!</b>\n\n"
        f"<b>Name:</b> {h(user['display_name'])}\n"
        f"<b>Username:</b> @{h(user['username']) if user['username'] else 'None'}\n"
        f"<b>Visibility:</b> {user['visibility']}\n"
        f"<b>Joined at:</b> {user['registered_at'].strftime('%Y-%m-%d %H:%M:%S')}"
    )

def msg_contribution_warning(amount):
    return (
        f"⚠️ <b>Important Reminder</b>\n\n"
        f"You are adding <b>{fmt_num(amount)}</b> dhikr.\n"
        f"Please ensure you have actually completed this amount or intend to complete it right now.\n\n"
        f"<blockquote>Lying about dhikr counts is a sin (gunah). Sincerity is the essence of worship.</blockquote>\n\n"
        f"Do you confirm this amount?"
    )

def msg_owner_concise_stats(stats):
    return (
        f"📊 <b>Bot Overview</b>\n\n"
        f"👥 <b>Total Users:</b> {fmt_num(stats['total_users'])}\n"
        f"📿 <b>Total Dhikr:</b> {fmt_num(stats['total_dhikr'])}\n"
        f"✅ <b>Active Tasks:</b> {stats['active_tasks']}\n"
    )

def msg_stats_card(grand, yearly, monthly, daily,
                   user_lifetime, user_yearly, user_monthly, user_daily,
                   streak, active_tasks, total_members):
    return (
        f"📊 <b>Dhikr Stats</b>\n"
        f"{'─'*28}\n"
        f"<blockquote>"
        f"🌍 <b>Grand Total:</b>    {fmt_num(grand)}\n"
        f"📅 <b>This Year:</b>      {fmt_num(yearly)}\n"
        f"🗓 <b>This Month:</b>     {fmt_num(monthly)}\n"
        f"☀️ <b>Today:</b>          {fmt_num(daily)}"
        f"</blockquote>\n"
        f"{'─'*28}\n"
        f"<blockquote>"
        f"👤 <b>Your All-Time:</b>  {fmt_num(user_lifetime)}\n"
        f"📅 <b>Your Year:</b>      {fmt_num(user_yearly)}\n"
        f"🗓 <b>Your Month:</b>     {fmt_num(user_monthly)}\n"
        f"☀️ <b>Your Today:</b>     {fmt_num(user_daily)}"
        f"</blockquote>\n"
        f"{'─'*28}\n"
        f"🔥 <b>Streak:</b>  {streak} day{'s' if streak!=1 else ''}\n"
        f"📋 <b>Active Tasks:</b>  {active_tasks}\n"
        f"👥 <b>Members:</b>  {fmt_num(total_members)}\n"
    )

def msg_daily_breakdown(task_title, rows):
    if not rows:
        return f"📈 <b>Daily breakdown:</b> {h(task_title)}\n\nNo data yet."
    lines = [f"📈 <b>Daily breakdown: {h(task_title)}</b>\n"]
    prev = None
    for r in rows:
        day, total = r["_id"], r["total"]
        if prev is not None:
            diff = total - prev
            arrow = f"↑ +{fmt_num(diff)}" if diff > 0 else (f"↓ {fmt_num(diff)}" if diff < 0 else "→ same")
            lines.append(f"📅 <b>{day}:</b>  {fmt_num(total)}  <i>{arrow}</i>")
        else:
            lines.append(f"📅 <b>{day}:</b>  {fmt_num(total)}")
        prev = total
    return "\n".join(lines)

def msg_contributor_list(task_title, rows, users_map):
    if not rows:
        return f"No contributions yet for <b>{h(task_title)}</b>."
    lines = [f"👤 <b>Contributors: {h(task_title)}</b>\n"]
    for i, r in enumerate(rows, 1):
        u = users_map.get(r["_id"])
        name = (u.get("username") or u.get("display_name") or str(r["_id"])) if u else str(r["_id"])
        lines.append(f"{i}. {h(name)} — {fmt_num(r['total'])}")
    return "\n".join(lines)

def msg_task_preview(data):
    lines = ["📋 <b>Task Preview — Please Review</b>\n"]
    lines.append(f"📿 <b>Title:</b> {h(data.get('title','—'))}")
    if data.get("category"):
        lines.append(f"📁 <b>Category:</b> {h(data['category'])}")
    if data.get("subcategory"):
        lines.append(f"📂 <b>Subcategory:</b> {h(data['subcategory'])}")
    if data.get("sub_subcategory"):
        lines.append(f"🏷 <b>Type:</b> {h(data['sub_subcategory'])}")
    lines.append(f"🔤 <b>Dhikr:</b> {h(data.get('dhikr_text','—'))}")
    lines.append(f"🏷 <b>Task Type:</b> {task_type_label(data.get('type','—'))}")
    if data.get("target"):       lines.append(f"🎯 <b>Target:</b> {fmt_num(int(data['target']))}")
    if data.get("ends_at"):      lines.append(f"⏰ <b>Ends:</b> {ends_at_fmt(data)}")
    if data.get("description"):  lines.append(f"📝 <b>Description:</b> {h(data['description'])}")
    if data.get("reference"):    lines.append(f"📖 <b>Reference:</b> {h(data['reference'])}")
    if data.get("intention_reminder"): lines.append(f"🤲 <b>Intention:</b> {h(data['intention_reminder'])}")
    if data.get("daily_limit_per_user"): lines.append(f"📏 <b>Daily limit:</b> {fmt_num(int(data['daily_limit_per_user']))} per person")
    lines.append(f"🏆 <b>Leaderboard:</b> {'Yes' if data.get('leaderboard_visible', True) else 'No'}")
    if data.get("media"):        lines.append(f"📎 <b>Media:</b> {len(data['media'])} item(s)")
    lines.append("\n<i>Tap ✅ Save Draft or 🚀 Publish &amp; Activate to go live.</i>")
    return "\n".join(lines)

def msg_leaderboard(task, lb_rows, users_map, viewer_id, viewer_rank, viewer_total):
    lines = [f"🏆 <b>Leaderboard: {h(task['title'])}</b>\n"]
    pos = 0
    for r in lb_rows:
        u = users_map.get(r["_id"])
        if not u or u.get("visibility") == "ghost":
            continue
        pos += 1
        name = (f"@{u['username']}" if u.get("username") else u.get("display_name","?")) \
               if u.get("visibility") == "public" else u.get("anon_name","Servant_????")
        medal = ["🥇","🥈","🥉"][pos-1] if pos <= 3 else f"{pos}."
        lines.append(f"{medal} {h(name)} — {fmt_num(r['total'])}")
    lines.append(f"\n{'─'*20}")
    if viewer_total > 0:
        lines.append(f"👤 <b>Your rank:</b> #{viewer_rank} — {fmt_num(viewer_total)}")
    else:
        lines.append("👤 You haven't contributed to this task yet.")
    return "\n".join(lines)

# ── BROADCAST TEMPLATES ───────────────────────────────────────

BROADCAST_TEMPLATES = {
    "general":  "📿 <b>Dhikr Reminder</b>\n\n<blockquote>Don't let the day pass without remembrance of Allah.</blockquote>\n\nActive tasks are waiting — open the bot: /start 🌙",
    "urgent":   "⏳ <b>Task Ending Soon!</b>\n\nOne of our dhikr tasks is nearing its end.\nThere's still time — every count matters.\n\nOpen the bot: /start 🤲",
    "friday":   "🌙 <b>Jumu'ah Mubarak</b>\n\n<blockquote>Friday is blessed — increase your dhikr and salawat.</blockquote>\n\nJoin our community dhikr: /start",
    "ramadan":  "🌙 <b>Ramadan Reminder</b>\n\n<blockquote>Every good deed in Ramadan is multiplied.</blockquote>\n\nContribute to our collective dhikr: /start 🤲",
}
