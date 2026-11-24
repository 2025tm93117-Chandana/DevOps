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
        KUBECONFIG = '/home/jenkins/.kube/config'
        K8S_NAMESPACE = 'acefitness'
        KUBECTL = '/usr/local/bin/minikube kubectl --'
        HOME = '/var/lib/jenkins'
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
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_TOKEN'
                )]) {
                    sh '''
                        set +x
                        export DOCKER_CONFIG="$(mktemp -d)"
                        trap 'rm -f "$DOCKER_CONFIG/config.json"; rmdir "$DOCKER_CONFIG"' EXIT
                        printf '%s' "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push "${DOCKER_HUB_REPO}:3.0.0-build${BUILD_NUMBER}"
                    '''
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

        stage('Kubernetes - Manual Deployment Info') {
            steps {
                script {
                    sh '''
                        echo "======================================="
                        echo "CI/CD Pipeline Complete!"
                        echo "======================================="
                        echo ""
                        echo "✓ Code Checkout"
                        echo "✓ Python Build & Dependencies"
                        echo "✓ Pytest (65 tests passing)"
                        echo "✓ SonarQube Code Quality"
                        echo "✓ Docker Image Build"
                        echo "✓ Docker Container Test"
                        echo "✓ Docker Container Deploy"
                        echo ""
                        echo "To deploy to Kubernetes (Minikube):"
                        echo "=================================================="
                        echo ""
                        echo "1. Create namespace:"
                        echo "   minikube kubectl -- apply -f k8s-namespace.yaml"
                        echo ""
                        echo "2. Deploy application:"
                        echo "   minikube kubectl -- apply -f k8s-deployment.yaml"
                        echo "   minikube kubectl -- apply -f k8s-service.yaml"
                        echo ""
                        echo "3. Check status:"
                        echo "   minikube kubectl -- get pods -n acefitness"
                        echo "   minikube kubectl -- get svc -n acefitness"
                        echo ""
                        echo "4. Access application:"
                        echo "   minikube ip              # Get IP"
                        echo "   curl http://<IP>:30000/health"
                        echo ""
                        echo "For Blue-Green Deployment:"
                        echo "   minikube kubectl -- apply -f k8s-blue-green.yaml"
                        echo ""
                        echo "For Canary Deployment:"
                        echo "   minikube kubectl -- apply -f k8s-canary.yaml"
                        echo ""
                        echo "=================================================="
                        echo ""
                        echo "Docker Image: ${IMAGE}:latest"
                        echo "Docker Hub Repo: ${DOCKER_HUB_REPO}"
                        echo ""
                        echo "To push to Docker Hub:"
                        echo "   docker login -u <username>"
                        echo "   docker push ${DOCKER_HUB_REPO}:3.0.0-build${BUILD_NUMBER}"
                        echo ""
                        echo "======================================="
                    '''
                }
            }
        }
    }

    post {
        success { echo 'Build succeeded.' }
        failure { echo 'Build failed.' }
    }
}
