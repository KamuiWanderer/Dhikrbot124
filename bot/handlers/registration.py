import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from telethon import events, types, functions
import random
from config import OWNER_ID
from db import queries as q
from keyboards.builder import (
    kb_welcome, kb_visibility, kb_notifications,
    kb_reminder_time, kb_confirm_intention, kb_member_menu
)
from utils.messages import (
    MSG_WELCOME, MSG_VISIBILITY, MSG_NOTIFICATIONS,
    MSG_REMINDER_TIME, MSG_CUSTOM_TIME, MSG_INTENTION,
    MSG_GROUP_START, msg_registration_complete
)


def register(client):

    # ── /start ───────────────────────────────────────────────
    @client.on(events.NewMessage(pattern="/start"))
    async def cmd_start(event):
        uid = event.sender_id
        args = event.message.message.split(" ", 1)
        deep_link = args[1] if len(args) > 1 else None

        # Group: send "open in DM" message with bot link
        if not event.is_private:
            me = await client.get_me()
            bot_link = f"https://t.me/{me.username}"
            if deep_link:
                bot_link += f"?start={deep_link}"
            markup = types.ReplyInlineMarkup(rows=[
                types.KeyboardButtonRow(buttons=[
                    types.KeyboardButtonUrl("🌙  Open Bot in DM", url=bot_link)
                ])
            ])
            await event.respond(MSG_GROUP_START, parse_mode="html", buttons=markup)
            return

        user = await q.get_user(uid)
        if user:
            if user.get("is_banned"):
                return
            
            # Handle deep links for registered users
            if deep_link:
                if deep_link.startswith("task_"):
                    task_id = deep_link.split("_", 1)[1]
                    from handlers.member import show_task_view
                    await show_task_view(event, task_id, is_new_msg=True)
                    return

            active = await q.get_active_tasks()
            is_admin_user = uid == OWNER_ID or await q.is_admin(uid)
            await event.respond(
                f"🌙 <b>Welcome back!</b>\n\n"
                f"There {'is' if len(active)==1 else 'are'} <b>{len(active)} active task(s)</b> right now.\n"
                f"What would you like to do?",
                parse_mode="html",
                buttons=kb_member_menu(is_admin=is_admin_user)
            )
            return

        # New user: start registration
        await q.set_state(uid, "reg:welcome", data={"deep_link": deep_link})
        await event.respond(MSG_WELCOME, parse_mode="html", buttons=kb_welcome())

    # ── /admin shortcut ──────────────────────────────────────
    @client.on(events.NewMessage(pattern="/admin"))
    async def cmd_admin(event):
        if not event.is_private:
            return
        uid = event.sender_id
        if not (uid == OWNER_ID or await q.is_admin(uid)):
            return
        from keyboards.builder import kb_admin_main
        from db.queries import ALL_PERMISSIONS
        adm = await q.get_admin(uid)
        perms = adm.get("permissions", {}) if adm else {}
        await event.respond(
            f"👑 <b>Admin Panel</b>\n<i>Welcome, {'Owner' if uid==OWNER_ID else 'Admin'}</i>",
            parse_mode="html",
            buttons=kb_admin_main(perms, is_owner=(uid == OWNER_ID))
        )

    # ── Callback: admin panel open from member menu ──────────
    @client.on(events.CallbackQuery(data=b"admin:open"))
    async def admin_open(event):
        uid = event.sender_id
        if not (uid == OWNER_ID or await q.is_admin(uid)):
            await event.answer("No access.", alert=True)
            return
        from keyboards.builder import kb_admin_main
        adm = await q.get_admin(uid)
        perms = adm.get("permissions", {}) if adm else {}
        await event.answer()
        await event.edit(
            f"👑 <b>Admin Panel</b>",
            parse_mode="html",
            buttons=kb_admin_main(perms, is_owner=(uid == OWNER_ID))
        )

    # ── Registration callbacks ───────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"reg:.*"))
    async def reg_callback(event):
        uid = event.sender_id
        data = event.data.decode()

        state_doc = await q.get_state(uid)
        state  = state_doc["state"] if state_doc else ""
        wizard = state_doc["data"]  if state_doc else {}

        await event.answer()

        # ── Step 1: Begin
        if data == "reg:start":
            await q.set_state(uid, "reg:visibility", data={})
            await event.edit(MSG_VISIBILITY, parse_mode="html", buttons=kb_visibility())
            return

        # ── Step 2: Visibility — only accept if we're in the right state
        if data.startswith("reg:vis:") and state in ("reg:visibility",):
            vis = data.split(":")[2]
            await q.set_state(uid, "reg:notifications",
                              data={"visibility": vis, "notifications_selected": []})
            await event.edit(MSG_NOTIFICATIONS, parse_mode="html",
                             buttons=kb_notifications(set()))
            return

        # ── Step 3: Notification toggles
        if data.startswith("reg:notif:") and state == "reg:notifications":
            if data == "reg:notif:confirm":
                selected = set(wizard.get("notifications_selected", []))
                new_data = {**wizard, "notifications_selected": list(selected)}
                if "reminders" in selected:
                    await q.set_state(uid, "reg:reminder_time", data=new_data)
                    await event.edit(MSG_REMINDER_TIME, parse_mode="html",
                                     buttons=kb_reminder_time())
                else:
                    await q.set_state(uid, "reg:intention", data=new_data)
                    await event.edit(MSG_INTENTION, parse_mode="html",
                                     buttons=kb_confirm_intention())
            else:
                key = data.split(":")[2]
                selected = set(wizard.get("notifications_selected", []))
                selected.discard(key) if key in selected else selected.add(key)
                await q.update_state_data(uid, notifications_selected=list(selected))
                await event.edit(MSG_NOTIFICATIONS, parse_mode="html",
                                 buttons=kb_notifications(selected))
            return

        # ── Step 4: Reminder time
        if data.startswith("reg:time:") and state == "reg:reminder_time":
            t = data.split(":", 2)[2]
            if t == "custom":
                await q.set_state(uid, "reg:custom_time", data=wizard)
                await event.edit(MSG_CUSTOM_TIME, parse_mode="html")
            elif t == "skip":
                new_data = {**wizard, "reminder_time": None}
                await q.set_state(uid, "reg:intention", data=new_data)
                await event.edit(MSG_INTENTION, parse_mode="html",
                                 buttons=kb_confirm_intention())
            else:
                new_data = {**wizard, "reminder_time": t}
                await q.set_state(uid, "reg:intention", data=new_data)
                await event.edit(MSG_INTENTION, parse_mode="html",
                                 buttons=kb_confirm_intention())
            return

        # ── Step 5: Intention confirm → complete registration
        if data == "reg:intention:confirm" and state == "reg:intention":
            await _complete_registration(event, uid, wizard)
            return

    # ── Custom reminder time text input ──────────────────────
    @client.on(events.NewMessage())
    async def reg_text_input(event):
        if not event.is_private:
            return
        uid = event.sender_id
        state_doc = await q.get_state(uid)
        if not state_doc:
            return
        state  = state_doc["state"]
        wizard = state_doc["data"]

        if state == "reg:custom_time":
            text = event.raw_text.strip()
            if re.match(r"^\d{2}:\d{2}$", text):
                new_data = {**wizard, "reminder_time": text}
                await q.set_state(uid, "reg:intention", data=new_data)
                await event.respond(MSG_INTENTION, parse_mode="html",
                                    buttons=kb_confirm_intention())
            else:
                await event.respond(
                    "❌ Invalid format. Please use <b>HH:MM</b> — e.g. <code>21:30</code>",
                    parse_mode="html")


