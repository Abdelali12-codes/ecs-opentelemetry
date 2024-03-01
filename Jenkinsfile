pipeline {
     agent any
     stages {
        stage('SCM') {
          steps{
               checkout scm
          }
        }
        stage('SonarQube Analysis') {
          steps{
               def scannerHome = tool 'SonarScanner';
               withSonarQubeEnv() {
                 sh "${scannerHome}/bin/sonar-scanner"
               }
          }
               
        }
    }
}
