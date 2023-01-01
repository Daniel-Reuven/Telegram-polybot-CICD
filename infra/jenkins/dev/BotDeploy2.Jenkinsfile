properties([
            parameters([[$class: 'ChoiceParameter', choiceType: 'PT_SINGLE_SELECT', filterLength: 1, filterable: false, name: 'BOT_IMAGE_NAME', randomName: 'choice-parameter-7498300564399', script: [$class: 'GroovyScript', fallbackScript: [classpath: [], oldScript: '', sandbox: true, script: 'return [\'error\']'], script: [classpath: [], oldScript: '', sandbox: true, script: '''try{
def build = jenkins.model.Jenkins.instance.getItemByFullName(\'dev/BotBuildPost\').getLastSuccessfulBuild().getBuildVariables()["BOT_IMAGE_NAME"]
return [build]
} catch (Exception e){return [e.getMessage()]}''']]]])])

pipeline {
    agent {
        docker {
            image '352708296901.dkr.ecr.eu-central-1.amazonaws.com/daniel-reuven-jenkins-ecr:latest'
            args  '--user root -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    environment {
        APP_ENV = "dev"
        BUILD_ENV = "${params.BOT_IMAGE_NAME}"
    }
    stages {
        stage('Bot Deploy') {
            steps {
            script{
                    println(BUILD_ENV)
                    println(APP_ENV)
            }
                withCredentials([
                    string(credentialsId: 'telegram-bot-token', variable: 'TELEGRAM_TOKEN'),
                    file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    sh '''
                    K8S_CONFIGS=infra/k8s

                    # replace placeholders in YAML k8s files
                    bash common/replaceInFile.sh $K8S_CONFIGS/bot.yaml APP_ENV $APP_ENV
                    bash common/replaceInFile.sh $K8S_CONFIGS/bot.yaml BOT_IMAGE $BUILD_ENV
                    bash common/replaceInFile.sh $K8S_CONFIGS/bot.yaml TELEGRAM_TOKEN $(echo -n $TELEGRAM_TOKEN | base64)

                    # apply the configurations to k8s cluster
                    kubectl apply --kubeconfig ${KUBECONFIG} -f $K8S_CONFIGS/bot.yaml
                    '''
                }
            }
        }
    }
}