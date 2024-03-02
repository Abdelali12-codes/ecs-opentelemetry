pipeline {
    agent any
    stages {
        stage('SCM') {
            steps {
                checkout scm
            }
        }
        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'SonarScanner 5.0'
                    withSonarQubeEnv("sonarqubeserver") {
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }
    }
}

