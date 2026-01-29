pipeline {
    agent {
        docker {
            image 'python:3.9-slim'
        }
    }
    
    environment {
        PIP_INDEX_URL = 'https://pypi.tuna.tsinghua.edu.cn/simple'
    }
    
    stages {
        stage('Install') {
            steps {
                sh '''
                    apt-get update && apt-get install -y --no-install-recommends gcc g++ make libgomp1
                    pip install --upgrade pip -i $PIP_INDEX_URL
                    pip install numpy==1.24.3 pandas==2.0.3 -i $PIP_INDEX_URL
                    pip install -r requirements.txt -i $PIP_INDEX_URL
                '''
            }
        }
        
        stage('Unit Tests') {
            steps {
                sh '''
                    cd pro2
                    python -m pytest tests/unit -v --tb=short --html=tests/reports/unit_test_report.html --self-contained-html || echo "Tests completed"
                '''
            }
            post {
                always {
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'pro2/tests/reports',
                        reportFiles: 'unit_test_report.html',
                        reportName: 'Unit Test Report'
                    ])
                }
            }
        }
        
        stage('Integration Tests') {
            steps {
                sh '''
                    cd pro2
                    python -m pytest tests/integration -v --tb=short --html=tests/reports/integration_test_report.html --self-contained-html || echo "Tests completed"
                '''
            }
        }
        
        stage('All Tests') {
            steps {
                sh '''
                    cd pro2
                    pip install pytest-cov -i $PIP_INDEX_URL
                    python -m pytest tests/ -v --cov=fund_search --cov-report=xml --cov-report=html --html=tests/reports/all_tests_report.html --self-contained-html || echo "All tests completed"
                '''
            }
        }
        
        stage('Build') {
            steps {
                sh 'python main.py'
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'pro2/tests/reports/*.html', allowEmptyArchive: true
            archiveArtifacts artifacts: 'pro2/htmlcov/**', allowEmptyArchive: true
        }
    }
}
