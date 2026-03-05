import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import types
from utils.messages import fmt_num

def _style(color):
    return types.KeyboardButtonStyle(
        bg_primary=(color == "primary"),
        bg_success=(color == "success"),
        bg_danger =(color == "danger"),
    )

def btn(text, data, color="primary"):
    return types.KeyboardButtonCallback(
        text=text,
        data=data.encode() if isinstance(data, str) else data,
        style=_style(color),
    )

def btn_url(text, url):
    return types.KeyboardButtonUrl(text=text, url=url)

def row(*buttons):
    return types.KeyboardButtonRow(buttons=list(buttons))

def markup(*rows):
    return types.ReplyInlineMarkup(rows=list(rows))

def tid(task_id):
    return str(task_id)

# ── REGISTRATION ─────────────────────────────────────────────

def kb_welcome():
    return markup(row(btn("🌙  Begin Registration", "reg:start", "primary")))

def kb_visibility():
    return markup(
        row(btn("🟢  Public — show my username",    "reg:vis:public",    "success")),
        row(btn("🟡  Anonymous — Servant_XXXX",     "reg:vis:anonymous", "primary")),
        row(btn("⚫  Ghost — fully invisible",      "reg:vis:ghost",     "danger")),
    )

def kb_notifications(selected):
    def label(key, emoji, text):
        tick = "✅ " if key in selected else ""
        return btn(f"{tick}{emoji} {text}", f"reg:notif:{key}",
                   "success" if key in selected else "primary")
    return markup(
        row(label("tasks",       "🔔", "New tasks")),
        row(label("endings",     "🏁", "Task endings")),
        row(label("leaderboard", "📊", "Leaderboard")),
        row(label("reminders",   "⏰", "Daily reminder")),
        row(btn("✔  Confirm", "reg:notif:confirm", "primary")),   # NOT green
    )

def kb_reminder_time():
    return markup(
        row(btn("6:00 AM",  "reg:time:06:00","primary"), btn("7:00 AM",  "reg:time:07:00","primary")),
        row(btn("8:00 AM",  "reg:time:08:00","primary"), btn("9:00 AM",  "reg:time:09:00","primary")),
        row(btn("After Dhuhr",   "reg:time:dhuhr",   "primary"), btn("After Asr",   "reg:time:asr",    "primary")),
        row(btn("After Maghrib", "reg:time:maghrib", "primary"), btn("After Isha",  "reg:time:isha",   "primary")),
        row(btn("✍️  Custom time", "reg:time:custom", "primary")),
        row(btn("⏭  Skip — no reminder", "reg:time:skip", "primary")),
    )

def kb_confirm_intention():
    return markup(row(btn("✅  I understand – BismiLlah", "reg:intention:confirm", "success")))

# ── MEMBER MENU ───────────────────────────────────────────────

def kb_member_menu(is_admin=False):
    rows = [
        row(btn("📿  Active Tasks", "menu:tasks",    "primary")),
        row(btn("📊  My Stats",     "menu:stats",    "primary")),
        row(btn("⚙️  Settings",     "menu:settings", "primary")),
    ]
    if is_admin:
        rows.append(row(btn("👑  Admin Panel", "admin:open", "success")))
    return markup(*rows)

def kb_task_list(active_tasks):
    rows = [row(btn(f"📿 {t['title']}", f"task:view:{tid(t['_id'])}", "primary")) for t in active_tasks]
    rows.append(row(btn("⬅️  Back", "menu:main", "primary")))
    return markup(*rows)

def kb_task_view(task, user_task_total, remaining=None, leaderboard=True):
    # Dynamic buttons based on remaining
    options = [1, 10, 33, 100, 500, 1000]
    visible_options = [o for o in options if remaining is None or o <= remaining]
    
    rows = []
    # Group into rows of 3
    for i in range(0, len(visible_options), 3):
        chunk = visible_options[i:i+3]
        rows.append(row(*[btn(f"+{fmt_num(o)}", f"contrib:{tid(task['_id'])}:{o}", "success") for o in chunk]))
    
    if remaining is None or remaining > 0:
        rows.append(row(btn("✍️ Custom Amount", f"contrib:{tid(task['_id'])}:custom", "primary")))
    
    if task.get("media"):
        rows.append(row(btn("📎  View Attachments", f"task:media:{tid(task['_id'])}", "primary")))
    if leaderboard and task.get("leaderboard_visible", True):
        rows.append(row(btn("🏆  Leaderboard", f"task:lb:{tid(task['_id'])}", "primary")))
    rows.append(row(btn("⬅️  Back to Tasks", "menu:tasks", "primary")))
    return markup(*rows)

