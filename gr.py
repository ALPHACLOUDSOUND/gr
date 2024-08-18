import logging
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackContext, ChatMemberHandler, filters
from collections import defaultdict
import time

# Setup
TELEGRAM_TOKEN = '7288641809:AAEbI1YpB9urJyi28TWKS3heii8w6TiBtc0'
OWNER_ID = '7049798779'

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Track admin actions
admin_actions = defaultdict(list)

# Promote a user to admin
async def promote(update: Update, context: CallbackContext):
    user = update.message.reply_to_message.from_user
    if user:
        await context.bot.promote_chat_member(
            chat_id=update.message.chat_id,
            user_id=user.id,
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=True
        )
        await update.message.reply_text(f"{user.first_name} has been promoted to admin.")
    else:
        await update.message.reply_text("Reply to the user's message you want to promote.")

# Demote an admin to a regular user
async def demote(update: Update, context: CallbackContext):
    user = update.message.reply_to_message.from_user
    if user:
        await context.bot.promote_chat_member(
            chat_id=update.message.chat_id,
            user_id=user.id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False
        )
        await update.message.reply_text(f"{user.first_name} has been demoted from admin.")
    else:
        await update.message.reply_text("Reply to the admin's message you want to demote.")

# Handle admin actions
async def monitor_admin_actions(update: Update, context: CallbackContext):
    admin_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_time = time.time()
    
    admin_actions[admin_id].append(current_time)
    admin_actions[admin_id] = [timestamp for timestamp in admin_actions[admin_id] if current_time - timestamp < 60]
    
    if len(admin_actions[admin_id]) > 10:
        await demote_admin(chat_id, admin_id, context)

async def demote_admin(chat_id, admin_id, context: CallbackContext):
    await context.bot.promote_chat_member(
        chat_id=chat_id,
        user_id=admin_id,
        can_change_info=False,
        can_delete_messages=False,
        can_invite_users=False,
        can_restrict_members=False,
        can_pin_messages=False,
        can_promote_members=False
    )
    await context.bot.send_message(chat_id=chat_id, text=f"Admin <b>{admin_id}</b> demoted for excessive bans/removals.", parse_mode="HTML")
    await context.bot.send_message(chat_id=OWNER_ID, text=f"Warning: Admin <b>{admin_id}</b> attempted to ban/remove multiple users in a short period.", parse_mode="HTML")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("promote", promote))
    application.add_handler(CommandHandler("demote", demote))
    
    application.add_handler(ChatMemberHandler(monitor_admin_actions, filters.ChatMemberUpdated.status() == "kicked"))

    application.run_polling()

if __name__ == '__main__':
    main()
