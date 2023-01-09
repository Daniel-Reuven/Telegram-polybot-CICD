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
        IMAGE_NAME = "daniel-reuven-worker-prod"
        APP_ENV = "prod"
    }
    stages {
        stage('Trigger Build') {
            steps {
                sh '''
                aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin $REGISTRY_URL
                echo $APP_ENV > env.txt
                docker build -t $IMAGE_NAME:$IMAGE_TAG . -f services/worker/Dockerfile --label "author=daniel-reuven"
                docker tag $IMAGE_NAME:$IMAGE_TAG $REGISTRY_URL/$IMAGE_NAME:$IMAGE_TAG
                docker push $REGISTRY_URL/$IMAGE_NAME:$IMAGE_TAG
                '''
            }
            post {
                always {
                    sh '''
                       docker images | grep "daniel-reuven-worker-prod" | awk '{print $1 ":" $2}' | xargs docker rmi
                    '''
                }
            }
        }
        stage('Trigger Post List') {
            steps {
                build job: 'prod/WorkerBuildResults', wait: false, parameters: [
                    string(name: 'WORKER_IMAGE_NAME', value: "${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}")
                ]
            }
        }
    }
}