# Telegram-Polybot

### Features
- Supports downloading of videos from links and converting to h265 video format.
- Supports downloading of videos from links and converting to mp3 format.
- Supports Uploading content to Mega drive and share download links.
- Supports Hebrew/English/Russian/Arabic languages in files names.
- Supports Whitelist / Blacklist features



### Installation:

- [ ] Use Python 3.10 or above
- [ ] Install FFMPEG(not python-ffmpeg)
- [ ] Install relevant packages from requirements.txt file:
`$ pip install -r requirements.txt`



### File Modification Requireds:
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
| quality      | (String)Video Quality resolution(720/1080/4096)       |

- [ ] Modify common/config.json dev_chat_id

| Key                           | Value                                             |
| ---------                     |---------------------------------------------------|
| aws_region                    | (String)AWS Region ID                             |
| bot_to_worker_queue_name      | (String)AWS "Incoming" SQS Queue Name             |
| worker_to_bot_queue_name      | (String)AWS "Outgoing" SQS Queue Name             |
| bucket_name                   | (String)AWS S3 Bucket Name for data/quality files |

- [ ] Modify jenkins's agent section from all jenkines pipelines files.
    * these files contains reference to jenkins agent docker image url.

            agent {
                docker {
                    image '352708296901.dkr.ecr.eu-central-1.amazonaws.com/daniel-reuven-jenkins-ecr:latest'
                    args  '--user root -v /var/run/docker.sock:/var/run/docker.sock'
                }
            }
- [ ] Modify variable/references in BotBuild jenkines pipelines files:
    * infra/jenkins/dev/BotBuild.Jenkinsfile
    * infra/jenkins/prod/BotBuild.Jenkinsfile
    * infra/jenkins/dev/WorkerBuild.Jenkinsfile
    * infra/jenkins/prod/WorkerBuild.Jenkinsfile

| Variable/reference | Value                        |
| --------------|-----------------------------------|
| REGISTRY_URL  | (String)AWS ECR to push images to |
| IMAGE_NAME    | (String)Name of image             |
| CODE_AUTHOR    | (String)Name of Author for docker images management and cleanup             |
- [ ] Modify parameters in Workerbuild jenkines pipelines files:
    * infra/jenkins/dev/BotDeploy.Jenkinsfile
    * infra/jenkins/prod/BotDeploy.Jenkinsfile
    * infra/jenkins/dev/WorkerDeploy.Jenkinsfile
    * infra/jenkins/prod/WorkerDeploy.Jenkinsfile

| Variable/reference | Value                        |
| --------------|-----------------------------------|
| EKS_NAME      | (String)Name of the AWS EKS       |
