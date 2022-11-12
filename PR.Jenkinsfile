pipeline {
    agent any

    stages {
        stage('Unittest') {
            steps {
                sh '''
                pip install -r requirements.txt
                python -m pytest --junitxml results.xml tests
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'results.xml'
                }
            }
        }
        stage('Functional test') {
            steps {
                echo "testing"
            }
        }
    }
}