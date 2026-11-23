pipeline {
    agent any

    triggers {
        githubPush()
        pollSCM('* * * * *')
    }

    options {
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
    }

    environment {
        VENV = '.venv'
        IMAGE = 'aceest-fitness'
        DOCKER_HUB_REPO = '2025tm93117/acefitness'
        DOCKER_HUB_CREDENTIALS = 'dockerhub-credentials'
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

        
        stage('Code Quality') {
            environment {
                PATH = "/opt/sonar-scanner/bin:${env.PATH}"
                SONAR_HOST_URL = 'http://localhost:9000'
            }
            steps {
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    sh 'sonar-scanner -Dsonar.host.url=${SONAR_HOST_URL} -Dsonar.token=${SONAR_TOKEN} -Dsonar.qualitygate.wait=true'
                }
            }
        }

         stage('Docker Build') {
            steps {
                sh 'docker build -t ${IMAGE}:${BUILD_NUMBER} -t ${IMAGE}:latest -t ${DOCKER_HUB_REPO}:3.0.0-build${BUILD_NUMBER} .'
            }
        }

        stage('Docker Test') {
            steps {
                sh 'docker run --rm ${DOCKER_HUB_REPO}:3.0.0-build${BUILD_NUMBER} python -m pytest -q'
            }
        }

        stage('Docker Push') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                        sh '''
                            # Create a temporary script file to avoid Jenkins masking issues
                            cat > /tmp/docker_push.sh << 'SCRIPT'
#!/bin/bash
set -e
mkdir -p ~/.docker
rm -f ~/.docker/config.json
echo "{\"auths\":{\"https://index.docker.io/v1/\":{\"auth\":\"$(echo -n "$1:$2" | base64 -w 0)\"}}}" > ~/.docker/config.json
chmod 600 ~/.docker/config.json
docker push $3:3.0.0-build$4
docker tag $3:3.0.0-build$4 $3:latest
docker push $3:latest
rm -f ~/.docker/config.json
SCRIPT
                            chmod +x /tmp/docker_push.sh
                            /tmp/docker_push.sh "${DOCKER_USER}" "${DOCKER_PASS}" "${DOCKER_HUB_REPO}" "${BUILD_NUMBER}"
                            rm -f /tmp/docker_push.sh
                        '''
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    docker rm -f ${IMAGE} || true
                    docker run -d --name ${IMAGE} -p 5000:5000 \
                        -v aceest_data:/data --restart unless-stopped ${IMAGE}:latest
                    for i in $(seq 1 10); do
                        curl -fsS http://localhost:5000/health && exit 0
                        sleep 2
                    done
                    docker logs ${IMAGE}
                    exit 1
                '''
            }
        }
    }

    post {
        success { echo 'Build succeeded.' }
        failure { echo 'Build failed.' }
    }
}
