properties(
[
    parameters(
    [
        [
            $class: 'ChoiceParameter',
            choiceType: 'PT_SINGLE_SELECT',
            filterLength: 1,
            filterable: false,
            name: 'BOT_IMAGE_NAME',
            randomName: 'choice-parameter-7498300564399',
            script:
            [
                $class: 'GroovyScript',
                fallbackScript:
                [
                        classpath: [],
                        oldScript: '',
                        sandbox: true,
                        script:
                        'return [\'error\']'
                ],
                script:
                [
                        classpath: [],
                        oldScript: '',
                        sandbox: true,
                        script:
                            '''
                            try{
                            def builds = []
                            def job = jenkins.model.Jenkins.instance.getItemByFullName('dev/BotBuildResults')
                            job.builds.each {
                                def build = it
                                builds.add(build.getBuildVariables()["BOT_IMAGE_NAME"])
                            }
                            builds.unique();
                            return builds
                            }
                            catch (Exception e){return [e.getMessage()]}
                            '''
                ]
            ]
        ]
    ])
])
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

                    # authenticate with AWS EKS Cluster
                    aws eks update-kubeconfig --region eu-central-1 --name dr-project-eks-cluster

                    # apply the configurations to k8s cluster
                    kubectl apply --kubeconfig ${KUBECONFIG} -f $K8S_CONFIGS/bot.yaml
                    '''
                }
            }
        }
    }
}