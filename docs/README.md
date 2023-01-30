# Telegram-Polybot

### Features
- Supports downloading of videos from links and converting to h265 video format.
- Supports downloading of videos from links and converting to mp3 format.
- Supports Uploading content to Mega drive and share download links.
- Supports Hebrew/English/Russian/Arabic languages in files names.



### Installation:

- [ ] Use Python 3.10 or above
- [ ] Install FFMPEG(not python-ffmpeg)
- [ ] Install relevant packages from requirements.txt file:
`$ pip install -r requirements.txt`
- [ ] Remove "-example" from files under config folder
- [ ] Modify infra/Helm/* helm files if needed
- [ ] Configure "secret.json" and update dev_chat_id key's value and then upload to AWS S3 Bucket:

| Key                   | Value                                                      |
| ---------             |------------------------------------------------------------|
| dev_chat_id           | (String)Telegram Chat ID of the Admin/Developer of the bot |
| version               | (String)1.7                                                |
- [ ] Configure "quality_file.json" and update dev_chat_id key's value and then upload to AWS S3 Bucket:

| Key          | Value                                              |
| ---------    |----------------------------------------------------|
| quality      | (Int)Video Quality resolution(either 1080 or 4096) |

- [ ] Modify common/config.json dev_chat_id

| Key                           | Value                                             |
| ---------                     |---------------------------------------------------|
| aws_region                    | (String)AWS Region ID                             |
| bot_to_worker_queue_name      | (String)AWS "Incoming" SQS Queue Name             |
| worker_to_bot_queue_name      | (String)AWS "Outgoing" SQS Queue Name             |
| bucket_name                   | (String)AWS S3 Bucket Name for data/quality files |
