import json
import time
import os
import boto3
import botocore
import requests
from botocore.exceptions import ClientError
from botocore.config import Config
from yt_dlp import YoutubeDL
from loguru import logger
from time import sleep


def search_download_youtube_video(video_name, num_results, s3_bucket_name):
    """
    This function downloads the first num_results search results from Youtube
    :param s3_bucket_name:  string of the S3 bucket name
    :param video_name: string of the video name
    :param num_results: integer representing how many videos to download
    :return: list of paths to your downloaded video files
    """
    # Parameters for youtube_dl use
    ydl = {'noplaylist': 'True', 'format': 'bestvideo[ext=mp4]+bestaudio[ext=mp4]/mp4', 'outtmpl': '%(id)s.%(ext)s'}
    # Try to download and return list of video/s or error msg
    with YoutubeDL(ydl) as ydl:
        ydl.cache.remove()
        # 1. get a list of video file names with download=false parameter
        videos = ydl.extract_info(f"ytsearch{num_results}:{video_name}", download=False)['entries']
        for video in videos:
            localprefix = video['id'] + '.mp4'
            prefix = 'ytdlAppData/' + video['id'] + '.mp4'
            # check aws s3 bucket for file, then locally and act accordingly,prefix != ydl.prepare_filename(video)
            if not (check_s3_file(prefix, s3_bucket_name)):
                if not (os.path.isfile(ydl.prepare_filename(video))):
                    video_url = video['webpage_url']
                    ydl.extract_info(video_url, download=True)
                    upload_file(localprefix, s3_bucket_name)
                    os.remove(ydl.prepare_filename(video))
                else:
                    upload_file(localprefix, s3_bucket_name)
                    os.remove(ydl.prepare_filename(video))
            else:
                if os.path.isfile(ydl.prepare_filename(video)):
                    # download_file(prefix, s3_bucket_name)
                    os.remove(ydl.prepare_filename(video))
            sleep(1)
        return [ydl.prepare_filename(video) for video in videos]


def search_youtube_video(video_name, video_url):
    """
    This function downloads the first num_results search results from YouTube
    :param video_url: url of the video
    :param video_name: string of the video name
    :return: list of paths to your downloaded video files
    """
    # Parameters for youtube_dl use
    ydl = {'noplaylist': 'True', 'format': 'bestvideo[ext=mp4]+bestaudio[ext=mp4]/mp4', 'outtmpl': '%(id)s.%(ext)s'}
    # Try to download and return list of video/s or error msg
    with YoutubeDL(ydl) as ydl:
        ydl.cache.remove()
        if video_name is None:
            videos = ydl.extract_info(video_url, download=False)
            return videos
        elif video_url is None:
            videos = ydl.extract_info(f"ytsearch{1}:{video_name}", download=False)['entries']
            return videos


def calc_backlog_per_instance(sqs_queue_client, asg_client, asg_group_name, aws_region):
    while True:
        msgs_in_queue = int(sqs_queue_client.attributes.get('ApproximateNumberOfMessages'))
        asg_size = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_group_name])['AutoScalingGroups'][0]['DesiredCapacity']
        if msgs_in_queue == 0:
            backlog_per_instance = 0
        elif asg_size == 0:
            backlog_per_instance = 99
        else:
            backlog_per_instance = msgs_in_queue / asg_size
        logger.info(f'backlog per instance: {backlog_per_instance}')
        # Create CloudWatch client
        cloudwatch = boto3.client('cloudwatch', aws_region)
        # Put custom metrics
        cloudwatch.put_metric_data(
            Namespace='daniel-reuven-monitor-polybot-asg',
            MetricData=[
                {
                    'MetricName': 'backlog_per_instance',
                    'Value': backlog_per_instance,
                    'Unit': 'Count'
                },
            ]
        )
        time.sleep(60)


def send_videos_from_queue2(sqs_queue_client2, bucket_name):
    i = 0
    while True:
        i += 1
        try:
            messages = sqs_queue_client2.receive_messages(
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5
            )
            logger.info(f'msgs in videos queue: {len(messages)}')
            if messages:
                logger.info(f'Attempting to send video to user via chat')
                for msg in messages:
                    logger.info(f'processing message {msg}')
                    video_filename = msg.body
                    chat_id = msg.message_attributes.get('chat_id').get('StringValue')
                    video_presigned_url = generate_presigned_url(video_filename, bucket_name, None)
                    send_message(chat_id, f'The following download link will be available for the next few minutes: {video_presigned_url}')
                    # delete message from the queue after it was handled
                    response = sqs_queue_client2.delete_messages(Entries=[{
                        'Id': msg.message_id,
                        'ReceiptHandle': msg.receipt_handle
                    }])
                    if 'Successful' in response:
                        logger.info(f'msg {msg} has been handled successfully')
                logger.info(f'file has been downloaded')
        except botocore.exceptions.ClientError as err:
            logger.exception(f"Couldn't receive messages {err}")
        if i == 6:
            logger.info(f'Process is running, checking queue every 10 seconds, this msg repeats every 60 seconds')
            i = 0
        sleep(10)


def check_s3_file(key_filename, s3_bucket_name):
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


def upload_file(key_filename, bucket, object_name=None):
    s3_prefix = 'ytdlAppData/' + key_filename
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
    s3_prefix = 'ytdlAppData/' + key_filename
    # Upload the file
    s3_client = boto3.client("s3", config=Config(signature_version='s3v4'))

    # If S3 object_name was not specified, use key_filename
    if object_name is None:
        object_name = s3_prefix
    try:
        response = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': s3_prefix}, ExpiresIn=1800)
    except ClientError as e:
        logger.error(e)
        return False
    return response


def send_message(chat_id, text):
    with open('.telegramToken') as f:
        _token = f.read()
    url = f"https://api.telegram.org/bot{_token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": text,
    }
    resp = requests.get(url, params=params)
    # Throw an exception if Telegram API fails
    resp.raise_for_status()