def kb_contrib_confirm(task_id, amount):
    return markup(
        row(btn("✅  Yes, I confirm", f"contrib:conf:{tid(task_id)}:{amount}", "success")),
        row(btn("❌  Cancel", f"task:view:{tid(task_id)}", "danger"))
    )

def kb_stats_view(scope="user", period="all"):
    rows = []
    if scope == "user":
        rows.append(row(btn("🌍  Global Stats", "stats:scope:global", "primary")))
    else:
        rows.append(row(btn("👤  My Stats", "stats:scope:user", "primary")))
    
    # Period buttons
    rows.append(row(
        btn("☀️ Today", f"stats:period:today:{scope}", "success" if period=="today" else "primary"),
        btn("🗓 Month", f"stats:period:month:{scope}", "success" if period=="month" else "primary")
    ))
    rows.append(row(
        btn("📅 Year", f"stats:period:year:{scope}", "success" if period=="year" else "primary"),
        btn("♾ All Time", f"stats:period:all:{scope}", "success" if period=="all" else "primary")
    ))
    
    rows.append(row(btn("⬅️  Back", "menu:main", "primary")))
    return markup(*rows)

def kb_settings(user):
    vis_labels = {"public":"🟢 Public","anonymous":"🟡 Anonymous","ghost":"⚫ Ghost"}
    vis = vis_labels.get(user.get("visibility","anonymous"),"🟡 Anonymous")
    return markup(
        row(btn(f"👁  Visibility: {vis}", "settings:visibility",    "primary")),
        row(btn("🔔  Notifications",       "settings:notifications", "primary")),
        row(btn("⏰  Reminder Time",        "settings:reminder",      "primary")),
        row(btn("⬅️  Back",                "menu:main",              "primary")),
    )

# ── ADMIN MAIN ────────────────────────────────────────────────

def kb_admin_main(perms, is_owner=False):
    rows = [
        row(btn("📋  Draft Tasks",   "adm:tasks:draft",  "primary"),
            btn("✅  Active Tasks",  "adm:tasks:active", "primary")),
        row(btn("➕  Create Task",   "adm:task:create",  "success")),
        row(btn("📊  Statistics",    "adm:stats",        "primary")),
        row(btn("👥  Users",         "adm:users:list",   "primary")),
        row(btn("📣  Broadcast",     "adm:broadcast",    "primary")),
    ]
    if is_owner:
        rows.append(row(btn("👑  Manage Admins", "adm:admins:list", "primary")))
        rows.append(row(btn("⚙️  Bot Settings",  "adm:settings",   "primary")))
    elif perms.get("appoint_admins"):
        rows.append(row(btn("👥  Manage Admins", "adm:admins:list", "primary")))
    rows.append(row(btn("⬅️  Back to Menu", "menu:main", "primary")))
    return markup(*rows)

# ── TASK WIZARD ───────────────────────────────────────────────

def kb_skip_cancel():
    return markup(row(btn("⏭  Skip","wiz:skip","primary"), btn("🗑  Cancel","wiz:cancel","danger")))

def kb_yes_skip_cancel():
    return markup(row(
        btn("✅  Yes",    "wiz:yes",    "success"),
        btn("⏭  Skip",   "wiz:skip",   "primary"),
        btn("🗑  Cancel", "wiz:cancel", "danger")
    ))

def kb_task_type():
    return markup(
        row(btn("🔢  Count-Based",  "wiz:type:count",     "primary")),
        row(btn("⏱  Time-Based",   "wiz:type:time",      "primary")),
        row(btn("🔄  Recurring",    "wiz:type:recurring", "primary")),
        row(btn("🚨  Emergency",    "wiz:type:emergency", "danger")),
        row(btn("🗑  Cancel",       "wiz:cancel",         "danger")),
    )

def kb_dhikr_categories(categories):
    rows = [row(btn(c, f"wiz:cat:{c}", "primary")) for c in categories]
    rows.append(row(btn("🗑  Cancel", "wiz:cancel", "danger")))
    return markup(*rows)

def kb_dhikr_subcategories(subcategories):
    rows = [row(btn(s, f"wiz:sub:{s}", "primary")) for s in subcategories]
    rows.append(row(btn("⬅️  Back", "wiz:dhikr", "primary")))
    return markup(*rows)

