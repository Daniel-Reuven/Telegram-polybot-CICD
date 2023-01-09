import json
import time
import threading
import boto3
import os
from datetime import datetime
from loguru import logger
from common.utils import download_youtube_video_to_s3, sync_quality_file, initial_download


def main(quality_file_dt, quality_var):
    threading.Thread(
        target=sync_quality_file, args=(config.get('bucket_name'), _token)
    ).start()
    i = 0
    while True:
        dt_now = datetime.now()  # for logs
        quality_var_test = os.path.getmtime('quality_file.json')
        quality_var_test_2 = datetime.fromtimestamp(quality_var_test)

        if quality_var_test_2 > quality_file_dt:
            # Reinitialize the quality file
            with open('quality_file.json') as f3:
                qconfig = json.load(f3)
            quality_var = qconfig.get('quality')
            quality_file = os.path.getmtime('quality_file.json')
            quality_file_dt = datetime.fromtimestamp(quality_file)
            f3.close()
        i += 1
        try:
            messages = queue.receive_messages(
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            for msg in messages:
                logger.info(f'processing message {msg}')
                video_filename = download_youtube_video_to_s3(msg.body, s3_bucket_name, quality_var)
                chat_id = msg.message_attributes.get('chat_id').get('StringValue')
                response2 = worker_to_bot_queue.send_message(
                    MessageBody=video_filename,
                    MessageAttributes={'chat_id': {'StringValue': chat_id, 'DataType': 'String'}
                                       }
                )
                logger.info(f'msg {response2.get("MessageId")} has been sent to bot queue')
                # delete message from the queue after it was handled
                response = queue.delete_messages(Entries=[{
                    'Id': msg.message_id,
                    'ReceiptHandle': msg.receipt_handle
                }])
                if 'Successful' in response:
                    logger.info(f'msg {msg} has been handled successfully')
        except Exception as err:
            logger.exception(f"Couldn't receive messages {err}")
        logger.info(f'Waiting for new msgs - {dt_now}')
        if i == 6:
            logger.info(f'Process is running as of {dt_now}, checking queue every 10 seconds, this message repeats every 60 seconds')
            i = 0
        time.sleep(10)


if __name__ == '__main__':
    with open('env.txt') as f2:
        env = f2.readline().strip('\n')
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
    sqs = boto3.resource('sqs', region_name=config.get('aws_region'))
    queue = sqs.get_queue_by_name(QueueName=config.get('bot_to_worker_queue_name'))
    worker_to_bot_queue = sqs.get_queue_by_name(QueueName=config.get('worker_to_bot_queue_name'))
    s3_bucket_name = config.get('bucket_name')
    # # Initialize secret file
    initial_download(s3_bucket_name, 'secret.json')
    # # Initialize quality file
    initial_download(s3_bucket_name, 'quality_file.json')
    with open('quality_file.json') as f3:
        qconfig = json.load(f3)
    f3.close()
    quality_var = qconfig.get('quality')
    quality_file = os.path.getmtime('quality_file.json')
    quality_file_dt = datetime.fromtimestamp(quality_file)
    cwd = os.getcwd()
    path = f"{cwd}/ytdlAppData"
    # Check whether the specified path exists or not
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)
    main(quality_file_dt, quality_var)
