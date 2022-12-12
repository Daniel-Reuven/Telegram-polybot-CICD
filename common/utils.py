import os
import boto3
import botocore
import requests
import yt_dlp
import re
import validators
from botocore.exceptions import ClientError
from botocore.config import Config
from loguru import logger
from time import sleep
from datetime import datetime
from validators import ValidationFailure


def download_youtube_video_to_s3(yt_link, s3_bucket_name):
    try:
        # Parameters for youtube_dl use
        # Max quality set to 1080p, to avoid large filesize
        ydl = {
            'noplaylist': 'True',
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'writethumbnail': True,
            'postprocessors': [{
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            }],
            'outtmpl': './ytdlAppData/%(id)s.%(ext)s',
            'verbose': False,
        }
        with yt_dlp.YoutubeDL(ydl) as ydl:
            # Clean local cache
            ydl.cache.remove()
            # Get info about the video via URL
            video = ydl.extract_info(yt_link, download=False)
            # Manipulate filename to remove unwanted characters
            folderogfilename = 'ytdlAppData/' + video['id'] + '.mp4'
            filenameog = video['title'] + '.mp4'
            filenamefix = re.sub(r'[^a-zA-Z0-9\u0590-\u05FF\u0627-\u064a\u0400-\u04FF \n\.-]', ' ', filenameog)
            filenamefix = filenamefix.replace("  ", " ")
            filenamefix = filenamefix.replace("  ", " ")
            folderfixfilename = 'ytdlAppData/' + filenamefix
            # check aws s3 bucket for the video
            if not (check_s3_file(filenamefix, s3_bucket_name)):
                # check locally for the video
                if not (os.path.isfile(folderfixfilename)):
                    # Download the video
                    video = ydl.extract_info(yt_link, download=True)
                    # Rename the video
                    logger.info(f"Renaming file {folderogfilename} to {folderfixfilename}")
                    os.rename(folderogfilename, folderfixfilename)
                    sleep(1)
                    # Upload the video to S3 bucket-folder and remove from local storage.
                    logger.info(f"Uploading {folderfixfilename} to S3 bucket {s3_bucket_name}")
                    upload_file(folderfixfilename, s3_bucket_name)
                    os.remove(folderfixfilename)
                    return filenamefix
                else:
                    # Upload the video to S3 bucket-folder and remove from local storage.
                    # added but not implemented code to check to compare local file and s3 file sizes and replace if not matching with the local copy.
                    logger.info(f"Uploading {folderfixfilename} to S3 bucket {s3_bucket_name}")
                    upload_file(folderfixfilename, s3_bucket_name)
                    os.remove(folderfixfilename)
                    return filenamefix
            else:  # File exists in S3 bucket-folder, no download needed.
                if os.path.isfile(folderfixfilename):
                    # If the video exists locally, delete.
                    os.remove(folderfixfilename)
                return filenamefix
    except Exception as e:
        logger.error(e)
        return "Error: Server error has occurred"


def is_string_an_url(url_string: str) -> bool:
    # Function to validate if input is a URL
    result = validators.url(url_string)
    if isinstance(result, ValidationFailure):
        return False
    return result


