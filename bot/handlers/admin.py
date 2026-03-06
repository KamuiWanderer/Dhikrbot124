import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from telethon import events
from bson import ObjectId
import google.generativeai as genai
from config import OWNER_ID, GEMINI_API_KEY
from db import queries as q
from db.queries import ALL_PERMISSIONS, SUPER_ADMIN_DEFAULTS, ADMIN_DEFAULTS
from keyboards.builder import (
    kb_admin_main, kb_task_type, kb_duration, kb_daily_limit,
    kb_leaderboard_choice, kb_media_choice, kb_add_more_media,
    kb_task_draft_actions, kb_draft_task_actions,
    kb_manage_task, kb_extend_duration, kb_confirm_end, kb_confirm_delete,
    kb_stats_menu, kb_user_actions, kb_admin_list, kb_admin_profile,
    kb_permissions_editor, kb_add_admin_role, kb_recurring_interval,
    kb_back_admin, kb_back_tasks, kb_owner_settings,
    kb_broadcast_menu, kb_broadcast_confirm,
    kb_yes_skip_cancel, kb_skip_cancel,
    kb_dhikr_categories, kb_dhikr_subcategories, kb_dhikr_sub_subcategories,
    kb_wiz_preset_choice,
    kb_ai_suggest, kb_ai_refine,
    btn, row, markup
)
from utils.messages import (
    msg_task_preview, msg_daily_breakdown,
    msg_contributor_list, fmt_num, BROADCAST_TEMPLATES, h,
    msg_owner_concise_stats
)
from utils.announcements import (
    announce_task_published, announce_task_ended,
    announce_paused, send_manual_reminder, announce_emergency
)


def is_owner(uid):
    return uid == OWNER_ID

async def get_perms(uid):
    if is_owner(uid):
        return {p: True for p in ALL_PERMISSIONS}
    adm = await q.get_admin(uid)
    return adm.get("permissions", {}) if adm else {}

async def check_access(event):
    uid = event.sender_id
    if is_owner(uid) or await q.is_admin(uid):
        return True
    await event.answer("❌ No admin access.", alert=True)
    return False

