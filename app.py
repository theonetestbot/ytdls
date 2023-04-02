import os
import logging
import tempfile
from pytube import YouTube
from telegram import ChatAction
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
VIDEO, AUDIO = range(2)

# Define the download directory
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', 'downloads')

def download_video_stream(update, context):
    """Start the process to download a YouTube video stream."""
    # Get the YouTube video ID from the command arguments
    video_id = context.args[0]

    # Get the available video streams for the video
    video = YouTube(f'https://www.youtube.com/watch?v={video_id}')
    video_streams = video.streams.filter(progressive=True)

    # Store the available streams in context user_data
    context.user_data['video_streams'] = video_streams

    # Prompt the user to select a stream
    stream_text = 'Select a video stream quality:\n\n'
    for i, stream in enumerate(video_streams):
        stream_text += f'{i+1}. {stream.resolution} ({stream.mime_type})\n'
    update.message.reply_text(stream_text)

    # Update the conversation state
    return VIDEO


def download_audio(update, context):
    """Start the process to download a YouTube audio stream."""
    # Get the YouTube video ID from the command arguments
    video_id = context.args[0]

    # Get the available audio streams for the video
    video = YouTube(f'https://www.youtube.com/watch?v={video_id}')
    audio_streams = video.streams.filter(only_audio=True)

    # Download the audio stream
    output_file = audio_streams[0].download(output_path=DOWNLOAD_DIR)

    # Send the audio file to the user
    context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(output_file, 'rb'))

    # Delete the downloaded file
    os.remove(output_file)


def select_video_stream(update, context):
    """Select the video stream to download and prompt the user for the download format."""
    # Get the selected video stream
    selected_stream = context.user_data['video_streams'][int(update.message.text) - 1]

    # Store the selected stream in context user_data
    context.user_data['selected_stream'] = selected_stream

    # Prompt the user to select the download format
    keyboard = [['Video', 'Audio'], ['Cancel']]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Select a download format:', reply_markup=reply_markup)

    # Update the conversation state
    return AUDIO


def download_video(update, context):
    """Download the selected video stream."""
    # Get the selected stream and download format
    selected_stream = context.user_data['selected_stream']
    download_format = update.message.text.lower()

    # Set the appropriate file extension
    file_ext = 'mp4' if download_format == 'video' else 'mp3'

    # Send a "typing" action to the user
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Download the video or audio stream
    output_file = selected_stream.download(output_path=DOWNLOAD_DIR, filename=f'{selected_stream.default_filename}.{file_ext}')

    # Send the file to the user
    if download_format == 'video':
        context.bot.send_video(chat_id=update.effective_chat.id, video=open(output_file, 'rb'))
    else:
        context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(output_file, 'rb'))

    # Delete the downloaded file
    os.remove(output_file)

    # End the conversation
    return ConversationHandler.END


def cancel(update, context):
    """End the conversation."""
    update.message.reply_text('Canceled.')

    return ConversationHandler.END


def main():
    """Start the bot."""
    # Create the Updater and dispatcher
    updater = Updater(token=os.environ.get('TELEGRAM_TOKEN'), use_context=True)
    dispatcher = updater.dispatcher

    # Add conversation handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('download', download_video_stream)],
        states={
            VIDEO: [MessageHandler(Filters.text & ~Filters.command, select_video_stream)],
            AUDIO: [MessageHandler(Filters.regex('^(Video|Audio)$'), download_video)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dispatcher.add_handler(conv_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