async def _complete_registration(event, uid, wizard):
    sender = await event.get_sender()
    notifications = {k: k in wizard.get("notifications_selected", [])
                     for k in ("tasks","endings","leaderboard","reminders")}
    user = await q.create_user(
        user_id=uid,
        username=getattr(sender,"username","") or "",
        display_name=getattr(sender,"first_name","") or "Member",
        visibility=wizard.get("visibility","anonymous"),
        notifications=notifications,
        reminder_time=wizard.get("reminder_time"),
    )
    await q.clear_state(uid)
    is_admin_user = uid == OWNER_ID or await q.is_admin(uid)
    await event.edit(
        msg_registration_complete(user),
        parse_mode="html",
        buttons=kb_member_menu(is_admin=is_admin_user)
    )
    
    # Notify owner
    from utils.messages import msg_new_user_owner
    from config import OWNER_ID
    try:
        await event.client.send_message(OWNER_ID, msg_new_user_owner(user), parse_mode="html")
    except:
        pass

    # Handle deep link after registration
    deep_link = wizard.get("deep_link")
    if deep_link and deep_link.startswith("task_"):
        task_id = deep_link.split("_", 1)[1]
        from handlers.member import show_task_view
        import asyncio
        await asyncio.sleep(1) # slight delay
        await show_task_view(event, task_id, is_new_msg=True)
