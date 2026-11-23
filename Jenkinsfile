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
                echo "Docker image built successfully: ${DOCKER_HUB_REPO}:3.0.0-build${BUILD_NUMBER}"
                echo "Note: Manual docker login required for push due to Jenkins credential handling"
                echo "To push manually run: docker push ${DOCKER_HUB_REPO}:3.0.0-build${BUILD_NUMBER}"
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

        stage('Kubernetes - Create Namespace') {
            steps {
                script {
                    sh '''
                        echo "Creating Kubernetes namespace..."
                        ${KUBECTL} apply -f k8s-namespace.yaml || true
                        ${KUBECTL} get namespace ${K8S_NAMESPACE}
                    '''
                }
            }
        }

        stage('Kubernetes - Deploy Application') {
            steps {
                script {
                    sh '''
                        echo "Deploying application to Kubernetes..."
                        ${KUBECTL} apply -f k8s-deployment.yaml
                        ${KUBECTL} apply -f k8s-service.yaml
                        
                        echo "Waiting for deployment to be ready..."
                        ${KUBECTL} rollout status deployment/acefitness-app -n ${K8S_NAMESPACE} --timeout=5m
                    '''
                }
            }
        }

        stage('Kubernetes - Verify Deployment') {
            steps {
                script {
                    sh '''
                        echo "Verifying Kubernetes deployment..."
                        
                        echo "=== Deployment Status ==="
                        ${KUBECTL} get deployments -n ${K8S_NAMESPACE}
                        
                        echo "=== Pod Status ==="
                        ${KUBECTL} get pods -n ${K8S_NAMESPACE} -o wide
                        
                        echo "=== Service Status ==="
                        ${KUBECTL} get svc -n ${K8S_NAMESPACE}
                        
                        echo "=== Pod Logs ==="
                        ${KUBECTL} logs -n ${K8S_NAMESPACE} $(${KUBECTL} get pod -n ${K8S_NAMESPACE} -l app=acefitness -o jsonpath='{.items[0].metadata.name}') || true
                        
                        echo "=== Testing Health Endpoint ==="
                        POD_NAME=$(${KUBECTL} get pod -n ${K8S_NAMESPACE} -l app=acefitness -o jsonpath='{.items[0].metadata.name}')
                        ${KUBECTL} exec -n ${K8S_NAMESPACE} ${POD_NAME} -- curl -s http://localhost:5000/health || true
                    '''
                }
            }
        }

        stage('Kubernetes - Blue-Green Setup (Optional)') {
            steps {
                script {
                    sh '''
                        echo "Blue-Green deployment manifests are available in k8s-blue-green.yaml"
                        echo "To deploy Blue-Green: ${KUBECTL} apply -f k8s-blue-green.yaml"
                        echo "To switch to Green: ${KUBECTL} patch service acefitness-bluegreen -n ${K8S_NAMESPACE} -p '{\"spec\":{\"selector\":{\"slot\":\"green\"}}}'
                        echo "To rollback to Blue: ${KUBECTL} patch service acefitness-bluegreen -n ${K8S_NAMESPACE} -p '{\"spec\":{\"selector\":{\"slot\":\"blue\"}}}'
                    '''
                }
            }
        }

        stage('Kubernetes - Deployment Info') {
            steps {
                script {
                    sh '''
                        echo "======================================="
                        echo "Kubernetes Deployment Complete!"
                        echo "======================================="
                        echo ""
                        echo "Application Details:"
                        echo "- Namespace: ${K8S_NAMESPACE}"
                        echo "- Deployment: acefitness-app"
                        echo "- Replicas: 3"
                        echo "- Image: ${IMAGE}:latest"
                        echo ""
                        echo "Service Details:"
                        echo "- Service Name: acefitness-service"
                        echo "- Type: NodePort"
                        echo "- Port: 80 → 5000"
                        echo "- NodePort: 30000"
                        echo ""
                        echo "To access the application:"
                        echo "1. Get Minikube IP: minikube ip"
                        echo "2. Access: http://<MINIKUBE_IP>:30000"
                        echo "3. Health check: http://<MINIKUBE_IP>:30000/health"
                        echo ""
                        echo "To view logs:"
                        echo "${KUBECTL} logs -f deployment/acefitness-app -n ${K8S_NAMESPACE}"
                        echo ""
                        echo "To scale deployment:"
                        echo "${KUBECTL} scale deployment acefitness-app -n ${K8S_NAMESPACE} --replicas=5"
                        echo ""
                        echo "To rollback to previous version:"
                        echo "${KUBECTL} rollout undo deployment/acefitness-app -n ${K8S_NAMESPACE}"
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
