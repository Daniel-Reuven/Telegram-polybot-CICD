import json
import threading
import boto3
from time import sleep
from telegram.ext import Updater, MessageHandler, Filters
from loguru import logger
from common.utils import send_videos_from_bot_queue, is_string_an_url, upload_file2, initial_download


class Bot:
    def __init__(self, token):
        # create frontend object to the bot programmer
        self.updater = Updater(token, use_context=True)
        # add _message_handler as main internal msg handler
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self._message_handler))

    def start(self):
        """Start polling msgs from users, this function never returns"""
        self.updater.start_polling()
        logger.info(f'{self.__class__.__name__} is up and listening to new messages....')
        self.updater.idle()

    def _message_handler(self, update, context):
        """Main messages handler"""
        self.send_text(update, f'Your original message: {update.message.text}')

    def send_text(self, update, text, chat_id=None, quote=False):
        """Sends text to a chat"""
        if chat_id:
            self.updater.bot.send_message(chat_id, text=text)
        else:
            # retry https://github.com/python-telegram-bot/python-telegram-bot/issues/1124
            update.message.reply_text(text, quote=quote)


class YouTubeVideoDownloaderBot(Bot):
    def __init__(self, token):
        super().__init__(token)
        # Starts a thread to handle bot queue
        threading.Thread(
            target=send_videos_from_bot_queue,
            args=(worker_to_bot_queue, config.get('bucket_name'))
        ).start()

    def _message_handler(self, update, context):
        # Gather user information for logging purposes
        chat_id = str(update.effective_message.chat_id)
        inbound_text = update.message.text
        fname = update.message.from_user.first_name
        lname = update.message.from_user.last_name
        username = update.message.from_user.username
        logger.info(f'chat_id: {chat_id}({username}) - {fname} {lname} has started a conversation'.format())
        # Start processing user input
        # Handle "/start" mode
        if update.message.text.lower() == '/start':
            self.send_text(update, f'Hello there, Welcome to Video Downloader.')
            sleep(1)
            self.send_text(update, f'Send a video link, get back download a link for that video\n/help - Display help information.')
        # Handle "/help" mode
        elif update.message.text.lower() == '/help':
            self.send_text(update, f'Hello there, Welcome to Video Downloader.')
            sleep(1)
            self.send_text(update, f'Send a video link, get back a download link for that video\n/help - Display help information.')
            logger.info(f'help menu requested'.format())
        # Handle "/setquality" mode
        elif update.message.text.lower().startswith('/setquality'):
            if chat_id == dev_chat_id:
                qfile_flag = False
                temp = inbound_text.split(" ", 1)[1]
                logger.info(f'Admin command detected, attempting to comply'.format())
                self.send_text(update, f'Admin command detected, attempting to comply')
                sleep(1)
                with open('quality_file.json') as f2:
                    qfile_data = json.load(f2)
                if temp == 'fhd':
                    if qfile_data["quality"] != 1080:
                        qfile_data["quality"] = 1080
                        qfile_flag = True
                elif temp == 'qhd':
                    if qfile_data["quality"] != 2160:
                        qfile_data["quality"] = 2160
                        qfile_flag = True
                if qfile_flag:
                    try:
                        with open('quality_file.json', 'w') as f2_w:
                            json.dump(qfile_data, f2_w)
                        f2_w.close()
                        local_file = 'quality_file.json'
                        s3_path = 'quality_file.json'
                        upload_file2(config.get('bucket_name'), local_file, s3_path)
                        logger.info(f'Admin command successfully executed'.format())
                        self.send_text(update, f'Admin command successfully executed')
                        qfile_flag = False
                    except Exception as e:
                        logger.error(e)
                        self.send_text(update, f'Failed to comply')
            else:
                self.send_text(update, f'you are not allowed to use admin commands.')
                logger.warning('admin command detected from non admin user'.format())
        else:
            temp = inbound_text.replace(" ", "")
            if is_string_an_url(temp):
                # Handle "free-text" mode
                # Check if user input is a valid URL for YT-DLP
                self.send_text(update, f'Processing link')
                logger.info(f'Sending to SQS queue({bot_to_worker_queue}) - {temp}'.format())
                # Send to AWS SQS queue
                response = bot_to_worker_queue.send_message(
                    MessageBody=inbound_text,
                    MessageAttributes={
                        'chat_id': {'StringValue': chat_id, 'DataType': 'String'}
                    }
                )
                logger.info(f'Message {response.get("MessageId")} has been sent to SQS queue({bot_to_worker_queue})')
            else:
                # Send a message to customer saying the URL is invalid
                self.send_text(update, f'Invalid URL, please try again with a valid URL.')
                logger.error(f'Invalid URL received by chat_id: {chat_id}'.format())


if __name__ == '__main__':
    with open('secrets/.telegramToken') as f:
        _token = f.read()
    f.close()
    with open('common/config.json') as f2:
        config = json.load(f2)
    f2.close()
    # Initialize secret file
    initial_download(config.get('bucket_name'), 'secret.json')
    # Initialize quality file
    initial_download(config.get('bucket_name'), 'quality_file.json')
    sqs = boto3.resource('sqs', region_name=config.get('aws_region'))
    bot_to_worker_queue = sqs.get_queue_by_name(QueueName=config.get('bot_to_worker_queue_name'))
    worker_to_bot_queue = sqs.get_queue_by_name(QueueName=config.get('worker_to_bot_queue_name'))
    with open('secret.json') as json_handler:
        secret_data = json.load(json_handler)
    dev_chat_id = secret_data["dev_chat_id"]
    json_handler.close()
    my_bot = YouTubeVideoDownloaderBot(_token)
    my_bot.start()
