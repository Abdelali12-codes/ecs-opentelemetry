pipeline {
     agent any
     stages {
        stage('SCM') {
               checkout scm
        }
        stage('SonarQube Analysis') {
               def scannerHome = tool 'SonarScanner 5.0';
               withSonarQubeEnv("sonarqubeserver") {
                 sh "${scannerHome}/bin/sonar-scanner"
               }
               
        }
    }
}
