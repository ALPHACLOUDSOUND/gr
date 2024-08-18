import logging
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackContext, ChatMemberHandler
from collections import defaultdict
import time

# Setup
TELEGRAM_TOKEN = '7288641809:AAEbI1YpB9urJyi28TWKS3heii8w6TiBtc0'
OWNER_ID = 7049798779  # Group owner's ID

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Track admin actions
admin_actions = defaultdict(list)
banned_users = defaultdict(list)

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
    banned_users[admin_id].append(update.chat_member.user.id)
    
    # Filter out actions older than 60 seconds
    admin_actions[admin_id] = [timestamp for timestamp in admin_actions[admin_id] if current_time - timestamp < 60]

    if len(admin_actions[admin_id]) > 10:
        await demote_admin(chat_id, admin_id, context)

async def demote_admin(chat_id, admin_id, context: CallbackContext):
    # Demote the admin
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
    
    # Prepare the message with the list of banned/kicked users
    banned_users_list = "\n".join([f"User ID: {user_id}" for user_id in banned_users[admin_id]])
    admin_username = (await context.bot.get_chat_member(chat_id, admin_id)).user.username
    
    message_text = (
        f"🚨 Admin @{admin_username} (ID: {admin_id}) has been demoted for banning/kicking more than 10 users.\n"
        f"List of banned/kicked users:\n{banned_users_list}"
    )
    
    # Pin the message in the group
    sent_message = await context.bot.send_message(chat_id=chat_id, text=message_text)
    await context.bot.pin_chat_message(chat_id=chat_id, message_id=sent_message.message_id)

    # Notify the group owner
    await context.bot.send_message(chat_id=OWNER_ID, text=message_text)

    # Clear the records for this admin after demotion
    del admin_actions[admin_id]
    del banned_users[admin_id]

# This function is triggered when a user is removed (kicked/banned) from the group
async def on_chat_member_update(update: Update, context: CallbackContext):
    if update.chat_member.old_chat_member.is_member and not update.chat_member.new_chat_member.is_member:
        # A user was removed from the group (kicked or banned)
        await monitor_admin_actions(update, context)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("promote", promote))
    application.add_handler(CommandHandler("demote", demote))
    
    # Listen to chat member updates (like kicking, banning, etc.)
    application.add_handler(ChatMemberHandler(on_chat_member_update))

    application.run_polling()

if __name__ == '__main__':
    main()

