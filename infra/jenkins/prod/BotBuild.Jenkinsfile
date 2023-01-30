pipeline {
    agent {
        docker {
            image '352708296901.dkr.ecr.eu-central-1.amazonaws.com/daniel-reuven-jenkins-ecr:latest'
            args  '--user root -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    environment {
        REGISTRY_URL = "352708296901.dkr.ecr.eu-central-1.amazonaws.com"
        IMAGE_TAG = "0.0.$BUILD_NUMBER"
        IMAGE_NAME = "daniel-reuven-bot-prod"
        APP_ENV = "prod"
        CODE_AUTHOR = "author=daniel-reuven"
    }
    stages {
        stage('Trigger Build') {
            steps {
                sh '''
                aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin $REGISTRY_URL
                echo $APP_ENV > env.txt
                docker build -t $IMAGE_NAME:$IMAGE_TAG . -f services/bot/Dockerfile --label $CODE_AUTHOR
                docker tag $IMAGE_NAME:$IMAGE_TAG $REGISTRY_URL/$IMAGE_NAME:$IMAGE_TAG
                docker push $REGISTRY_URL/$IMAGE_NAME:$IMAGE_TAG
                '''
            }
            post {
                always {
                    sh '''
                        echo 'Cleaning up image after pushing to ECR'
                        docker images | grep $IMAGE_NAME | awk '{print $1 ":" $2}' | xargs docker rmi
                    '''
                }
            }
        }
        stage('Trigger Post List') {
            steps {
                build job: 'prod/BotBuildResults', wait: false, parameters: [
                    string(name: 'BOT_IMAGE_NAME', value: "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}")
                ]
            }
        }
    }
}