def send_videos_from_bot_queue(worker_to_bot_queue, bucket_name):
    i = 0
    # Start looping with sleep every 10 seconds to check for messages in queue.
    while True:
        dtnow = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
        i += 1
        try:
            messages = worker_to_bot_queue.receive_messages(
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5
            )
            logger.info(f'msgs received from queue: {len(messages)}')
            if messages:
                logger.info(f'Attempting to send video to user via chat')
                for msg in messages:
                    logger.info(f'processing message {msg}')
                    video_filename = msg.body
                    logger.info(f'{video_filename} = filename')
                    if video_filename == "Error: Server error has occurred":
                        chat_id = msg.message_attributes.get('chat_id').get('StringValue')
                        telegram_api_send_single_message(chat_id, f'There was an error trying to complete your request.')
                        # delete message from the queue after it was handled
                        response = worker_to_bot_queue.delete_messages(Entries=[{
                            'Id': msg.message_id,
                            'ReceiptHandle': msg.receipt_handle
                        }])
                        if 'Successful' in response:
                            logger.info(f'msg {msg} has been handled successfully')
                    else:
                        chat_id = msg.message_attributes.get('chat_id').get('StringValue')
                        video_presigned_url = generate_presigned_url(video_filename, bucket_name, None)
                        temp_string = f'<a href = "{video_presigned_url}">Link</a>'
                        telegram_api_send_single_message(chat_id, f'The following download link will be available for the next few minutes: {temp_string}')
                        # delete message from the queue after it was handled
                        response = worker_to_bot_queue.delete_messages(Entries=[{
                            'Id': msg.message_id,
                            'ReceiptHandle': msg.receipt_handle
                        }])
                        if 'Successful' in response:
                            logger.info(f'msg {msg} has been handled successfully')
                        logger.info(f'file has been downloaded')
        except botocore.exceptions.ClientError as err:
            logger.exception(f"Couldn't receive messages {err}")
        # every 60 seconds update log to show that thread is running.
        if i == 6:
            logger.info(f'Thread is running as of {dtnow}, checking queue every 10 seconds, this message repeats every 60 seconds')
            i = 0
        sleep(10)


def check_s3_file(key_filename, s3_bucket_name):
    # Function to check if requested file(path) exists in S3 bucket
    s3_prefix = 'ytdlAppData/' + key_filename
    s3 = boto3.resource('s3')
    try:
        s3.Object(s3_bucket_name, s3_prefix).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            # The object does not exist.
            return False
        else:
            # Something else has gone wrong.
            raise
    else:
        # The object does exist.
        return True


def check_s3_object_filesize(key_filename, s3_bucket_name):
    # Function to check if requested file(path) exists in S3 bucket
    s3_prefix = 'ytdlAppData/' + key_filename
    s3 = boto3.resource('s3')
    try:
        response = s3.head_object(s3_bucket_name, key_filename)
        size = response['ContentLength']
    except ClientError as e:
        logger.error(e)
        raise
    else:
        # Return the file size of the object
        return size


def upload_file(key_filename, bucket, object_name=None):
    # Function to upload file(path) to S3 bucket
    s3_prefix = key_filename
    # Upload the file
    s3_client = boto3.client('s3')
    # If S3 object_name was not specified, use key_filename
    if object_name is None:
        object_name = s3_prefix
    try:
        response = s3_client.upload_file(key_filename, bucket, s3_prefix)
    except ClientError as e:
        logger.error(e)
        return False
    return True


def download_file(key_filename, bucket, object_name=None):
    # Function to download requested file(path) from S3 bucket
    s3_prefix = 'ytdlAppData/' + key_filename
    # Upload the file
    s3_client = boto3.client('s3')
    # If S3 object_name was not specified, use key_filename
    if object_name is None:
        object_name = s3_prefix
    try:
        response = s3_client.download_file(bucket, object_name, s3_prefix)
    except ClientError as e:
        logger.error(e)
        return False
    return True


def generate_presigned_url(key_filename, bucket, object_name=None):
    # Function to generated expiring presigned URL for requested file(path) from S3 bucket
    s3_prefix = 'ytdlAppData/' + key_filename
    s3_client = boto3.client("s3", 'eu-central-1', config=Config(signature_version='s3v4'))
    # If S3 object_name was not specified, use key_filename
    if object_name is None:
        object_name = s3_prefix
    try:
        response = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': s3_prefix}, ExpiresIn=3600)
    except ClientError as e:
        logger.error(e)
        return False
    return response


def telegram_api_send_single_message(chat_id, text):
    # Send 
    with open('secrets/.telegramToken') as f:
        _token = f.read()
    url = f"https://api.telegram.org/bot{_token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    resp = requests.get(url, params=params)
    # Throw an exception if Telegram API fails
    resp.raise_for_status()