def kb_dhikr_sub_subcategories(sub_subcategories):
    rows = [row(btn(ss, f"wiz:ssub:{ss}", "primary")) for ss in sub_subcategories]
    rows.append(row(btn("⬅️  Back", "wiz:dhikr", "primary")))
    return markup(*rows)

def kb_wiz_preset_choice():
    return markup(
        row(btn("✨ Use Predefined", "wiz:preset:use", "success")),
        row(btn("✍️ Add Custom",     "wiz:preset:custom", "primary")),
        row(btn("🗑  Cancel",         "wiz:cancel", "danger"))
    )

def kb_duration():
    return markup(
        row(btn("1 Hour",  "wiz:dur:1",   "primary"), btn("3 Hours",  "wiz:dur:3",   "primary")),
        row(btn("6 Hours", "wiz:dur:6",   "primary"), btn("12 Hours", "wiz:dur:12",  "primary")),
        row(btn("1 Day",   "wiz:dur:24",  "primary"), btn("3 Days",   "wiz:dur:72",  "primary")),
        row(btn("1 Week",  "wiz:dur:168", "primary")),
        row(btn("✍️  Custom",             "wiz:dur:custom", "primary")),
        row(btn("⏭  No end date / manual", "wiz:dur:skip", "primary")),   # skip = no expiry
        row(btn("🗑  Cancel",              "wiz:cancel",    "danger")),
    )

def kb_recurring_interval():
    return markup(
        row(btn("📅  Daily",  "wiz:recur:daily",  "primary"),
            btn("📆  Weekly", "wiz:recur:weekly", "primary")),
        row(btn("🗑  Cancel", "wiz:cancel", "danger")),
    )

def kb_daily_limit():
    return markup(
        row(btn("✅  Yes, set a limit", "wiz:limit:yes", "success"),
            btn("❌  No limit",         "wiz:limit:no",  "primary")),
        row(btn("🗑  Cancel", "wiz:cancel", "danger")),
    )

def kb_leaderboard_choice():
    return markup(
        row(btn("👁  Public Leaderboard", "wiz:lb:yes", "success"),
            btn("🔒  No Leaderboard",     "wiz:lb:no",  "primary")),
        row(btn("🗑  Cancel", "wiz:cancel", "danger")),
    )

def kb_media_choice():
    return markup(
        row(btn("📷  Image",       "wiz:media:image",   "primary"),
            btn("🎥  Video",       "wiz:media:video",   "primary")),
        row(btn("🎙  Audio",       "wiz:media:audio",   "primary"),
            btn("🔗  YouTube URL", "wiz:media:youtube", "primary")),
        row(btn("⏭  No Media / Done", "wiz:media:done", "primary")),
        row(btn("🗑  Cancel",          "wiz:cancel",     "danger")),
    )

def kb_add_more_media():
    return markup(
        row(btn("➕  Add Another", "wiz:media:more", "success"),
            btn("✅  Done",        "wiz:media:done", "primary")),
    )

def kb_task_draft_actions():
    """After wizard completes — save as draft or publish immediately."""
    return markup(
        row(btn("💾  Save as Draft",          "wiz:savedraft", "primary")),
        row(btn("🚀  Publish & Activate Now", "wiz:publish",   "success")),
        row(btn("✍️  Edit",                   "wiz:edit",      "primary")),
        row(btn("🗑  Cancel",                  "wiz:cancel",    "danger")),
    )

def kb_draft_task_actions(task_id):
    """Actions on a saved draft."""
    return markup(
        row(btn("🚀  Activate Task",  f"adm:task:activate:{tid(task_id)}", "success")),
        row(btn("✏️  Edit",           f"adm:task:editdesc:{tid(task_id)}", "primary")),
        row(btn("🗑  Delete Draft",   f"adm:task:delete:{tid(task_id)}",   "danger")),
        row(btn("⬅️  Back",           "adm:tasks:draft",                   "primary")),
    )

# ── MANAGE ACTIVE TASK ────────────────────────────────────────

