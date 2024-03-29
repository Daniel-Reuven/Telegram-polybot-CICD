import os
import boto3
import botocore
import requests
import yt_dlp
import re
import validators
import pytz
import json
from urllib import parse
from botocore.exceptions import ClientError
from botocore.config import Config
from loguru import logger
from time import sleep
from datetime import datetime, timedelta
from validators import ValidationFailure


class MyLogger:
    def debug(self, msg):
        # For compatibility with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            logger.debug(f'yt-dlp: {msg}'.format())
            pass
        else:
            self.info(msg)

    def info(self, msg):
        logger.info(f'yt-dlp: {msg}'.format())
        pass

    def warning(self, msg):
        logger.warning(f'yt-dlp: {msg}'.format())
        pass

    def error(self, msg):
        logger.error(f'yt-dlp: {msg}'.format())


def download_youtube_video_to_s3(yt_link, s3_bucket_name, quality_var):
    try:
        # Parameters for youtube_dl use
        qformat = f'bestvideo[height<={quality_var}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        ydl = {
            'noplaylist': 'True',
            'logger': MyLogger(),
            'verbose': False,
            'format': qformat,
            'writethumbnail': True,
            'postprocessors': [{
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            }],
            'outtmpl': './ytdlAppData/%(id)s.%(ext)s',
        }
        with yt_dlp.YoutubeDL(ydl) as ydl:
            # Clean local cache
            ydl.cache.remove()
            # Get info about the video via URL
            tempvideo = ydl.extract_info(yt_link, download=False)
            folder_filename = 'ytdlAppData/' + tempvideo['id'] + '.mp4'
            filenameclean = tempvideo['title']
            # Manipulate filename to remove unwanted characters
            s = re.sub(r'[^a-zA-Z0-9\u0590-\u05FF\u0627-\u064a\u0400-\u04FF \n\.-]', '', filenameclean)
            # Remove double spaces
            while '  ' in s:
                s = s.replace("  ", " ")
            # Remove dots at the end of title.
            while s.endswith('.'):
                s = s[:len(s) - 1]
            if s.endswith(' '):
                s = s[:len(s) - 1]
            if not len(s) == 0:
                final_filename = '[' + tempvideo['id'] + ']' + s + '.mp4'
            else:
                final_filename = '[' + tempvideo['id'] + ']' + 'title contains illegal characters' + '.mp4'
            folder_final_filename = 'ytdlAppData/' + final_filename
            # check aws s3 bucket for the video
            bucket_file_check = aws_s3_bucket_check_is_file(final_filename, s3_bucket_name)
            if not bucket_file_check:
                # check locally for the video
                if not (os.path.isfile(folder_final_filename)):
                    # Download the video
                    ydl.extract_info(yt_link, download=True)
                    # Rename the video
                    logger.info(f'Renaming file "{folder_filename}" to "{folder_final_filename}"')
                    os.rename(folder_filename, folder_final_filename)
                    logger.info(f'Renaming file "{folder_filename}" to "{folder_final_filename}" - Completed')
                # Upload the video to S3 bucket-folder
                logger.info(f'Uploading "{folder_final_filename}" to S3 bucket "{s3_bucket_name}"')
                aws_s3_bucket_upload_media_file(folder_final_filename, s3_bucket_name)
                logger.info(f'Uploading "{folder_final_filename}" to S3 bucket "{s3_bucket_name}" - Completed')
                # Remove local file
                logger.info(f'Deleting local file "{folder_final_filename}"')
                os.remove(folder_final_filename)
                logger.info(f'Deleting local file "{folder_final_filename}" - Completed')
                return final_filename
            else:  # File exists in S3 bucket-folder, and is available until lifecycle rule applies.
                logger.info(f'File "{folder_final_filename}" already exists in AWS S3 Bucket "{s3_bucket_name}", returning filename')
                if os.path.isfile(folder_final_filename):
                    # If the video exists locally, delete
                    logger.info(f'Deleting local file "{folder_final_filename}"')
                    os.remove(folder_final_filename)
                    logger.info(f'Deleting local file "{folder_final_filename}" - Completed')
                return final_filename
    except Exception as e:
        logger.error(e)
        return "Error: Server error has occurred"


def send_videos_from_bot_queue(worker_to_bot_queue, bucket_name):
    i = 0
    # Start looping with sleep every 10 seconds to check for messages in queue
    while True:
        dtnow = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
        i += 1
        try:
            messages = worker_to_bot_queue.receive_messages(
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5
            )
            logger.info(f'msgs received from queue: {len(messages)} - {dtnow}')
            if messages:
                logger.info(f'Attempting to process msg to customer')
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
                        video_presigned_url = aws_s3_bucket_generate_presigned_url(video_filename, bucket_name, None)
                        temp_string = f'<a href = "{video_presigned_url}">{video_filename}</a>'
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
        # every 60 seconds update log to show that thread is running
        if i == 6:
            logger.info(f'Process is running as of {dtnow}, checking queue every 10 seconds, this message repeats every 60 seconds(5-sec delay for each request running every '
                        f'10-sec)')
            i = 0
        sleep(10)


