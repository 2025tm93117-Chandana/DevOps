pipeline {
    agent any

    triggers {
        githubPush()
        pollSCM('H/5 * * * *')
    }

    options {
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
    }

    environment {
        VENV = '.venv'
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh '''
                    python3 -m venv ${VENV}
                    . ${VENV}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    python -m py_compile app.py
                '''
            }
        }
    }

    post {
        success { echo 'Build succeeded.' }
        failure { echo 'Build failed.' }
    }
}
