//def build = Jenkins.getInstance().getItemByFullName('dev/BotBuildPost').getLastSuccessfulBuild()
// get parameters
//def String MYVAR = build.getEnvironment(TaskListener.NULL).get('BOT_IMAGE_NAME')
pipeline {
    agent {
        docker {
            image '352708296901.dkr.ecr.eu-central-1.amazonaws.com/daniel-reuven-jenkins-ecr:latest'
            args  '--user root -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    environment {
        APP_ENV = "dev"
        BOT_IMAGE_NAME = ""
    }
    stages {
        stage('Set Variable') {
            steps {
                script {
                    def build = Jenkins.getInstance().getItemByFullName('dev/BotBuildPost').getLastSuccessfulBuild()
                    // get parameters
                    def String MYVAR = build.getEnvironment(TaskListener.NULL).get('BOT_IMAGE_NAME')
                    println("${MYVAR}")
                    BOT_IMAGE_NAME = "${MYVAR}"
                    println(BOT_IMAGE_NAME)
                }
            }
        }
        stage('Bot Deploy') {
            steps {
                withCredentials([
                    string(credentialsId: 'telegram-bot-token', variable: 'TELEGRAM_TOKEN'),
                    file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    sh '''
                    echo 1
                    echo $BOT_IMAGE_NAME
                    echo 2
                    K8S_CONFIGS=infra/k8s

                    # replace placeholders in YAML k8s files
                    bash common/replaceInFile.sh $K8S_CONFIGS/bot.yaml APP_ENV $APP_ENV
                    bash common/replaceInFile.sh $K8S_CONFIGS/bot.yaml BOT_IMAGE $BOT_IMAGE_NAME
                    bash common/replaceInFile.sh $K8S_CONFIGS/bot.yaml TELEGRAM_TOKEN $(echo -n $TELEGRAM_TOKEN | base64)

                    # apply the configurations to k8s cluster
                    kubectl apply --kubeconfig ${KUBECONFIG} -f $K8S_CONFIGS/bot.yaml
                    '''
                }
            }
        }
    }
}