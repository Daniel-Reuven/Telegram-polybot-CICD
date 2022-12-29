def build = Jenkins.getInstance().getItemByFullName('dev/BotBuild').getLastSuccessfulBuild()
// println(jobLog)
// def build = Jenkins.get().getItems(org.jenkinsci.plugins.workflow.job.WorkflowJob).find {it.displayName == 'dev/BotBuild'}?.getLastSuccessfulBuild()
// def test1 = build.buildVariables["DEV_BOT_IMAGE_NAME"]
def packageName = build.buildVariables.get("DEV_BOT_IMAGE_NAME")
// println BOT_IMAGE_NAME
// println("MY_PARAM in previous build: ${currentBuild.previousBuild.buildVariables["MY_PARAM_COPY"]}")
def newParameters = new ArrayList(currentParameters); newParameters << new NodeParameterValue("param_NODE", "Target node -- the node of the previous job")
println(test1)
pipeline {
    agent {
        docker {
            image '352708296901.dkr.ecr.eu-central-1.amazonaws.com/daniel-reuven-jenkins-ecr:latest'
            args  '--user root -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    environment {
        APP_ENV = "dev"
    }
    stages {
        stage('Bot Deploy') {
            steps {
                withCredentials([
                    string(credentialsId: 'telegram-bot-token', variable: 'TELEGRAM_TOKEN'),
                    file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    sh '''
                    echo 1
                    echo DEV_BOT_IMAGE_NAME
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