pipeline {
    agent {
        docker {
            // TODO build & push your Jenkins agent image, place the URL here
            image '<jenkins-agent-image>'
            args  '--user root -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        APP_ENV = "prod"
    }

    // TODO prod bot deploy pipeline

}