def sync_quality_file(s3_bucket_name, _token):
    # Start looping with sleep every 15 minutes
    while True:
        try:
            dt_now = datetime.now()
            dt_file = aws_s3_bucket_check_file_modify_date('quality_file.json', s3_bucket_name)
            utc = pytz.UTC
            dt_file = dt_file.replace(tzinfo=utc)
            dt_now = dt_now.replace(tzinfo=utc)
            if dt_file >= (dt_now - timedelta(minutes=1)):
                logger.info('Updates to quality file detected, attempting to update settings.')
                aws_s3_bucket_download_file2('quality_file.json', s3_bucket_name)
                logger.info('Successfully updated quality file.')
                # Possible code for informing dev of successful change
                with open('/app/secret.json') as json_handler:
                    secret_data = json.load(json_handler)
                dev_chat_id = secret_data["dev_chat_id"]
                json_handler.close()
                telegram_api_send_single_message(dev_chat_id, 'Backend: quality updated successfully')
            logger.info(f'Sync process is running as of {dt_now}, checking for changes every 1 minute.')
        except Exception as e:
            logger.error(e)
            logger.info(dt_file.astimezone().tzinfo)
            logger.info(dt_now.astimezone().tzinfo)
            # Possible code for informing dev of failed change
            with open('/app/secret.json') as json_handler:
                secret_data = json.load(json_handler)
            dev_chat_id = secret_data["dev_chat_id"]
            json_handler.close()
            telegram_api_send_single_message(dev_chat_id, f'Backend: Something went wrong - {e}')
        sleep(60)


def initial_download(s3_bucket_name, filename):
    # Function to initial download sensitive files from s3 bucket to pods
    try:
        logger.info(f'Initial download of "{filename}" - Starting')
        aws_s3_bucket_download_file2(filename, s3_bucket_name)
        logger.info(f'Initial download of "{filename}" - Completed')
    except botocore.exceptions.ClientError as e:
        logger.error(f'Initial download of "{filename}" failed.')


def is_string_an_url(url_string: str) -> bool:
    # Function to validate if input string is a URL or if contains playlist
    result = validators.url(url_string)
    if isinstance(result, ValidationFailure) or '/playlist?list=' in url_string:
        return False
    return result


def aws_s3_bucket_check_is_file(key_filename, s3_bucket_name):
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


def aws_s3_bucket_check_file_modify_date(s3_prefix, s3_bucket_name):
    # Function to check if requested file has been modified and return last modified date.
    try:
        datetime_value = boto3.client('s3').head_object(Bucket=s3_bucket_name, Key=s3_prefix)['LastModified']
    except botocore.exceptions.ClientError as e:
        logger.error(e)
        return e
    else:
        # Return the last modified date of the file
        return datetime_value


def aws_s3_bucket_check_object_filesize(key_filename, s3_bucket_name):
    # Function to check and return requested file(path) size
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


def aws_s3_bucket_upload_media_file(key_filename, bucket, object_name=None):
    # Function to upload file(path) to S3 bucket
    s3_prefix = key_filename
    tags = {"Cached": "Yes"}
    # Upload the file
    s3_client = boto3.client('s3')
    # If S3 object_name was not specified, use key_filename
    if object_name is None:
        object_name = s3_prefix
    try:
        response = s3_client.upload_file(key_filename, bucket, s3_prefix, ExtraArgs={"Tagging": parse.urlencode(tags), "ContentDisposition": "attachment"})
        logger.info(f'uploaded {s3_prefix} with tags: {tags} and metadata "ContentDisposition": "attachment" to force download')
    except ClientError as e:
        logger.error(e)
        return False
    return True


def aws_s3_bucket_upload_file2(bucket_name, local_file, s3_path):
    # Function to upload file(path) to S3 bucket
    s3 = boto3.resource('s3')
    try:
        s3.Bucket(bucket_name).upload_file(local_file, s3_path)
        logger.info(f'uploaded modified quality file')
    except ClientError as e:
        logger.error(e)
        return False
    return True


def aws_s3_bucket_download_file(key_filename, bucket, object_name=None):
    # Function to download requested file(path) from S3 bucket
    s3_prefix = 'ytdlAppData/' + key_filename
    s3_client = boto3.client('s3')
    # If S3 object_name was not specified, use key_filename
    if object_name is None:
        object_name = s3_prefix
    try:
        s3_client.download_file(bucket, object_name, s3_prefix)
    except ClientError as e:
        logger.error(e)
        return False
    return True


def aws_s3_bucket_download_file2(key_filename, bucket):
    # Function to download requested file(path) from S3 bucket
    s3_prefix = key_filename
    s3_client = boto3.client('s3')
    try:
        s3_client.download_file(bucket, key_filename, s3_prefix)
    except ClientError as e:
        logger.error(e)


def aws_s3_bucket_generate_presigned_url(key_filename, bucket, object_name=None):
    # Function to generated expiring presigned URL for requested file(path) from S3 bucket
    s3_prefix = 'ytdlAppData/' + key_filename
    s3_client = boto3.client("s3", 'eu-central-1', config=Config(signature_version='s3v4'))
    # If S3 object_name was not specified, use key_filename
    if object_name is None:
        object_name = s3_prefix
    try:
        response = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': s3_prefix}, ExpiresIn=3600)
        logger.info(f'generated presigned URL for {s3_prefix}')
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
    try:
        resp = requests.get(url, params=params)
        logger.info(f'Attempting to send msg to {chat_id}')
    except requests.exceptions.RequestException as e:
        # Throw an exception if Telegram API fails
        logger.error(f'Status: {e}'.format())
