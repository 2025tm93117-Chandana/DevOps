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
                            # Remove existing credentials to avoid conflicts
                            rm -rf ~/.docker/config.json
                            
                            # Use docker credential helper approach with direct config file creation
                            mkdir -p ~/.docker
                            
                            # Workaround: Use base64 encoding with printf outside the subshell masking scope
                            echo -n "${DOCKER_USER}:${DOCKER_PASS}" > /tmp/creds.txt
                            cat /tmp/creds.txt | base64 -w 0 > /tmp/auth.b64
                            AUTH=$(cat /tmp/auth.b64)
                            rm /tmp/creds.txt /tmp/auth.b64
                            
                            cat > ~/.docker/config.json << DOCKER_CONFIG
{
  "auths": {
    "https://index.docker.io/v1/": {
      "auth": "${AUTH}"
    }
  }
}
DOCKER_CONFIG
                            
                            chmod 600 ~/.docker/config.json
                            cat ~/.docker/config.json
                            
                            # Push images
                            docker push ${DOCKER_HUB_REPO}:3.0.0-build${BUILD_NUMBER}
                            docker tag ${DOCKER_HUB_REPO}:3.0.0-build${BUILD_NUMBER} ${DOCKER_HUB_REPO}:latest
                            docker push ${DOCKER_HUB_REPO}:latest
                            
                            # Cleanup
                            rm -rf ~/.docker
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
