properties(
[
    parameters(
    [
        [
            $class: 'ChoiceParameter',
            choiceType: 'PT_SINGLE_SELECT',
            filterLength: 1,
            filterable: false,
            name: 'WORKER_IMAGE_NAME',
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
                            def job = jenkins.model.Jenkins.instance.getItemByFullName('dev/WorkerBuildResults')
                            job.builds.each {
                                def build = it
                                builds.add(build.getBuildVariables()["WORKER_IMAGE_NAME"])
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
            // TODO build & push your Jenkins agent image, place the URL here
            image '352708296901.dkr.ecr.eu-central-1.amazonaws.com/daniel-reuven-jenkins-ecr:latest'
            args  '--user root -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    environment {
        APP_ENV = "dev"
        BUILD_ENV = "${params.WORKER_IMAGE_NAME}"
    }
    stages {
        stage('Worker Deploy') {
            steps {
                withCredentials([
                    file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')
                ]) {
                    sh '''
                    K8S_CONFIGS=infra/k8s

                    # replace placeholders in YAML k8s files
                    bash common/replaceInFile.sh $K8S_CONFIGS/worker.yaml APP_ENV $APP_ENV
                    bash common/replaceInFile.sh $K8S_CONFIGS/worker.yaml WORKER_IMAGE $BUILD_ENV

                    # authenticate with AWS EKS Cluster
                    aws eks update-kubeconfig --region eu-central-1 --name dr-project-eks-cluster

                    # apply the configurations to k8s cluster
                    kubectl apply -f $K8S_CONFIGS/worker.yaml
                    '''
                }
            }
        }
    }
}