import json
import time
import boto3
import botocore
import os
from loguru import logger
from utils import search_download_youtube_video


def process_msg(msg):
    video_filename = search_download_youtube_video(msg, 1, s3_bucket_name)
    print(f'the video file name is : {video_filename}')
    return video_filename


def main():
    while True:
        try:
            messages = queue.receive_messages(
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            for msg in messages:
                logger.info(f'processing message {msg}')
                video_filename = process_msg(msg.body)
                chat_id = msg.message_attributes.get('chat_id').get('StringValue')
                response2 = worker_to_bot_queue.send_message(
                    MessageBody=video_filename[0],
                    MessageAttributes={'chat_id': {'StringValue': chat_id, 'DataType': 'String'}
                                       }
                )
                logger.info(f'msg {response2.get("MessageId")} has been sent to queue 2')
                # delete message from the queue after it was handled
                response = queue.delete_messages(Entries=[{
                    'Id': msg.message_id,
                    'ReceiptHandle': msg.receipt_handle
                }])
                if 'Successful' in response:
                    logger.info(f'msg {msg} has been handled successfully')
        except botocore.exceptions.ClientError as err:
            logger.exception(f"Couldn't receive messages {err}")
        time.sleep(10)


if __name__ == '__main__':
    with open('config.json') as f:
        config = json.load(f)

    sqs = boto3.resource('sqs', region_name=config.get('aws_region'))
    queue = sqs.get_queue_by_name(QueueName=config.get('bot_to_worker_queue_name'))
    worker_to_bot_queue = sqs.get_queue_by_name(QueueName=config.get('worker_to_bot_queue_name'))
    s3_bucket_name = config.get('bucket_name')
    cwd = os.getcwd()
    path = f"{cwd}/ytdlAppData"
    # Check whether the specified path exists or not
    isExist = os.path.exists(path)

    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)
        print("The new directory is created!")

    main()
