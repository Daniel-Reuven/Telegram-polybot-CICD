import time
from yt_dlp import YoutubeDL
from loguru import logger


def search_download_youtube_video(video_name, num_results=1):
    """
    This function downloads the first num_results search results from Youtube
    :param video_name: string of the video name
    :param num_results: integer representing how many videos to download
    :return: list of paths to your downloaded video files
    """
    with YoutubeDL() as ydl:
        videos = ydl.extract_info(f"ytsearch{num_results}:{video_name}", download=True)['entries']

    return [ydl.prepare_filename(video) for video in videos]


def calc_backlog_per_instance(sqs_queue_client, asg_client, asg_group_name):
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

        # TODO send the backlog_per_instance metric to cloudwatch

        time.sleep(60)
