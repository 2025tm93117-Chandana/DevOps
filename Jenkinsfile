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
                echo "Checking Out SourceCode"
                cleanWs()
                checkout scm
            }
        }

        stage('Build') {
            steps {
                echo "installing Python Dependencies"
                sh '''
                    python3 -m venv ${VENV}
                    . ${VENV}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    python -m py_compile app.py
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    . ${VENV}/bin/activate
                    python -m pytest -v --junitxml=test-results.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results.xml'
                }
            }
        }
    }

    post {
        success { echo 'Build succeeded.' }
        failure { echo 'Build failed.' }
    }
}