# ── AI Helper ──────────────────────────────────────────────
async def get_ai_suggestion(section, context, prompt_type="suggest"):
    if not GEMINI_API_KEY:
        return "❌ AI not configured (GEMINI_API_KEY missing)."
    
    genai.configure(apiKey=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompts = {
        "title": "Suggest a catchy title for a Dhikr task. Context: {context}. Return ONLY the title.",
        "description": "Write a short, inspiring description for a Dhikr task. Context: {context}. Return ONLY the description.",
        "arabic": "Provide the correct Arabic text for this Dhikr: {context}. Return ONLY the Arabic text.",
        "meaning": "Provide the English meaning for this Dhikr: {context}. Return ONLY the meaning.",
        "reference": "Provide a short Hadith or Quranic reference for this Dhikr: {context}. Return ONLY the reference.",
        "reminder": "Write a short intention reminder for this Dhikr: {context}. Return ONLY the reminder."
    }
    
    base_prompt = prompts.get(section, "Suggest something for {section} based on {context}")
    
    if prompt_type == "longer":
        base_prompt += " Make it longer and more detailed."
    elif prompt_type == "shorter":
        base_prompt += " Make it very short and concise."
    
    try:
        response = await model.generate_content(base_prompt.format(section=section, context=context))
        return response.text.strip()
    except Exception as e:
        return f"❌ AI Error: {str(e)}"


    # ── Reset Verification Text Input ────────────────────────
    @client.on(events.NewMessage())
    async def reset_verify_input(event):
        if not event.is_private: return
        uid = event.sender_id
        if uid != OWNER_ID: return
        state_doc = await q.get_state(uid)
        if state_doc and state_doc["state"] == "adm:reset_verify":
            if event.raw_text.strip() == "RESET DATABASE NOW":
                await q.reset_database()
                await q.clear_state(uid)
                await event.respond("✅ <b>DATABASE RESET COMPLETE.</b>\nAll data has been wiped.", parse_mode="html")
            else:
                await event.respond("❌ Verification failed. Reset cancelled.")
                await q.clear_state(uid)

    @client.on(events.NewMessage(pattern="/resetdb"))
    async def cmd_resetdb(event):
        uid = event.sender_id
        if uid != OWNER_ID:
            return
        from keyboards.builder import kb_reset_confirm
        await event.respond(
            "🧨 <b>WARNING: DATABASE RESET</b>\n\n"
            "This will wipe ALL users, tasks, and contributions.\n"
            "This action is <b>IRREVERSIBLE</b>.\n\n"
            "Are you absolutely sure?",
            parse_mode="html",
            buttons=kb_reset_confirm()
        )

def register(client):

    @client.on(events.NewMessage(pattern="/botstats"))
    async def cmd_botstats(event):
        uid = event.sender_id
        if not is_owner(uid):
            return
        stats = await q.get_owner_concise_stats()
        await event.respond(msg_owner_concise_stats(stats), parse_mode="html")

    # ── Admin main nav ───────────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm:main"))
    async def adm_main(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        perms = await get_perms(uid)
        await event.edit("👑 <b>Admin Panel</b>", parse_mode="html",
                         buttons=kb_admin_main(perms, is_owner(uid)))

    # ═══════════════════════════════════════════════════════════
    #  TASK CREATION WIZARD
    # ═══════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"adm:task:create"))
    async def adm_task_create(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        perms = await get_perms(uid)
        if not (is_owner(uid) or perms.get("create_tasks")):
            await event.answer("❌ No permission to create tasks.", alert=True)
            return
        await q.set_state(uid, "wiz:title", data={})
        await event.edit(
            "➕ <b>Create New Task</b>\n\n"
            "<b>Step 1</b> — Enter the task title:",
            parse_mode="html",
            buttons=markup(row(btn("🗑  Cancel", "wiz:cancel", "danger")))
        )

    @client.on(events.CallbackQuery(pattern=b"wiz:.*"))
    async def wiz_callback(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        data = event.data.decode()
        state_doc = await q.get_state(uid)
        if not state_doc:
            await event.answer("Session expired. Use /admin.", alert=True)
            return
        state = state_doc["state"]
        wiz   = state_doc["data"]
        await event.answer()

        if data == "wiz:cancel":
            await q.clear_state(uid)
            perms = await get_perms(uid)
            await event.edit("🗑 Cancelled.", parse_mode="html",
                             buttons=kb_admin_main(perms, is_owner(uid)))
            return

        if data == "wiz:skip":
            await _wiz_next(event, uid, state, wiz)
            return

        if data == "wiz:yes":
            await _wiz_yes(event, uid, state, wiz)
            return

        # ── AI Suggestions ───────────────────────────────────
        if data.startswith("wiz:ai:"):
            parts = data.split(":")
            action = parts[2]
            section = parts[3]
            
            context = wiz.get("dhikr_text") or wiz.get("title") or "Dhikr"
            
            if action == "suggest":
                await event.edit(f"🤖 <b>AI is thinking for {section}...</b>", parse_mode="html")
                suggestion = await get_ai_suggestion(section, context)
                wiz[f"ai_{section}_temp"] = suggestion
                await event.edit(
                    f"🤖 <b>AI Suggestion for {section}:</b>\n\n{h(suggestion)}",
                    parse_mode="html",
                    buttons=kb_ai_refine(section)
                )
                await q.update_state_data(uid, **{f"ai_{section}_temp": suggestion})
                return
            
            elif action == "use":
                suggestion = wiz.get(f"ai_{section}_temp")
                if suggestion:
                    wiz[section] = suggestion
                    await _wiz_next(event, uid, state, wiz)
                return
            
            elif action in ("longer", "shorter"):
                await event.edit(f"🤖 <b>AI is refining {section}...</b>", parse_mode="html")
                suggestion = await get_ai_suggestion(section, context, prompt_type=action)
                wiz[f"ai_{section}_temp"] = suggestion
                await event.edit(
                    f"🤖 <b>AI Suggestion ({action}) for {section}:</b>\n\n{h(suggestion)}",
                    parse_mode="html",
                    buttons=kb_ai_refine(section)
                )
                await q.update_state_data(uid, **{f"ai_{section}_temp": suggestion})
                return

        # Dhikr Categories
        if data == "wiz:dhikr":
            from constants import get_category_list
            await q.set_state(uid, "wiz:cat", data=wiz)
            await event.edit("<b>Step 2</b> — Select Dhikr Category:",
                             parse_mode="html", buttons=kb_dhikr_categories(get_category_list()))
            return

        if data.startswith("wiz:cat:"):
            cat = data.split(":", 2)[2]
            wiz["category"] = cat
            from constants import get_subcategory_list
            subcats = get_subcategory_list(cat)
            if not subcats:
                wiz["dhikr_text"] = cat
                await q.set_state(uid, "wiz:description", data=wiz)
                await event.edit("<b>Step 3</b> — Add a description? (optional)",
                                 parse_mode="html", buttons=kb_yes_skip_cancel())
            else:
                await q.set_state(uid, "wiz:sub", data=wiz)
                await event.edit(f"<b>Step 2.1</b> — Select subcategory for {cat}:",
                                 parse_mode="html", buttons=kb_dhikr_subcategories(subcats))
            return

        if data.startswith("wiz:sub:"):
            sub = data.split(":", 2)[2]
            wiz["subcategory"] = sub
            from constants import get_sub_subcategory_list
            ssubs = get_sub_subcategory_list(wiz["category"], sub)
            if not ssubs:
                wiz["dhikr_text"] = sub
                await q.set_state(uid, "wiz:description", data=wiz)
                await event.edit("<b>Step 3</b> — Add a description? (optional)",
                                 parse_mode="html", buttons=kb_yes_skip_cancel())
            else:
                await q.set_state(uid, "wiz:ssub", data=wiz)
                await event.edit(f"<b>Step 2.2</b> — Select specific type for {sub}:",
                                 parse_mode="html", buttons=kb_dhikr_sub_subcategories(ssubs))
            return

        if data.startswith("wiz:ssub:"):
            ssub = data.split(":", 2)[2]
            wiz["sub_subcategory"] = ssub
            if ssub == "Custom Dhikr":
                await q.set_state(uid, "wiz:dhikr_custom", data=wiz)
                await event.edit("✍️ Enter the <b>Custom Dhikr</b> text:",
                                 parse_mode="html", buttons=markup(row(btn("🗑 Cancel", "wiz:cancel", "danger"))))
            else:
                wiz["dhikr_text"] = ssub
                from constants import DHIKR_PRESETS
                if ssub in DHIKR_PRESETS:
                    await q.set_state(uid, "wiz:preset_choice", data=wiz)
                    await event.edit(f"✨ <b>Predefined data found for {h(ssub)}</b>\n\nWould you like to use the predefined Arabic text, meaning, and description?",
                                     parse_mode="html", buttons=kb_wiz_preset_choice())
                else:
                    await q.set_state(uid, "wiz:description", data=wiz)
                    await event.edit("<b>Step 3</b> — Add a description? (optional)",
                                     parse_mode="html", buttons=kb_yes_skip_cancel())
            return

        if data == "wiz:preset:use":
            from constants import DHIKR_PRESETS
            preset = DHIKR_PRESETS.get(wiz["sub_subcategory"])
            if preset:
                wiz["arabic"] = preset.get("arabic")
                wiz["meaning"] = preset.get("meaning")
                wiz["description"] = preset.get("description")
                wiz["reference"] = preset.get("reference")
                wiz["intention_reminder"] = preset.get("reminder")
            
            await q.set_state(uid, "wiz:type", data=wiz)
            await event.edit("<b>Step 7</b> — Choose task type:",
                             parse_mode="html", buttons=kb_task_type())
            return

        if data == "wiz:preset:custom":
            await q.set_state(uid, "wiz:description", data=wiz)
            await event.edit("<b>Step 3</b> — Add a description? (optional)",
                             parse_mode="html", buttons=kb_yes_skip_cancel())
            return

        # Task type
        if data.startswith("wiz:type:"):
            t = data.split(":")[2]
            wiz["type"] = t
            await q.update_state_data(uid, type=t)
            if t == "emergency":
                wiz["leaderboard_visible"] = False
                await q.set_state(uid, "wiz:preview", data={**wiz})
                await event.edit(msg_task_preview(wiz), parse_mode="html",
                                 buttons=kb_task_draft_actions())
                return
            if t == "count":
                await q.set_state(uid, "wiz:target", data=wiz)
                await event.edit(
                    "<b>Step 8</b> — Enter the target count:\n<i>e.g. <code>100000</code></i>",
                    parse_mode="html",
                    buttons=markup(row(btn("🗑 Cancel", "wiz:cancel", "danger")))
                )
            elif t == "recurring":
                await q.set_state(uid, "wiz:recurring_interval", data=wiz)
                await event.edit("<b>Step 8</b> — Choose recurring interval:",
                                 parse_mode="html", buttons=kb_recurring_interval())
            else:
                await q.set_state(uid, "wiz:duration", data=wiz)
                await event.edit("<b>Step 9</b> — Choose task duration:",
                                 parse_mode="html", buttons=kb_duration())
            return

        if data.startswith("wiz:recur:"):
            interval = data.split(":")[2]
            wiz["recurring_interval"] = interval
            await q.set_state(uid, "wiz:duration", data=wiz)
            await event.edit("<b>Step 9</b> — Choose duration per cycle:",
                             parse_mode="html", buttons=kb_duration())
            return

        if data.startswith("wiz:dur:"):
            dur = data.split(":")[2]
            if dur == "custom":
                await q.set_state(uid, "wiz:custom_duration", data=wiz)
                await event.edit(
                    "✍️ Enter duration in hours (e.g. <code>48</code>) "
                    "or a specific date (<code>2025-12-31 20:00</code>):",
                    parse_mode="html",
                    buttons=markup(row(btn("🗑 Cancel", "wiz:cancel", "danger")))
                )
                return
            if dur == "skip":
                wiz["ends_at"] = None
            else:
                ends_at = datetime.utcnow() + timedelta(hours=int(dur))
                wiz["ends_at"] = ends_at.isoformat()
            await q.set_state(uid, "wiz:daily_limit", data=wiz)
            await event.edit("<b>Step 10</b> — Set a daily per-user limit?",
                             parse_mode="html", buttons=kb_daily_limit())
            return

        if data == "wiz:limit:yes":
            await q.set_state(uid, "wiz:limit_value", data=wiz)
            await event.edit("✍️ Enter max count per person per day:",
                             parse_mode="html",
                             buttons=markup(row(btn("🗑 Cancel", "wiz:cancel", "danger"))))
            return

        if data == "wiz:limit:no":
            wiz["daily_limit_per_user"] = None
            await q.set_state(uid, "wiz:leaderboard", data=wiz)
            await event.edit("<b>Step 11</b> — Leaderboard settings:",
                             parse_mode="html", buttons=kb_leaderboard_choice())
            return

        if data.startswith("wiz:lb:"):
            lb = data.split(":")[2] == "yes"
            wiz["leaderboard_visible"] = lb
            await q.set_state(uid, "wiz:media", data=wiz)
            await event.edit("<b>Step 12</b> — Add media? (optional)",
                             parse_mode="html", buttons=kb_media_choice())
            return

        if data.startswith("wiz:media:"):
            action = data.split(":")[2]
            if action == "done":
                await q.set_state(uid, "wiz:preview", data=wiz)
                await event.edit(msg_task_preview(wiz), parse_mode="html",
                                 buttons=kb_task_draft_actions())
                return
            if action == "more":
                await event.edit("Add another media item:",
                                 parse_mode="html", buttons=kb_media_choice())
                return
            prompts = {
                "image":   "📷 Send the image now:",
                "video":   "🎥 Send the video file now:",
                "audio":   "🎙 Send the audio file now:",
                "youtube": "🔗 Paste the YouTube URL:",
            }
            await q.set_state(uid, f"wiz:media_upload:{action}", data=wiz)
            await event.edit(prompts.get(action, "Send the file:"),
                             parse_mode="html",
                             buttons=markup(row(btn("⏭ Skip", "wiz:media:done", "primary"))))
            return

        if data == "wiz:savedraft":
            await _save_draft(event, uid, wiz, client)
            return

        if data == "wiz:publish":
            await _publish_task(event, uid, wiz, client, activate=True)
            return

        if data == "wiz:edit":
            await q.set_state(uid, "wiz:title", data=wiz)
            await event.edit(
                f"➕ <b>Edit Task</b>\n\n<b>Step 1</b> — Enter title:\n<i>Current: {h(wiz.get('title','—'))}</i>",
                parse_mode="html",
                buttons=markup(row(btn("🗑 Cancel", "wiz:cancel", "danger")))
            )
            return

    # ── Wizard text inputs ───────────────────────────────────
    @client.on(events.NewMessage())
    async def wiz_text_input(event):
        if not event.is_private:
            return
        uid = event.sender_id
        if not (is_owner(uid) or await q.is_admin(uid)):
            return
        state_doc = await q.get_state(uid)
        if not state_doc or not state_doc["state"].startswith("wiz:"):
            return
        state = state_doc["state"]
        wiz   = state_doc["data"]
        text  = event.raw_text.strip()

        if state == "wiz:title":
            wiz["title"] = text
            from constants import get_category_list
            await q.set_state(uid, "wiz:cat", data=wiz)
            await event.respond(
                "<b>Step 2</b> — Select Dhikr Category:",
                parse_mode="html",
                buttons=kb_dhikr_categories(get_category_list())
            )

        elif state == "wiz:dhikr_custom":
            wiz["dhikr_text"] = text
            await q.set_state(uid, "wiz:description", data=wiz)
            await event.respond("<b>Step 3</b> — Add a description? (optional)",
                                parse_mode="html", buttons=kb_ai_suggest("description"))

        elif state == "wiz:description_text":
            wiz["description"] = text
            await q.set_state(uid, "wiz:arabic", data=wiz)
            await event.respond("<b>Step 3.1</b> — Add Arabic text? (optional)",
                                parse_mode="html", buttons=kb_ai_suggest("arabic"))

        elif state == "wiz:arabic_text":
            wiz["arabic"] = text
            await q.set_state(uid, "wiz:meaning", data=wiz)
            await event.respond("<b>Step 3.2</b> — Add English meaning? (optional)",
                                parse_mode="html", buttons=kb_ai_suggest("meaning"))

        elif state == "wiz:meaning_text":
            wiz["meaning"] = text
            await q.set_state(uid, "wiz:reference", data=wiz)
            await event.respond("<b>Step 4</b> — Add a reference (Hadith/Ayah)? (optional)",
                                parse_mode="html", buttons=kb_ai_suggest("reference"))

        elif state == "wiz:reference_text":
            wiz["reference"] = text
            await q.set_state(uid, "wiz:intention", data=wiz)
            await event.respond("<b>Step 5</b> — Add an intention reminder? (optional)",
                                parse_mode="html", buttons=kb_ai_suggest("reminder"))

        elif state == "wiz:intention_text":
            wiz["intention_reminder"] = text
            await q.set_state(uid, "wiz:type", data=wiz)
            await event.respond("<b>Step 7</b> — Choose task type:",
                                parse_mode="html", buttons=kb_task_type())

        elif state == "wiz:target":
            if not text.isdigit() or int(text) <= 0:
                await event.respond("❌ Please enter a valid positive number.", parse_mode="html")
                return
            wiz["target"] = int(text)
            await q.set_state(uid, "wiz:duration", data=wiz)
            await event.respond("<b>Step 9</b> — Choose task duration:",
                                parse_mode="html", buttons=kb_duration())

        elif state == "wiz:custom_duration":
            try:
                if text.isdigit():
                    ends_at = datetime.utcnow() + timedelta(hours=int(text))
                else:
                    ends_at = datetime.strptime(text, "%Y-%m-%d %H:%M")
                wiz["ends_at"] = ends_at.isoformat()
                await q.set_state(uid, "wiz:daily_limit", data=wiz)
                await event.respond("<b>Step 10</b> — Set a daily per-user limit?",
                                    parse_mode="html", buttons=kb_daily_limit())
            except ValueError:
                await event.respond(
                    "❌ Invalid. Use hours e.g. <code>48</code> or date <code>YYYY-MM-DD HH:MM</code>",
                    parse_mode="html")

        elif state == "wiz:limit_value":
            if not text.isdigit() or int(text) <= 0:
                await event.respond("❌ Please enter a valid positive number.", parse_mode="html")
                return
            wiz["daily_limit_per_user"] = int(text)
            await q.set_state(uid, "wiz:leaderboard", data=wiz)
            await event.respond("<b>Step 11</b> — Leaderboard settings:",
                                parse_mode="html", buttons=kb_leaderboard_choice())

        elif state.startswith("wiz:media_upload:"):
            media_type = state.split(":")[2]
            if media_type == "youtube":
                media_list = wiz.get("media", [])
                media_list.append({"type": "youtube", "url": text, "title": "YouTube Video"})
                wiz["media"] = media_list
                await q.set_state(uid, "wiz:media", data=wiz)
                await event.respond("✅ YouTube link added!",
                                    parse_mode="html", buttons=kb_add_more_media())

        elif state == "adm:admins:getuser":
            target_username = text.lstrip("@")
            role = wiz.get("new_role", "admin")
            try:
                target = await client.get_entity(target_username)
                defaults = SUPER_ADMIN_DEFAULTS if role == "super_admin" else ADMIN_DEFAULTS
                await q.create_admin(target.id, role, defaults.copy(), uid)
                await event.respond(
                    f"✅ <b>@{h(target_username)}</b> added as <b>{role.replace('_',' ').title()}</b>!",
                    parse_mode="html",
                    buttons=markup(row(btn("👑 Manage Admins", "adm:admins:list", "primary")))
                )
            except Exception as e:
                await event.respond(f"❌ Couldn't find user: {h(str(e))}", parse_mode="html")
            await q.clear_state(uid)

        elif state == "adm:task:remind_text":
            task_id = wiz.get("task_id")
            custom_text = wiz.get("custom_text", text)
            task = await q.get_task(task_id)
            if task:
                await send_manual_reminder(client, task, text)
                await event.respond(
                    "✅ Reminder sent to group and opted-in members!",
                    parse_mode="html",
                    buttons=kb_manage_task(task, await get_perms(uid), is_owner(uid))
                )
            await q.clear_state(uid)

        elif state == "adm:task:editdesc_text":
            task_id = wiz.get("task_id")
            await q.update_task(task_id, description=text)
            task = await q.get_task(task_id)
            await event.respond("✅ Description updated!", parse_mode="html",
                                buttons=kb_manage_task(task, await get_perms(uid), is_owner(uid)))
            await q.clear_state(uid)

        elif state == "adm:task:extend_custom":
            task_id = wiz.get("task_id")
            if text.isdigit():
                hours = int(text)
                task = await q.get_task(task_id)
                current_end = task.get("ends_at") or datetime.utcnow()
                new_end = current_end + timedelta(hours=hours)
                await q.update_task(task_id, ends_at=new_end)
                await event.respond(
                    f"✅ Extended by <b>{hours}h</b>. New end: <code>{new_end.strftime('%d %b %Y %H:%M')} UTC</code>",
                    parse_mode="html", buttons=kb_back_tasks()
                )
            else:
                await event.respond("❌ Please enter a number of hours.", parse_mode="html")
            await q.clear_state(uid)

        elif state == "adm:broadcast:custom_text":
            wiz["custom_text"] = text
            await q.update_state_data(uid, custom_text=text)
            await event.respond(
                f"📋 <b>Preview your broadcast:</b>\n\n{text}\n\n<i>Choose who to send to:</i>",
                parse_mode="html",
                buttons=markup(
                    row(btn("📢  Send to ALL",          "bc:send:all:custom",   "danger")),
                    row(btn("🔔  Send to opted-in only", "bc:send:opted:custom", "success")),
                    row(btn("❌  Cancel",                "adm:broadcast",        "primary")),
                )
            )

    # ── Wizard media file upload ─────────────────────────────
    @client.on(events.NewMessage())
    async def wiz_media_upload(event):
        if not event.is_private:
            return
        uid = event.sender_id
        state_doc = await q.get_state(uid)
        if not state_doc:
            return
        state = state_doc["state"]
        wiz   = state_doc["data"]
        if not state.startswith("wiz:media_upload:"):
            return
        media_type = state.split(":")[2]
        if media_type == "youtube":
            return
        if not (event.photo or event.video or event.audio or event.voice or event.document):
            return
        
        # Extract serializable media reference
        file_id = None
        if event.photo:
            file_id = event.photo
        elif event.video:
            file_id = event.video
        elif event.audio:
            file_id = event.audio
        elif event.voice:
            file_id = event.voice
        elif event.document:
            file_id = event.document

        media_list = wiz.get("media", [])
        media_list.append({"type": media_type, "file_id": file_id})
        wiz["media"] = media_list
        # We store the wiz data in FSM state. MongoDB can't encode Telethon objects.
        # However, Telethon objects are needed for client.send_file.
        # To fix this, we'll store a placeholder or a serialized version if needed, 
        # but for now let's just ensure we don't store the raw object if it's causing issues.
        # Actually, the error was bson.errors.InvalidDocument.
        # I'll use a helper to make it serializable for the DB but keep the object for the session if possible.
        # But FSM state is in DB. So I MUST serialize it.
        
        # For now, let's just store the file_id if it's a string, or the whole object if we can serialize it.
        # Telethon objects are not easily serializable.
        # Let's just store the message ID and chat ID to re-fetch if needed, or use pack_bot_file_id.
        from telethon.utils import pack_bot_file_id
        packed_id = pack_bot_file_id(file_id)
        
        media_list[-1]["file_id"] = packed_id
        wiz["media"] = media_list
        
        await q.set_state(uid, "wiz:media", data=wiz)
        await event.respond(f"✅ {media_type.title()} added!",
                            parse_mode="html", buttons=kb_add_more_media())

    # ═══════════════════════════════════════════════════════════
    #  TASK LISTS — DRAFT + ACTIVE
    # ═══════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"adm:tasks:.*"))
    async def adm_tasks(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        data = event.data.decode()
        parts = data.split(":")
        action = parts[2]
        await event.answer()

        if action == "draft":
            tasks_list = await q.get_tasks_by_status("draft")
            if not tasks_list:
                await event.edit(
                    "💾 No draft tasks.\n\n<i>Create a task and save as draft to see it here.</i>",
                    parse_mode="html", buttons=kb_back_admin()
                )
                return
            rows_btns = [row(btn(f"💾 {t['title']}", f"adm:task:viewdraft:{str(t['_id'])}", "primary"))
                         for t in tasks_list]
            rows_btns.append(row(btn("⬅️ Back", "adm:main", "primary")))
            await event.edit("💾 <b>Draft Tasks</b>:", parse_mode="html",
                             buttons=markup(*rows_btns))

        elif action == "active":
            tasks_list = await q.get_active_tasks()
            if not tasks_list:
                await event.edit("📋 No active tasks.", parse_mode="html",
                                 buttons=kb_back_admin())
                return
            rows_btns = [row(btn(
                f"{'⏸' if t['status']=='paused' else '🟢'} {t['title']}",
                f"adm:task:manage:{str(t['_id'])}", "primary")) for t in tasks_list]
            rows_btns.append(row(btn("⬅️ Back", "adm:main", "primary")))
            await event.edit("✅ <b>Active Tasks</b>:", parse_mode="html",
                             buttons=markup(*rows_btns))

        elif action == "ended":
            tasks_list = await q.get_tasks_by_status("ended")
            if not tasks_list:
                await event.edit("📁 No archived tasks.", parse_mode="html",
                                 buttons=kb_back_admin())
                return
            rows_btns = [row(btn(
                f"🔴 {t['title']} — {fmt_num(t.get('total_count',0))}",
                f"adm:task:archived:{str(t['_id'])}", "primary")) for t in tasks_list[:20]]
            rows_btns.append(row(btn("⬅️ Back", "adm:main", "primary")))
            await event.edit("📁 <b>Archived Tasks</b>:", parse_mode="html",
                             buttons=markup(*rows_btns))

    # ═══════════════════════════════════════════════════════════
    #  TASK ACTIONS
    # ═══════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"adm:task:.*"))
    async def adm_task_actions(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        data = event.data.decode()
        parts = data.split(":")
        action  = parts[2] if len(parts) > 2 else ""
        task_id = parts[3] if len(parts) > 3 else None
        perms = await get_perms(uid)
        await event.answer()

        if action == "viewdraft" and task_id:
            task = await q.get_task(task_id)
            if not task:
                return
            await event.edit(msg_task_preview(task), parse_mode="html",
                             buttons=kb_draft_task_actions(task_id))

        elif action == "activate" and task_id:
            # Enforce one active task at a time
            active_tasks = await q.get_active_tasks()
            if active_tasks:
                names = ", ".join(f"<b>{h(t['title'])}</b>" for t in active_tasks)
                await event.edit(
                    f"⚠️ There is already an active task: {names}\n\n"
                    f"Please end or pause it before activating a new one.",
                    parse_mode="html",
                    buttons=markup(
                        row(btn("📋 View Active Task", "adm:tasks:active", "primary")),
                        row(btn("⬅️ Back to Drafts",  "adm:tasks:draft",  "primary")),
                    )
                )
                return
            task = await q.get_task(task_id)
            await q.update_task(task_id, status="active", starts_at=datetime.utcnow())
            task["status"] = "active"
            await announce_task_published(client, task)
            await event.edit(
                f"🚀 <b>{h(task['title'])}</b> is now live! Announcement sent to group.",
                parse_mode="html",
                buttons=kb_manage_task(task, perms, is_owner(uid))
            )

        elif action == "manage" and task_id:
            task = await q.get_task(task_id)
            if not task:
                await event.edit("❌ Task not found.", parse_mode="html",
                                 buttons=kb_back_tasks())
                return
            await event.edit(
                f"⚙️ <b>Manage: {h(task['title'])}</b>\n"
                f"Status: {'⏸ Paused' if task['status']=='paused' else '🟢 Active'}\n"
                f"Total: <b>{fmt_num(task.get('total_count',0))}</b>",
                parse_mode="html",
                buttons=kb_manage_task(task, perms, is_owner(uid))
            )

        elif action == "archived" and task_id:
            task = await q.get_task(task_id)
            if not task:
                return
            await event.edit(
                f"📁 <b>Archived: {h(task['title'])}</b>\n\n"
                f"Final count: <b>{fmt_num(task.get('total_count',0))}</b>",
                parse_mode="html",
                buttons=markup(row(btn("⬅️ Back", "adm:tasks:ended", "primary")))
            )

        elif action == "pause" and task_id:
            await q.update_task(task_id, status="paused")
            task = await q.get_task(task_id)
            await announce_paused(client, task, True)
            await event.edit(f"⏸ <b>{h(task['title'])}</b> paused.", parse_mode="html",
                             buttons=kb_manage_task(task, perms, is_owner(uid)))

        elif action == "resume" and task_id:
            await q.update_task(task_id, status="active")
            task = await q.get_task(task_id)
            await announce_paused(client, task, False)
            await event.edit(f"▶️ <b>{h(task['title'])}</b> resumed.", parse_mode="html",
                             buttons=kb_manage_task(task, perms, is_owner(uid)))

        elif action == "end" and task_id:
            task = await q.get_task(task_id)
            await event.edit(
                f"⚠️ <b>End task early?</b>\n\n{h(task['title'])}\n"
                f"Current count: <b>{fmt_num(task.get('total_count',0))}</b>",
                parse_mode="html", buttons=kb_confirm_end(task_id)
            )

        elif action == "endconfirm" and task_id:
            task = await q.get_task(task_id)
            await q.end_task(task_id)
            await announce_task_ended(client, task)
            await event.edit(
                f"🔚 <b>{h(task['title'])}</b> ended.\nFinal count: <b>{fmt_num(task.get('total_count',0))}</b>",
                parse_mode="html", buttons=kb_back_tasks()
            )

        elif action == "extend" and task_id:
            await q.set_state(uid, "adm:task:extend", data={"task_id": task_id})
            await event.edit("⏳ <b>Extend duration by:</b>", parse_mode="html",
                             buttons=kb_extend_duration())

        elif action == "togglelb" and task_id:
            task = await q.get_task(task_id)
            new_val = not task.get("leaderboard_visible", True)
            await q.update_task(task_id, leaderboard_visible=new_val)
            task["leaderboard_visible"] = new_val
            await event.edit(
                f"🏆 Leaderboard <b>{'enabled' if new_val else 'disabled'}</b> for this task.",
                parse_mode="html",
                buttons=kb_manage_task(task, perms, is_owner(uid))
            )

        elif action == "remind" and task_id:
            await q.set_state(uid, "adm:task:remind_text", data={"task_id": task_id})
            await event.edit(
                "📣 <b>Send a broadcast reminder</b>\n\n"
                "Type a custom message, or tap a template below:",
                parse_mode="html",
                buttons=markup(
                    row(btn("📢 General Reminder",  "adm:remind:tpl:general:"+task_id, "primary")),
                    row(btn("⏳ Urgent / Ending Soon","adm:remind:tpl:urgent:"+task_id, "primary")),
                    row(btn("🌙 Jumu'ah",            "adm:remind:tpl:friday:"+task_id, "primary")),
                    row(btn("✍️ Custom message",      "adm:remind:tpl:custom:"+task_id, "primary")),
                    row(btn("❌ Cancel",              "adm:tasks:active",               "danger")),
                )
            )

        elif action == "editdesc" and task_id:
            await q.set_state(uid, "adm:task:editdesc_text", data={"task_id": task_id})
            await event.edit("✏️ Enter the new description:", parse_mode="html",
                             buttons=markup(row(btn("🗑 Cancel", "adm:tasks:active", "danger"))))

        elif action == "editmedia" and task_id:
            task = await q.get_task(task_id)
            wiz_data = dict(task)
            wiz_data["_id"] = str(task["_id"])
            await q.set_state(uid, "wiz:media", data=wiz_data)
            await event.edit("📎 <b>Edit Media</b> — Add or replace media:",
                             parse_mode="html", buttons=kb_media_choice())

        elif action == "contribs" and task_id:
            task = await q.get_task(task_id)
            contrib_rows = await q.get_task_per_contributor(task_id)
            user_ids = [r["_id"] for r in contrib_rows[:20]]
            users_map = {}
            for uid2 in user_ids:
                u = await q.get_user(uid2)
                if u:
                    users_map[uid2] = u
            text = msg_contributor_list(task["title"], contrib_rows[:20], users_map)
            rm_btns = []
            if is_owner(uid) or perms.get("remove_contributions"):
                rm_btns = [row(btn(
                    f"🗑 Remove: {h(users_map.get(r['_id'],{}).get('username','ID:'+str(r['_id'])))}",
                    f"adm:task:removecontrib:{task_id}:{r['_id']}", "danger"
                )) for r in contrib_rows[:10]]
            rm_btns.append(row(btn("⬅️ Back", f"adm:task:manage:{task_id}", "primary")))
            await event.edit(text, parse_mode="html", buttons=markup(*rm_btns))

        elif action == "removecontrib" and task_id:
            target_uid = int(parts[4]) if len(parts) > 4 else None
            if target_uid:
                await q.remove_user_contributions(task_id, target_uid)
                await event.answer("✅ Contributions removed.", alert=True)

        elif action == "daily" and task_id:
            task = await q.get_task(task_id)
            rows_data = await q.get_daily_breakdown(task_id)
            text = msg_daily_breakdown(task["title"], rows_data)
            await event.edit(text, parse_mode="html",
                             buttons=markup(row(btn("⬅️ Back", f"adm:task:manage:{task_id}", "primary"))))

        elif action == "delete" and task_id:
            await event.edit("⚠️ <b>Delete this task permanently?</b>\nThis cannot be undone.",
                             parse_mode="html", buttons=kb_confirm_delete(task_id))

        elif action == "deleteconfirm" and task_id:
            from db.models import tasks as tasks_col, contributions as contrib_col
            oid = ObjectId(task_id)
            await tasks_col().delete_one({"_id": oid})
            await contrib_col().delete_many({"task_id": oid})
            await event.edit("🗑 Task deleted.", parse_mode="html", buttons=kb_back_tasks())

    # ── Reminder templates ───────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"adm:remind:tpl:.*"))
    async def remind_template(event):
        if not await check_access(event):
            return
        data = event.data.decode()
        parts = data.split(":")
        template_key = parts[3]
        task_id      = parts[4] if len(parts) > 4 else None
        uid = event.sender_id
        await event.answer()

        if template_key == "custom":
            await q.set_state(uid, "adm:task:remind_text", data={"task_id": task_id})
            await event.edit("✍️ Type your custom reminder message:",
                             parse_mode="html",
                             buttons=markup(row(btn("❌ Cancel", "adm:tasks:active", "danger"))))
            return

        text = BROADCAST_TEMPLATES.get(template_key, "")
        if task_id:
            task = await q.get_task(task_id)
            if task and text:
                await send_manual_reminder(client, task, text)
                await event.edit(
                    f"✅ <b>Reminder sent!</b>\n\n{text}",
                    parse_mode="html",
                    buttons=kb_manage_task(task, await get_perms(uid), is_owner(uid))
                )
        await q.clear_state(uid)

    # ── Extension callbacks ──────────────────────────────────
    @client.on(events.CallbackQuery(pattern=b"ext:.*"))
    async def ext_callback(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        data = event.data.decode()
        state_doc = await q.get_state(uid)
        if not state_doc:
            return
        wiz = state_doc["data"]
        task_id = wiz.get("task_id")
        await event.answer()

        if data == "ext:cancel":
            await q.clear_state(uid)
            task = await q.get_task(task_id)
            await event.edit("Cancelled.", parse_mode="html",
                             buttons=kb_manage_task(task, await get_perms(uid), is_owner(uid)))
            return
        if data == "ext:custom":
            await q.set_state(uid, "adm:task:extend_custom", data=wiz)
            await event.edit("✍️ Enter number of hours to extend by:",
                             parse_mode="html",
                             buttons=markup(row(btn("🗑 Cancel", "ext:cancel", "danger"))))
            return
        hours = int(data.split(":")[1])
        task = await q.get_task(task_id)
        current_end = task.get("ends_at") or datetime.utcnow()
        new_end = current_end + timedelta(hours=hours)
        await q.update_task(task_id, ends_at=new_end)
        await q.clear_state(uid)
        task = await q.get_task(task_id)
        await event.edit(
            f"✅ Extended by <b>{hours}h</b>. New end: <code>{new_end.strftime('%d %b %Y %H:%M')} UTC</code>",
            parse_mode="html",
            buttons=kb_manage_task(task, await get_perms(uid), is_owner(uid))
        )

    # ═══════════════════════════════════════════════════════════
    #  BROADCAST
    # ═══════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"adm:broadcast"))
    async def adm_broadcast(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        perms = await get_perms(uid)
        if not (is_owner(uid) or perms.get("send_announcements") or perms.get("dm_blast")):
            await event.answer("❌ No permission.", alert=True)
            return
        await event.answer()
        await event.edit("📣 <b>Broadcast</b>\n\nChoose a message template:",
                         parse_mode="html", buttons=kb_broadcast_menu())

    @client.on(events.CallbackQuery(pattern=b"bc:.*"))
    async def bc_callback(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        data = event.data.decode()
        parts = data.split(":")
        action = parts[1]
        await event.answer()

        if action == "template":
            key = parts[2]
            if key == "custom":
                await q.set_state(uid, "adm:broadcast:custom_text", data={})
                await event.edit("✍️ <b>Custom Broadcast</b>\n\nType your message:",
                                 parse_mode="html",
                                 buttons=markup(row(btn("❌ Cancel", "adm:broadcast", "primary"))))
                return
            text = BROADCAST_TEMPLATES.get(key, "")
            await event.edit(
                f"📋 <b>Preview:</b>\n\n{text}\n\n<i>Choose recipients:</i>",
                parse_mode="html",
                buttons=kb_broadcast_confirm(key)
            )

        elif action == "edit":
            key = parts[2]
            await q.set_state(uid, "adm:broadcast:custom_text", data={"original_key": key})
            await event.edit("✍️ Edit your message:", parse_mode="html",
                             buttons=markup(row(btn("❌ Cancel", "adm:broadcast", "primary"))))

        elif action == "send":
            audience = parts[2]   # "all" or "opted"
            key      = parts[3]
            # Get text
            if key == "custom":
                state_doc = await q.get_state(uid)
                text = (state_doc["data"].get("custom_text","") if state_doc else "") or ""
            else:
                text = BROADCAST_TEMPLATES.get(key, "")

            if not text:
                await event.answer("No message to send.", alert=True)
                return

            if audience == "all":
                users_list = await q.get_all_users()
            else:
                users_list = await q.get_users_with_notif("tasks")

            uids = [u["user_id"] for u in users_list]
            from utils.announcements import dm_users
            import asyncio
            await event.edit(
                f"📢 Sending to <b>{len(uids)}</b> member(s)…\n<i>Please wait, this may take a while.</i>",
                parse_mode="html"
            )
            sent, blocked, failed = await dm_users(client, uids, text)
            await q.clear_state(uid)
            
            # Detailed report
            report_text = (
                f"✅ <b>Broadcast Finished</b>\n\n"
                f"👥 Total: <b>{len(uids)}</b>\n"
                f"✅ Sent: <b>{sent}</b>\n"
                f"🚫 Blocked: <b>{blocked}</b>\n"
                f"❌ Failed: <b>{failed}</b>"
            )
            if failed > 0:
                report_text += "\n\n<i>Note: Failed messages are usually due to network errors or Telegram restrictions.</i>"
            if blocked > 0:
                report_text += "\n\n<i>Note: Blocked users have either blocked the bot or deleted their accounts.</i>"
                
            await event.edit(
                report_text,
                parse_mode="html",
                buttons=kb_back_admin()
            )

    # ═══════════════════════════════════════════════════════════
    #  STATS
    # ═══════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"adm:stats.*"))
    async def adm_stats(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        data = event.data.decode()
        perms = await get_perms(uid)
        await event.answer()

        if data == "adm:stats":
            await event.edit("📊 <b>Statistics</b>", parse_mode="html",
                             buttons=kb_stats_menu(is_owner(uid), perms))

        elif data == "adm:stats:grand":
            grand   = await q.get_grand_total()
            members = await q.get_user_count()
            ended   = await q.get_tasks_by_status("ended")
            await event.edit(
                f"🌍 <b>Grand Total Stats</b>\n\n"
                f"Total dhikr ever: <b>{fmt_num(grand)}</b>\n"
                f"Registered members: <b>{fmt_num(members)}</b>\n"
                f"Completed tasks: <b>{len(ended)}</b>",
                parse_mode="html",
                buttons=markup(row(btn("⬅️ Back", "adm:stats", "primary")))
            )

        elif data == "adm:stats:yearly":
            y = await q.get_yearly_total()
            await event.edit(f"📅 <b>This Year:</b> {fmt_num(y)} dhikr", parse_mode="html",
                             buttons=markup(row(btn("⬅️ Back", "adm:stats", "primary"))))

        elif data == "adm:stats:monthly":
            m = await q.get_monthly_total()
            await event.edit(f"🗓 <b>This Month:</b> {fmt_num(m)} dhikr", parse_mode="html",
                             buttons=markup(row(btn("⬅️ Back", "adm:stats", "primary"))))

        elif data == "adm:stats:daily":
            d = await q.get_daily_total()
            await event.edit(f"☀️ <b>Today:</b> {fmt_num(d)} dhikr", parse_mode="html",
                             buttons=markup(row(btn("⬅️ Back", "adm:stats", "primary"))))

        elif data == "adm:stats:pertask":
            all_tasks = await q.get_active_tasks()
            ended = await q.get_tasks_by_status("ended")
            combined = all_tasks + ended
            if not combined:
                await event.edit("No tasks yet.", parse_mode="html",
                                 buttons=markup(row(btn("⬅️ Back", "adm:stats", "primary"))))
                return
            lines = ["📋 <b>Per-Task Breakdown</b>\n"]
            for t in combined[:20]:
                lines.append(f"• <b>{h(t['title'])}</b>: {fmt_num(t.get('total_count',0))} — {t['status']}")
            await event.edit("\n".join(lines), parse_mode="html",
                             buttons=markup(row(btn("⬅️ Back", "adm:stats", "primary"))))

        elif data == "adm:stats:export":
            from datetime import date
            import io
            grand   = await q.get_grand_total()
            yearly  = await q.get_yearly_total()
            monthly = await q.get_monthly_total()
            daily   = await q.get_daily_total()
            members = await q.get_user_count()
            report = (
                f"DHIKR BOT — STATS EXPORT\n"
                f"Generated: {date.today().isoformat()}\n"
                f"{'='*40}\n"
                f"Grand Total:  {grand:,}\n"
                f"This Year:    {yearly:,}\n"
                f"This Month:   {monthly:,}\n"
                f"Today:        {daily:,}\n"
                f"Members:      {members:,}\n"
            )
            buf = io.BytesIO(report.encode())
            buf.name = f"dhikr_stats_{date.today().isoformat()}.txt"
            await client.send_file(uid, buf, caption="📊 Stats Export")
            await event.answer("✅ Report sent to your DM.", alert=True)

    # ═══════════════════════════════════════════════════════════
    #  USERS
    # ═══════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"adm:users:.*"))
    async def adm_users(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        perms = await get_perms(uid)
        await event.answer()

        all_users = await q.get_all_users(skip_banned=False)
        total  = len(all_users)
        banned = sum(1 for u in all_users if u.get("is_banned"))
        rows_btns = []
        for u in all_users[:30]:
            name = u.get("username") or u.get("display_name") or str(u["user_id"])
            icon = "🚫" if u.get("is_banned") else "👤"
            rows_btns.append(row(btn(f"{icon} {name}", f"adm:user:view:{u['user_id']}", "primary")))
        rows_btns.append(row(btn("⬅️ Back", "adm:main", "primary")))
        await event.edit(
            f"👥 <b>Users</b> — Total: {total} | Banned: {banned}",
            parse_mode="html", buttons=markup(*rows_btns)
        )

    @client.on(events.CallbackQuery(pattern=b"adm:user:.*"))
    async def adm_user_actions(event):
        if not await check_access(event):
            return
        uid = event.sender_id
        data = event.data.decode()
        parts = data.split(":")
        action = parts[2]
        target_uid = int(parts[3]) if len(parts) > 3 else None
        perms = await get_perms(uid)
        await event.answer()

        if action == "view" and target_uid:
            u = await q.get_user(target_uid)
            if not u:
                await event.answer("User not found.", alert=True)
                return
            name = u.get("username") or u.get("display_name") or str(target_uid)
            await event.edit(
                f"👤 <b>{h(name)}</b>\n"
                f"ID: <code>{target_uid}</code>\n"
                f"Visibility: {u.get('visibility','—')}\n"
                f"Lifetime count: <b>{fmt_num(u.get('lifetime_count',0))}</b>\n"
                f"Streak: {u.get('streak',0)}\n"
                f"Banned: {'Yes 🚫' if u.get('is_banned') else 'No'}",
                parse_mode="html",
                buttons=kb_user_actions(target_uid, u.get("is_banned",False),
                                        is_owner(uid), perms)
            )

        elif action == "ban" and target_uid:
            await q.ban_user(target_uid)
            await event.answer(f"🚫 User {target_uid} banned.", alert=True)

        elif action == "unban" and target_uid:
            await q.unban_user(target_uid)
            await event.answer(f"✅ User {target_uid} unbanned.", alert=True)

        elif action == "contribs" and target_uid:
            from datetime import date
            today       = date.today().isoformat()
            year_start  = date.today().replace(month=1, day=1).isoformat()
            month_start = date.today().replace(day=1).isoformat()
            u_life  = (await q.get_user(target_uid) or {}).get("lifetime_count", 0)
            u_year  = await q.get_user_period_total(target_uid, year_start)
            u_month = await q.get_user_period_total(target_uid, month_start)
            u_today = await q.get_user_period_total(target_uid, today, today)
            await event.edit(
                f"📊 <b>Contributions for {target_uid}</b>\n\n"
                f"All-time: <b>{fmt_num(u_life)}</b>\n"
                f"This year: <b>{fmt_num(u_year)}</b>\n"
                f"This month: <b>{fmt_num(u_month)}</b>\n"
                f"Today: <b>{fmt_num(u_today)}</b>",
                parse_mode="html",
                buttons=markup(row(btn("⬅️ Back", f"adm:user:view:{target_uid}", "primary")))
            )

    # ═══════════════════════════════════════════════════════════
    #  ADMIN MANAGEMENT
    # ═══════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"adm:admins:.*"))
    async def adm_admins(event):
        uid = event.sender_id
        data = event.data.decode()
        parts = data.split(":")
        action = parts[2] if len(parts) > 2 else ""
        
        # Fix: target_uid might not be an int if it's a role string in some actions
        target_uid = None
        if len(parts) > 3:
            try:
                target_uid = int(parts[3])
            except ValueError:
                pass

        if not (is_owner(uid) or await q.has_permission(uid, "appoint_admins", OWNER_ID)
                or await q.has_permission(uid, "view_admins", OWNER_ID)):
            await event.answer("❌ No permission.", alert=True)
            return
        await event.answer()

        if action == "list":
            admin_list = await q.get_all_admins()
            for a in admin_list:
                u = await q.get_user(a["user_id"])
                a["username"] = (u.get("username") or u.get("display_name")) if u else str(a["user_id"])
            await event.edit(
                f"👑 <b>Admin Management</b>\n{len(admin_list)} admin(s)",
                parse_mode="html",
                buttons=kb_admin_list(admin_list, is_owner(uid))
            )

        elif action == "view" and target_uid:
            adm = await q.get_admin(target_uid)
            if not adm:
                await event.answer("Admin not found.", alert=True)
                return
            u = await q.get_user(target_uid)
            name = (u.get("username") or u.get("display_name")) if u else str(target_uid)
            role = adm.get("role","admin")
            perms_list = [f"{'✅' if v else '❌'} {k}" for k,v in adm.get("permissions",{}).items()]
            viewer_is_super = (await q.get_admin(uid) or {}).get("role") == "super_admin"
            await event.edit(
                f"{'🛡️' if role=='super_admin' else '⚙️'} <b>{h(name)}</b>\n"
                f"Role: <b>{role.replace('_',' ').title()}</b>\n"
                f"ID: <code>{target_uid}</code>\n\n"
                f"<b>Permissions:</b>\n" + "\n".join(perms_list[:15]),
                parse_mode="html",
                buttons=kb_admin_profile(target_uid, role, is_owner(uid), viewer_is_super)
            )

        elif action == "add" and is_owner(uid):
            await event.edit("Choose role for new admin:", parse_mode="html",
                             buttons=kb_add_admin_role())

        elif action == "newrole" and is_owner(uid):
            role = parts[3] if len(parts) > 3 else "admin"
            await q.set_state(uid, "adm:admins:getuser", data={"new_role": role})
            await event.edit(
                f"✍️ Send the <b>@username</b> or Telegram ID of the new {role.replace('_',' ').title()}:",
                parse_mode="html",
                buttons=markup(row(btn("🗑 Cancel","adm:admins:list","danger")))
            )

        elif action == "promote" and target_uid and is_owner(uid):
            adm = await q.get_admin(target_uid)
            new_perms = SUPER_ADMIN_DEFAULTS.copy()
            new_perms.update(adm.get("permissions",{}))
            await q.update_admin_role(target_uid, "super_admin")
            await q.update_admin_permissions(target_uid, new_perms)
            await event.answer("✅ Promoted.", alert=True)

        elif action == "demote" and target_uid and is_owner(uid):
            await q.update_admin_role(target_uid, "admin")
            await q.update_admin_permissions(target_uid, ADMIN_DEFAULTS.copy())
            await event.answer("⬇️ Demoted.", alert=True)

        elif action == "remove" and target_uid:
            await q.remove_admin(target_uid)
            await event.answer("🗑 Removed.", alert=True)
            admin_list = await q.get_all_admins()
            for a in admin_list:
                u = await q.get_user(a["user_id"])
                a["username"] = (u.get("username") or u.get("display_name")) if u else str(a["user_id"])
            await event.edit("👑 <b>Admin Management</b>", parse_mode="html",
                             buttons=kb_admin_list(admin_list, is_owner(uid)))

        elif action == "editperms" and target_uid:
            adm = await q.get_admin(target_uid)
            current_perms = adm.get("permissions",{})
            perm_list = ALL_PERMISSIONS if is_owner(uid) else [
                p for p in ALL_PERMISSIONS if p not in (
                    "appoint_admins","edit_admin_permissions","view_admins",
                    "delete_tasks","end_tasks_early","dm_blast",
                    "remove_contributions","edit_templates","export_stats","manage_ramadan"
                )
            ]
            await event.edit(
                f"🔧 <b>Edit Permissions for admin {target_uid}</b>",
                parse_mode="html",
                buttons=kb_permissions_editor(target_uid, current_perms, perm_list)
            )

        elif action == "toggleperm" and target_uid:
            perm = parts[4] if len(parts) > 4 else None
            if not perm:
                return
            adm = await q.get_admin(target_uid)
            current_perms = adm.get("permissions",{})
            current_perms[perm] = not current_perms.get(perm, False)
            await q.update_admin_permissions(target_uid, current_perms)
            perm_list = ALL_PERMISSIONS if is_owner(uid) else [
                p for p in ALL_PERMISSIONS if p not in (
                    "appoint_admins","edit_admin_permissions","view_admins",
                    "delete_tasks","end_tasks_early","dm_blast",
                    "remove_contributions","edit_templates","export_stats","manage_ramadan"
                )
            ]
            await event.edit(
                f"🔧 <b>Edit Permissions for admin {target_uid}</b>",
                parse_mode="html",
                buttons=kb_permissions_editor(target_uid, current_perms, perm_list)
            )

    # ═══════════════════════════════════════════════════════════
    #  OWNER SETTINGS
    # ═══════════════════════════════════════════════════════════
    @client.on(events.CallbackQuery(pattern=b"adm:settings.*"))
    async def adm_settings(event):
        uid = event.sender_id
        if not is_owner(uid):
            await event.answer("❌ Owner only.", alert=True)
            return
        data = event.data.decode()
        await event.answer()

        if data == "adm:settings":
            await event.edit("⚙️ <b>Bot Settings (Owner Only)</b>", parse_mode="html",
                             buttons=kb_owner_settings())

        elif data == "adm:settings:resetdb":
            from keyboards.builder import kb_reset_confirm
            await event.edit(
                "⚠️ <b>WARNING: DATABASE RESET</b>\n\n"
                "This will permanently delete ALL users, tasks, and contributions.\n"
                "This action CANNOT be undone.\n\n"
                "Are you absolutely sure?",
                parse_mode="html",
                buttons=kb_reset_confirm(step=1)
            )

        elif data == "adm:settings:reset_step2":
            from keyboards.builder import kb_reset_confirm
            await event.edit(
                "🛑 <b>SECOND CONFIRMATION</b>\n\n"
                "Please find the correct button to proceed. Shuffling buttons now...",
                parse_mode="html",
                buttons=kb_reset_confirm(step=2)
            )

        elif data == "adm:settings:reset_step3":
            from keyboards.builder import kb_reset_final
            await event.edit(
                "🔥 <b>FINAL WARNING</b>\n\n"
                "This is your last chance to abort.\n"
                "Tapping the button below will wipe EVERYTHING.",
                parse_mode="html",
                buttons=kb_reset_final()
            )

        elif data == "adm:settings:reset_final":
            await q.reset_database()
            await event.edit("💥 <b>DATABASE WIPED SUCCESSFULLY.</b>", parse_mode="html",
                             buttons=kb_back_admin())

        elif data == "adm:settings:clearfsm":
            from db.models import fsm_states
            await fsm_states().delete_many({})
            await event.edit("✅ All FSM states cleared.", parse_mode="html",
                             buttons=kb_owner_settings())

        elif data == "adm:settings:ramadan":
            await event.edit("🌙 <i>Ramadan Mode is a Phase 3 feature — coming soon!</i>",
                             parse_mode="html", buttons=kb_owner_settings())

        elif data == "adm:settings:templates":
            await event.edit(
                "📣 <b>Broadcast Templates</b>\n\n"
                "Use the Broadcast panel to send messages to members.\n"
                "<i>Custom template editing coming in Phase 2.</i>",
                parse_mode="html", buttons=kb_owner_settings()
            )

        elif data == "adm:settings:groupstats":
            await event.edit(
                "📊 Admins can post stats to the group via the Statistics panel.",
                parse_mode="html", buttons=kb_owner_settings()
            )


# ─────────────────────────────────────────────────────────────
#  Wizard helpers
# ─────────────────────────────────────────────────────────────
async def _wiz_next(event, uid, state, wiz):
    transitions = {
        "wiz:description": ("wiz:arabic",     "<b>Step 3.1</b> — Add Arabic text? (optional)"),
        "wiz:arabic":      ("wiz:meaning",    "<b>Step 3.2</b> — Add English meaning? (optional)"),
        "wiz:meaning":     ("wiz:reference",  "<b>Step 4</b> — Add a Hadith/Ayah reference? (optional)"),
        "wiz:reference":   ("wiz:intention",  "<b>Step 5</b> — Add an intention reminder? (optional)"),
        "wiz:intention":   ("wiz:type",       "<b>Step 7</b> — Choose task type:"),
    }
    kbs = {
        "wiz:description": kb_ai_suggest("arabic"),
        "wiz:arabic":      kb_ai_suggest("meaning"),
        "wiz:meaning":     kb_ai_suggest("reference"),
        "wiz:reference":   kb_ai_suggest("reminder"),
        "wiz:intention":   kb_task_type(),
    }
    if state in transitions:
        next_state, msg = transitions[state]
        await q.set_state(uid, next_state, data=wiz)
        await event.edit(msg, parse_mode="html", buttons=kbs[state])

async def _wiz_yes(event, uid, state, wiz):
    text_inputs = {
        "wiz:description": ("wiz:description_text", "✍️ Enter the task description:"),
        "wiz:arabic":      ("wiz:arabic_text",      "✍️ Enter the Arabic text:"),
        "wiz:meaning":     ("wiz:meaning_text",     "✍️ Enter the English meaning:"),
        "wiz:reference":   ("wiz:reference_text",   "✍️ Enter the Hadith/Ayah reference:"),
        "wiz:intention":   ("wiz:intention_text",   "✍️ Enter the intention reminder:"),
    }
    if state in text_inputs:
        next_state, prompt = text_inputs[state]
        await q.set_state(uid, next_state, data=wiz)
        await event.edit(prompt, parse_mode="html",
                         buttons=markup(row(btn("🗑 Cancel", "wiz:cancel", "danger"))))

async def _save_draft(event, uid, wiz, client):
    task_data = _build_task_data(wiz, uid, status="draft")
    task_id = await q.create_task(task_data)
    await q.clear_state(uid)
    perms = await get_perms(uid)
    await event.edit(
        f"💾 <b>Draft saved!</b>\n\n<i>{h(task_data['title'])}</i>\n\n"
        f"Go to <b>Draft Tasks</b> to activate it when ready.",
        parse_mode="html",
        buttons=markup(
            row(btn("💾 View Drafts",    "adm:tasks:draft", "primary")),
            row(btn("⬅️ Admin Panel",   "adm:main",         "primary")),
        )
    )

async def _publish_task(event, uid, wiz, client, activate=True):
    # Check one-active-task rule
    if activate:
        active_tasks = await q.get_active_tasks()
        if active_tasks:
            names = ", ".join(f"<b>{h(t['title'])}</b>" for t in active_tasks)
            await event.edit(
                f"⚠️ There is already an active task: {names}\n\n"
                f"End or pause it first, or save this as a draft instead.",
                parse_mode="html",
                buttons=markup(
                    row(btn("💾 Save as Draft",      "wiz:savedraft",        "primary")),
                    row(btn("📋 View Active Task",   "adm:tasks:active",     "primary")),
                    row(btn("🗑 Cancel",              "wiz:cancel",           "danger")),
                )
            )
            return

    status = "active" if activate else "draft"
    task_data = _build_task_data(wiz, uid, status=status)
    task_id = await q.create_task(task_data)
    task_data["_id"] = task_id
    await q.clear_state(uid)
    perms = await get_perms(uid)
    await event.edit(
        f"🚀 <b>{h(task_data['title'])}</b> is live! Announcement sent.",
        parse_mode="html",
        buttons=kb_admin_main(perms, is_owner(uid))
    )
    if wiz.get("type") == "emergency":
        from utils.announcements import announce_emergency
        await announce_emergency(client, task_data)
    else:
        await announce_task_published(client, task_data)

def _build_task_data(wiz, uid, status="active"):
    ends_at = None
    if wiz.get("ends_at"):
        try:
            ends_at = datetime.fromisoformat(wiz["ends_at"])
        except Exception:
            pass
    return {
        "title":               wiz.get("title","Untitled"),
        "dhikr_text":          wiz.get("dhikr_text",""),
        "category":            wiz.get("category"),
        "subcategory":         wiz.get("subcategory"),
        "sub_subcategory":     wiz.get("sub_subcategory"),
        "description":         wiz.get("description"),
        "reference":           wiz.get("reference"),
        "intention_reminder":  wiz.get("intention_reminder"),
        "media":               wiz.get("media",[]),
        "type":                wiz.get("type","count"),
        "target":              wiz.get("target"),
        "ends_at":             ends_at,
        "recurring_interval":  wiz.get("recurring_interval"),
        "status":              status,
        "leaderboard_visible": wiz.get("leaderboard_visible",True),
        "daily_limit_per_user":wiz.get("daily_limit_per_user"),
        "created_by":          uid,
        "starts_at":           datetime.utcnow() if status == "active" else None,
    }