def kb_manage_task(task, perms, is_owner):
    tid_str = tid(task["_id"])
    is_paused = task.get("status") == "paused"
    rows = []
    if is_owner or perms.get("pause_resume_tasks"):
        rows.append(row(btn(
            "▶️  Resume Task" if is_paused else "⏸  Pause Task",
            f"adm:task:{'resume' if is_paused else 'pause'}:{tid_str}",
            "success" if is_paused else "primary"
        )))
    if is_owner or perms.get("end_tasks_early"):
        rows.append(row(btn("🔚  End Task Early",       f"adm:task:end:{tid_str}",       "danger")))
    if is_owner or perms.get("extend_tasks"):
        rows.append(row(btn("⏳  Extend Duration",       f"adm:task:extend:{tid_str}",    "primary")))
    if is_owner or perms.get("toggle_leaderboard"):
        lb_text = "🔕  Disable Leaderboard" if task.get("leaderboard_visible") else "👁  Enable Leaderboard"
        rows.append(row(btn(lb_text,                     f"adm:task:togglelb:{tid_str}",  "primary")))
    if is_owner or perms.get("send_announcements"):
        rows.append(row(btn("📣  Broadcast Reminder",   f"adm:task:remind:{tid_str}",    "primary")))
    if is_owner or perms.get("edit_tasks"):
        rows.append(row(btn("✏️  Edit Description",     f"adm:task:editdesc:{tid_str}",  "primary")))
    if is_owner or perms.get("add_media"):
        rows.append(row(btn("📎  Edit Media",            f"adm:task:editmedia:{tid_str}", "primary")))
    if is_owner or perms.get("view_contributors"):
        rows.append(row(btn("👤  View Contributors",    f"adm:task:contribs:{tid_str}",  "primary")))
    if is_owner or perms.get("view_per_task_stats"):
        rows.append(row(btn("📈  Daily Breakdown",      f"adm:task:daily:{tid_str}",     "primary")))
    if is_owner or perms.get("delete_tasks"):
        rows.append(row(btn("🗑  Delete Task",           f"adm:task:delete:{tid_str}",    "danger")))
    rows.append(row(btn("⬅️  Back", "adm:tasks:active", "primary")))
    return markup(*rows)

def kb_extend_duration():
    return markup(
        row(btn("+1 Hour",  "ext:1",   "primary"), btn("+3 Hours",  "ext:3",   "primary")),
        row(btn("+6 Hours", "ext:6",   "primary"), btn("+12 Hours", "ext:12",  "primary")),
        row(btn("+1 Day",   "ext:24",  "primary"), btn("+3 Days",   "ext:72",  "primary")),
        row(btn("✍️  Custom",   "ext:custom", "primary")),
        row(btn("🗑  Cancel",   "ext:cancel", "danger")),
    )

def kb_confirm_end(task_id):
    return markup(
        row(btn("⚠️  Yes, End Task", f"adm:task:endconfirm:{tid(task_id)}", "danger"),
            btn("❌  Cancel",         "adm:tasks:active",                    "primary")),
    )

def kb_confirm_delete(task_id):
    return markup(
        row(btn("⚠️  Yes, Delete", f"adm:task:deleteconfirm:{tid(task_id)}", "danger"),
            btn("❌  Cancel",       f"adm:task:manage:{tid(task_id)}",         "primary")),
    )

# ── BROADCAST ─────────────────────────────────────────────────

def kb_broadcast_menu():
    return markup(
        row(btn("📢  General Reminder",   "bc:template:general",  "primary")),
        row(btn("⏳  Urgent / Ending Soon","bc:template:urgent",   "primary")),
        row(btn("🌙  Jumu'ah Message",     "bc:template:friday",   "primary")),
        row(btn("🌙  Ramadan Message",     "bc:template:ramadan",  "primary")),
        row(btn("✍️  Custom Message",      "bc:template:custom",   "primary")),
        row(btn("⬅️  Back",               "adm:main",             "primary")),
    )

def kb_broadcast_confirm(template_key):
    return markup(
        row(btn("📢  Send to ALL members",    f"bc:send:all:{template_key}",   "danger")),
        row(btn("🔔  Send to opted-in only",  f"bc:send:opted:{template_key}", "success")),
        row(btn("✍️  Edit message",           f"bc:edit:{template_key}",       "primary")),
        row(btn("❌  Cancel",                  "adm:broadcast",                 "primary")),
    )

# ── STATS ─────────────────────────────────────────────────────

