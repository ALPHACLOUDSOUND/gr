import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ChatMemberHandler
import time

# Define constants
OWNER_ID = 7049798779
BOT_TOKEN = '7288641809:AAEbI1YpB9urJyi28TWKS3heii8w6TiBtc0'
ADMIN_ACTION_THRESHOLD = 10  # Number of bans/kicks to trigger demotion
MONITORING_PERIOD = 120  # Period in seconds (2 minutes)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to track admin actions
admin_actions = {}

async def ban_all(update: Update, context: CallbackContext):
    # Check if the command issuer is the owner
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    # Send a confirmation message with an inline button
    keyboard = [[InlineKeyboardButton("Confirm Ban All", callback_data='confirm_ban_all')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Are you sure you want to ban all members from this group? This action cannot be undone.",
        reply_markup=reply_markup
    )

async def confirm_ban_all(update: Update, context: CallbackContext):
    query = update.callback_query
    
    # Check if the user confirming is the owner
    if query.from_user.id != OWNER_ID:
        await query.answer("You are not authorized to confirm this action.")
        return
    
    await query.answer()  # Acknowledge the query to avoid a "loading" circle

    chat_id = query.message.chat_id
    bot = context.bot
    
    try:
        # Get all members of the chat (this requires the bot to have the necessary permissions)
        members = await bot.get_chat_members_count(chat_id)
        
        for member in members:
            user_id = member.user.id
            
            # Skip the owner and the bot itself
            if user_id not in [OWNER_ID, bot.id]:
                try:
                    await bot.ban_chat_member(chat_id, user_id)
                except Exception as e:
                    logger.error(f"Failed to ban {user_id}: {e}")
        
        await query.edit_message_text("All users have been banned from the group.")
    except Exception as e:
        logger.error(f"Error banning users: {e}")
        await query.edit_message_text("An error occurred while banning users.")

async def monitor_admin_actions(update: Update, context: CallbackContext):
    if update.chat_member.new_chat_member.status == 'kicked':
        admin_id = update.chat_member.from_user.id
        chat_id = update.effective_chat.id
        banned_user_id = update.chat_member.new_chat_member.user.id
        
        current_time = time.time()
        
        # Initialize or update the admin's action log
        if admin_id not in admin_actions:
            admin_actions[admin_id] = []
        
        # Add the current action with a timestamp
        admin_actions[admin_id].append((banned_user_id, current_time))
        
        # Filter out actions that are outside the monitoring period
        admin_actions[admin_id] = [(uid, t) for uid, t in admin_actions[admin_id] if current_time - t < MONITORING_PERIOD]
        
        # Check if the admin has exceeded the action threshold
        if len(admin_actions[admin_id]) > ADMIN_ACTION_THRESHOLD:
            try:
                # Demote the admin
                await context.bot.promote_chat_member(
                    chat_id, admin_id,
                    can_change_info=False,
                    can_delete_messages=False,
                    can_invite_users=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_promote_members=False,
                    can_manage_video_chats=False,
                    is_anonymous=False
                )
                
                # Pin a message with details
                banned_usernames = ", ".join([f"@{(await context.bot.get_chat_member(chat_id, uid)).user.username or 'unknown'}" for uid, _ in admin_actions[admin_id]])
                pin_message = (
                    f"⚠️ Admin @{update.chat_member.from_user.username or 'unknown'} (ID: {admin_id}) has been demoted for banning/kicking more than {ADMIN_ACTION_THRESHOLD} members.\n"
                    f"List of banned/kicked users: {banned_usernames}"
                )
                message = await context.bot.send_message(chat_id, pin_message)
                await context.bot.pin_chat_message(chat_id, message.message_id)
                
                # Reset the admin's action log
                admin_actions[admin_id] = []
            except Exception as e:
                logger.error(f"Failed to demote admin {admin_id}: {e}")

def main():
    # Create the Application and pass it your bot's token
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command and callback handlers
    application.add_handler(CommandHandler("ban_all", ban_all))
    application.add_handler(CallbackQueryHandler(confirm_ban_all, pattern='confirm_ban_all'))

    # Monitor chat member updates to track bans/kicks
    application.add_handler(ChatMemberHandler(monitor_admin_actions))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
