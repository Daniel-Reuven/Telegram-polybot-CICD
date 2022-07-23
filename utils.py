# import logging
import time
import os
import boto3
import botocore
from botocore.exceptions import ClientError
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
            # if video['duration'] >= 900:
            #     return "Error, selected track/s are above predefined duration limit"
            # if video['duration'] <= 0.1:
            #     return "Error, selected track/s are below predefined duration limit"
            localprefix = video['id'] + '.mp4'
            prefix = 'ytdlAppData/' + video['id'] + '.mp4'
            # print(s3_bucket_name)
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
