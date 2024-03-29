import logging
import os
from telegram import Update, error, ReplyKeyboardMarkup as RKM
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from video_splitter import Video_splitter
import settings
from bot import Katana

vs = Video_splitter()
filename = None


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

START, VIDEO, SPLIT_BY_SECOND, SPLIT_BY_PART = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start bot"""
    user = update.message.from_user
    logger.info("%s started the bot", user.first_name.title())
    await update.message.reply_text(
        "I am Video Splitter. Send a video. Split size is 30 seconds."
    )
    
    return VIDEO


async def collect_video(update, context):
    file_id = update.message.video.file_id
    new_file = await context.bot.get_file(file_id)
    video_name = await new_file.download_to_drive("vid/video.mp4")
    logger.info("Saved %s ", video_name) 


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message to bot."""
    user = update.message.from_user
    message = f"""
	Hello {user.first_name}, welcome to Video Splitter by @yaw_o_k .
	Commands:
	/start : Start the bot
	/help : Show this information
	/split_size (args: seconds): Change split size seconds. eg "/split_size 5" ie. Changes split size from 30 seconds(default) to 5 seconds
    """
    logger.info("%s started the bot", user.first_name.title())
    await update.message.reply_text(message)


async def split_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change seconds a video will be divided into."""
    try:
        user_input = update.message.text.split(" ")[1]
        vs.change_seconds(new_seconds=int(user_input))
        await update.message.reply_text(
            f"Video split size has changed to {user_input} seconds.",
        )
        logger.info("Video split size changed to %s seconds", user_input)
    except IndexError:
        # User requests to view split size by /split_size only
        await update.message.reply_text(
            f"""
			Split size of a video is set to: {vs.seconds}
			You can change the video split size by passing an argument with /split_size.
			Eg: /split_size 5 (change split size of a video to 5 seconds)
			""",
        )
        logger.info("Split size printed to user")
    except TypeError:
        await update.message.reply_text(
            f"""Wrong input. Enter a number as an argument instead. 
			Eg: /split_size 5 (change split size of a video to 5 seconds)
			""",
        )
        logger.info("Split size change attempt failed")
    except ValueError:
        await update.message.reply_text(
            "There is more than one space between the command and the variable.\nTry again",
        )
        logger.info("Split size change attempt failed")


async def split_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change seconds a video will be divided into."""
    try:
        user_input = update.message.text.split(" ")[1]
        vs.change_split_number(new_number=int(user_input))
        await update.message.reply_text(
            f"Video split number has changed to {user_input} parts.",
        )
        logger.info("Video split size changed to %s parts", user_input)
    except IndexError:
        # User requests to view split size by /split_size only
        await update.message.reply_text(
            f"""
			Split size of a video is set to: {vs.split_number}
			You can change the video split size by passing an argument with /split_number.
			Eg: /split_number 5 (change split number of a video to 5 parts)
			""",
        )
        logger.info("Split number printed to user")
    except TypeError:
        await update.message.reply_text(
            f"""Wrong input. Enter a number as an argument instead. 
			Eg: /split_number 2 (change split number of a video to 2 parts)
			""",
        )
        logger.info("Split number change attempt failed")
    except ValueError:
        await update.message.reply_text(
            "There is more than one space between the command and the variable.\nTry again",
        )
        logger.info("Split size change attempt failed")


async def split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Split video and send files to bot."""
    # Download file.
    sticker = await context.bot.send_sticker(
        chat_id=update.effective_chat.id, sticker="loading.tgs"
    )
    sent_videos = []
    try:
        file_id = update.message.video.file_id
        new_file = await context.bot.get_file(file_id)
        video_name = await new_file.download_to_drive("vid/video.mp4")
        logger.info("Saved %s ", video_name)

        # split
        split_videos = vs.split(str(video_name))
        for v in split_videos:
            sent_videos.append(v)
            await context.bot.send_video(chat_id=update.effective_chat.id, video=v)

            # Remove files to reuse folder
        vs.remove(split_videos)
        vs.remove([str(video_name)])
        logger.info("Removed %s and split videos", video_name)
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=sticker.id
        )

    except error.BadRequest:
        video_size = update.message.video.file_size
        await update.message.reply_text(
            f"""
		Size of video too large to be saved. Please
		try again with a smaller video size.
		Current video size: {int(video_size/1000000)}mb.
		Bot filesize limit: 20mb.
		""",
        )
        logger.info("Video too large; ask your to resend smaller video.")
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=sticker.id
        )
    except SystemExit:
        video_duration = update.message.video.duration
        message = f"""
		Video duration is too short to be split.
		Current video duration: {video_duration} seconds.
		Current split size: {vs.seconds} seconds.
		You can use /split_size {video_duration/2} to split video into 2.
		"""
        await update.message.reply_text(message)
        vs.remove([str(video_name)])
        logger.info("Removed %s.", video_name)
        logger.info("Ask user to change split size to suit video duration.")
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=sticker.id
        )
    except error.TimedOut:
        for v in split_videos:
            if v not in sent_videos:
                sent_videos.append(v)
                await context.bot.send_video(chat_id=update.effective_chat.id, video=v)

        # Remove files to reuse folder
        vs.remove(split_videos)
        vs.remove([str(video_name)])
        logger.info("Removed %s and split videos", video_name)
        print(sticker.id)
        print(sticker)
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=sticker.id
        )




if __name__ == "__main__":
    katana = Katana(Update, ContextTypes.DEFAULT_TYPE, error, RKM)
    # Create vid folder
    try:
        os.mkdir("vid")
    except FileExistsError:
        logger.info("vid folder already exists.")
    PORT = int(os.environ.get("PORT", "8443"))
    application = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", katana.start)],
        states={
            katana.VIDEO: [MessageHandler(filters.VIDEO, katana.collect_video)],
            katana.SECONDS_OR_PARTS: [
                MessageHandler(filters.Regex("^Seconds$"), katana.collect_seconds),
                MessageHandler(filters.Regex("^Parts$"), katana.collect_parts),
                ],
            katana.SPLIT: [MessageHandler(filters.Text, katana.split_video)],
        },
        fallbacks=[CommandHandler("help", katana.help)]
        )




    """ start_handler = CommandHandler("start", katana.start)
    split_size_handler = CommandHandler("split_size", split_size)
    split_number_handler = CommandHandler("split_number", split_number)
    video_handler = MessageHandler(filters.VIDEO, split)
    help_handler = CommandHandler("help", help) """
    application.add_handler(conversation)
    # application.add_handler(video_handler)
    # application.add_handler(split_size_handler)
    # application.add_handler(split_number_handler)
    # application.add_handler(help_handler)

    application.run_polling()
"""
	application.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    secret_token=settings.SECRET_TOKEN,
    webhook_url="katana.up.railway.app"
)
"""
