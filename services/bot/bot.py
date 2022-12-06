import json
import threading
import botocore
from telegram.ext import Updater, MessageHandler, Filters
from loguru import logger
import boto3
from boto3.dynamodb.conditions import Key
from common.utils import calc_backlog_per_instance, search_youtube_video, send_videos_from_queue2


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

    def send_video(self, update, context, file_path):
        """Sends video to a chat"""
        context.bot.send_video(chat_id=update.message.chat_id, video=open(file_path, 'rb'), supports_streaming=True)

    def send_text(self, update, text, chat_id=None, quote=False):
        """Sends text to a chat"""
        if chat_id:
            self.updater.bot.send_message(chat_id, text=text)
        else:
            # retry https://github.com/python-telegram-bot/python-telegram-bot/issues/1124
            update.message.reply_text(text, quote=quote)



class YoutubeObjectDetectBot(Bot):
    def __init__(self, token):
        super().__init__(token)
        threading.Thread(
            target=calc_backlog_per_instance,
            args=(workers_queue, asg, config.get("autoscaling_group_name"), config.get('aws_region'))
        ).start()
        threading.Thread(
            target=send_videos_from_queue2,
            args=(worker_to_bot_queue, config.get('bucket_name'))
        ).start()

    def _message_handler(self, update, context):
        try:
            chat_id = str(update.effective_message.chat_id)
            if update.message.text.startswith('/myvideos'):
                response = table.query(KeyConditionExpression=Key('chatId').eq(chat_id))
                for key, value in response.items():
                    if isinstance(value, list):
                        array_length = len(value)
                        for i in range(array_length):
                            temp_dict = value[i]
                            video_url = temp_dict['url']
                            video = search_youtube_video(None, video_url)
                            self.send_text(update, f'Video Name: {video["title"]}, Video Link: {video["webpage_url"]}', chat_id=chat_id)
                logger.info(f'sent videos information to client, chat_id: {chat_id}')
            else:
                response = workers_queue.send_message(
                    MessageBody=update.message.text,
                    MessageAttributes={
                        'chat_id': {'StringValue': chat_id, 'DataType': 'String'}
                    }
                )
                logger.info(f'msg {response.get("MessageId")} has been sent to queue')
                self.send_text(update, f'Your message is being processed...', chat_id=chat_id)
                for video in search_youtube_video(update.message.text, None):
                    item = {
                        'chatId': chat_id,
                        'videoId': video['id'],
                        'url': video['webpage_url'],
                        'title': video['title']
                    }
                    response2 = table.put_item(Item=item)

        except botocore.exceptions.ClientError as error:
            logger.error(error)
            self.send_text(update, f'Something went wrong, please try again...')

if __name__ == '__main__':
    with open('.telegramToken') as f:
        _token = f.read()

    with open('config.json') as f:
        config = json.load(f)

    sqs = boto3.resource('sqs', region_name=config.get('aws_region'))
    workers_queue = sqs.get_queue_by_name(QueueName=config.get('bot_to_worker_queue_name'))
    worker_to_bot_queue = sqs.get_queue_by_name(QueueName=config.get('worker_to_bot_queue_name'))
    asg = boto3.client('autoscaling', region_name=config.get('aws_region'))
    dynamodb = boto3.resource('dynamodb', region_name=config.get('aws_region'))
    table = dynamodb.Table(config.get('table_name'))
    my_bot = YoutubeObjectDetectBot(_token)
    my_bot.start()