def kb_stats_menu(is_owner, perms):
    rows = [
        row(btn("🌍  Grand Total",  "adm:stats:grand",   "primary")),
        row(btn("📅  This Year",    "adm:stats:yearly",  "primary"),
            btn("🗓  This Month",   "adm:stats:monthly", "primary")),
        row(btn("☀️  Today",       "adm:stats:daily",   "primary")),
    ]
    if is_owner or perms.get("view_per_task_stats"):
        rows.append(row(btn("📋  Per-Task Breakdown", "adm:stats:pertask", "primary")))
    if is_owner or perms.get("export_stats"):
        rows.append(row(btn("📤  Export Report", "adm:stats:export", "success")))
    rows.append(row(btn("⬅️  Back", "adm:main", "primary")))
    return markup(*rows)

# ── USERS ─────────────────────────────────────────────────────

def kb_user_actions(target_user_id, is_banned, is_owner, perms):
    rows = []
    if is_owner or perms.get("view_contributors"):
        rows.append(row(btn("📊  View Contributions", f"adm:user:contribs:{target_user_id}", "primary")))
    if is_owner or perms.get("ban_users"):
        if is_banned:
            rows.append(row(btn("✅  Unban User", f"adm:user:unban:{target_user_id}", "success")))
        else:
            rows.append(row(btn("🚫  Ban User",   f"adm:user:ban:{target_user_id}",   "danger")))
    rows.append(row(btn("⬅️  Back", "adm:users:list", "primary")))
    return markup(*rows)

# ── ADMIN MANAGEMENT ─────────────────────────────────────────

def kb_admin_list(admin_list, is_owner):
    rows = [row(btn(
        f"{'🛡️' if a['role']=='super_admin' else '⚙️'} {a.get('username','ID:'+str(a['user_id']))}",
        f"adm:admins:view:{a['user_id']}", "primary")) for a in admin_list]
    if is_owner:
        rows.append(row(btn("➕  Add Admin", "adm:admins:add", "success")))
    rows.append(row(btn("⬅️  Back", "adm:main", "primary")))
    return markup(*rows)

def kb_admin_profile(target_uid, role, is_owner, viewer_is_super):
    rows = []
    if is_owner:
        if role == "admin":
            rows.append(row(btn("⬆️  Promote to Super Admin", f"adm:admins:promote:{target_uid}", "success")))
        else:
            rows.append(row(btn("⬇️  Demote to Admin",        f"adm:admins:demote:{target_uid}",  "primary")))
        rows.append(row(btn("🔧  Edit Permissions", f"adm:admins:editperms:{target_uid}", "primary")))
        rows.append(row(btn("🗑  Remove Admin",      f"adm:admins:remove:{target_uid}",    "danger")))
    elif viewer_is_super and role == "admin":
        rows.append(row(btn("🔧  Edit Permissions", f"adm:admins:editperms:{target_uid}", "primary")))
        rows.append(row(btn("🗑  Remove Admin",      f"adm:admins:remove:{target_uid}",    "danger")))
    rows.append(row(btn("⬅️  Back", "adm:admins:list", "primary")))
    return markup(*rows)

def kb_permissions_editor(target_uid, current_perms, perm_list):
    rows = []
    for perm in perm_list:
        on = current_perms.get(perm, False)
        label = perm.replace("_"," ").title()
        rows.append(row(btn(f"{'✅' if on else '❌'} {label}",
                            f"adm:admins:toggleperm:{target_uid}:{perm}",
                            "success" if on else "primary")))
    rows.append(row(btn("💾  Save & Close", f"adm:admins:view:{target_uid}", "success")))
    return markup(*rows)

def kb_add_admin_role():
    return markup(
        row(btn("🛡️  Super Admin", "adm:admins:newrole:super_admin", "primary"),
            btn("⚙️  Admin",       "adm:admins:newrole:admin",       "primary")),
        row(btn("🗑  Cancel", "adm:admins:list", "danger")),
    )

# ── OWNER SETTINGS ────────────────────────────────────────────

def kb_owner_settings():
    return markup(
        row(btn("🌙  Toggle Ramadan Mode",        "adm:settings:ramadan",    "primary")),
        row(btn("📣  Announcement Templates",     "adm:settings:templates",  "primary")),
        row(btn("📊  Toggle Group Stats",         "adm:settings:groupstats", "primary")),
        row(btn("🧹  Clear All FSM States",       "adm:settings:clearfsm",   "danger")),
        row(btn("⬅️  Back",                       "adm:main",               "primary")),
    )

def kb_back_admin():
    return markup(row(btn("⬅️  Back to Admin Menu", "adm:main", "primary")))

def kb_back_tasks():
    return markup(row(btn("⬅️  Back to Tasks", "adm:tasks:active", "primary")))
