import json
import threading
import boto3
from botocore.exceptions import ClientError
from telegram.ext import Updater, MessageHandler, Filters
from loguru import logger
from common.utils import send_videos_from_bot_queue, is_string_an_url, aws_s3_bucket_upload_file2, initial_download


class Bot:
    def __init__(self, token):
        # create frontend object to the bot programmer
        self.updater = Updater(token, request_kwargs={'read_timeout': 600, 'connect_timeout': 600}, use_context=True)
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


class VideoDownloaderBot(Bot):
    def __init__(self, token):
        super().__init__(token)
        # Starts a thread to handle bot queue
        self.thread1 = threading.Thread(target=send_videos_from_bot_queue, args=(worker_to_bot_queue, config.get('bucket_name')))
        self.thread1.start()

    def _message_handler(self, update, context):
        # Gather user information for logging purposes
        chat_id = str(update.effective_message.chat_id)
        inbound_text = update.message.text
        fname = update.message.from_user.first_name
        lname = update.message.from_user.last_name
        username = update.message.from_user.username
        logger.info(f'chat_id: {chat_id}({username}) - {fname} {lname} has started a conversation'.format())
        # Start processing user input( check for update.message to ignore edited inputs.
        if update.message:
            # Handle "/start" mode
            if update.message.text.lower() == '/start':
                self.send_text(update, f'Hello there, Welcome to Video Downloader.')
                self.send_text(update, f'Send a video link, get back download a link for that video\n/help - Display help information.')
            # Handle "/help" mode
            elif update.message.text.lower() == '/help':
                self.send_text(update, f'Hello there, Welcome to Video Downloader Help Menu.')
                self.send_text(update, f'This bot has various features\n'
                                       f'Send a video link and get back an expiring fast download link for that video.\n'
                                       f'/Start - Display basic hello information.\n'
                                       f'/Quality - Display what video resolution is the bot set to try to download, up to.\n'
                                       f'/help - Display help information.\n')
                logger.info(f'help menu requested'.format())
            # Handle "/quality" mode
            elif update.message.text.lower() == '/quality':
                with open('quality_file.json') as f3:
                    qfile_data = json.load(f3)
                f3.close()
                self.send_text(update, f'Quality: up to {qfile_data["quality"]}')
                logger.info(f'quality check requested'.format())
            # Handle "/setquality" mode
            elif update.message.text.lower().startswith('/setquality'):
                if chat_id == dev_chat_id:
                    logger.info(f'Admin command detected, attempting to comply'.format())
                    self.send_text(update, f'Admin command detected, attempting to comply')
                    local_file = 'quality_file.json'
                    s3_path = 'quality_file.json'
                    with open('quality_file.json') as f3:
                        qfile_data = json.load(f3)
                    f3.close()
                    if update.message.text.lower() == '/setquality qhd':
                        qfile_data["quality"] = 2160
                        try:
                            with open('quality_file.json', 'w') as f3_w:
                                json.dump(qfile_data, f3_w)
                            f3_w.close()
                            aws_s3_bucket_upload_file2(config.get('bucket_name'), local_file, s3_path)
                            logger.info(f'Quality updated, waiting for backend(1-2 minutes).'.format())
                            self.send_text(update, f'Quality updated, waiting for backend(1-2 minutes).')
                        except Exception as e:
                            logger.error(e)
                            self.send_text(update, f'Failed to comply')
                    elif update.message.text.lower() == '/setquality fhd':
                        qfile_data["quality"] = 1080
                        try:
                            with open('quality_file.json', 'w') as f3_w:
                                json.dump(qfile_data, f3_w)
                            f3_w.close()
                            aws_s3_bucket_upload_file2(config.get('bucket_name'), local_file, s3_path)
                            logger.info(f'Quality updated, waiting for backend(1-2 minutes).'.format())
                            self.send_text(update, f'Quality updated, waiting for backend(1-2 minutes).')
                        except Exception as e:
                            logger.error(e)
                            self.send_text(update, f'Failed to comply')
                    else:
                        # Send a message to customer saying the command is invalid
                        self.send_text(update, f'Invalid command, please try again with correct command.')
                        logger.error(f'Invalid command received by chat_id: {chat_id}'.format())
                else:
                    self.send_text(update, f'you are not allowed to use admin commands.')
                    logger.warning('admin command detected from non admin user'.format())
            else:
                # Handle "free-text" / URL text mode.
                temp = inbound_text
                # Remove any spaces from URL.
                while ' ' in temp:
                    temp = temp.replace(' ', '')
                # Check if user input is a valid URL for YT-DLP
                if is_string_an_url(temp):
                    self.send_text(update, f'Processing link')
                    logger.info(f'Sending to SQS queue({bot_to_worker_queue}) - {temp}'.format())
                    try:
                        # Send to AWS SQS queue
                        response = bot_to_worker_queue.send_message(
                            MessageBody=temp,
                            MessageAttributes={
                                'chat_id': {'StringValue': chat_id, 'DataType': 'String'}
                            }
                        )
                        logger.info(f'Message {response.get("MessageId")} has been sent to SQS queue({bot_to_worker_queue})')
                    except ClientError as e:
                        logger.error(f'An error has occurred: {e}')
                        self.send_text(update, f'An error has occurred, please try again, if problem persists, please try again later')
                else:
                    # Send a message to customer saying the URL is invalid
                    self.send_text(update, f'Invalid URL, please try again with a valid URL.')
                    logger.error(f'Invalid URL received by chat_id: {chat_id}'.format())


if __name__ == '__main__':
    with open('env.txt') as f0:
        env = f0.readline().strip('\n')
    f0.close()
    logger.info(f'environment is: {env}')
    if env == 'dev':
        with open('common/config-dev.json') as f1:
            config = json.load(f1)
    else:
        with open('common/config.json') as f1:
            config = json.load(f1)
    logger.info(f'environment config: {config}')
    f1.close()
    with open('secrets/.telegramToken') as f2:
        _token = f2.read()
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
    my_bot = VideoDownloaderBot(_token)
    my_bot.start()
