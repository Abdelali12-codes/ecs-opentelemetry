from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
)
from aws_cdk import RemovalPolicy, CfnOutput
from constructs import Construct
import aws_cdk.aws_cloudfront as cloudfront
import aws_cdk.aws_cloudfront_origins as origins
import aws_cdk.aws_certificatemanager as certificate
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_iam as iam
import aws_cdk.aws_elasticloadbalancingv2 as elb
import aws_cdk.aws_certificatemanager as acm
import aws_cdk.aws_rds as rds
import aws_cdk.aws_secretsmanager as secretsmanager
import aws_cdk.aws_route53_targets as targets
import  aws_cdk.aws_s3 as s3
import aws_cdk.aws_route53 as route53
import json 
from config import (
    reactconf,
    flaskconf
    
    )

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        
        bucket_name = self.node.try_get_context('bucket_name')
        db_name = self.node.try_get_context('db_name')
        db_user = self.node.try_get_context('db_user')
        
        vpc = ec2.Vpc.from_lookup(self, "ImportedVpc",vpc_id=flaskconf['vpcid'] )
        
        
        # rds sg
        alb_sg = ec2.SecurityGroup(self, "RDSSSG",
           vpc = vpc,
           security_group_name="rds-sg-flask",
           allow_all_outbound=True,
        )
        
        alb_sg.add_ingress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(3306)
        )
        
        # Using the templated secret as credentials
        rdsinstance = rds.DatabaseInstance(self, "MysqlInstance2",
            engine=rds.DatabaseInstanceEngine.MYSQL,
            database_name=db_name,
            instance_type= ec2.InstanceType.of(ec2.InstanceClass.MEMORY5, ec2.InstanceSize.LARGE),
            credentials=rds.Credentials.from_generated_secret(secret_name="rdssecret",
            username=db_user),
            vpc=vpc
        )
        # Route53 record
        zone = route53.HostedZone.from_hosted_zone_attributes(self,'Route53HostedZone',
            hosted_zone_id=flaskconf['zone_id'],
           zone_name=flaskconf['domaine']
        )
        
        # Acm Certificate
        certificate = acm.Certificate.from_certificate_arn(self, "domainCert", flaskconf["certificatearn"])
        
        # Acm for Cloudfront
        clfcert = acm.Certificate.from_certificate_arn(self, "domainCert", reactconf["certificate_arn"])

        
        # Loadbalancer sg
        alb_sg = ec2.SecurityGroup(self, "ALBSSG",
           vpc = vpc,
           security_group_name="alb-sg",
           allow_all_outbound=True,
        )
        
        alb_sg.add_ingress_rule(
            ec2.Peer.ipv4('0.0.0.0/0'),
            ec2.Port.tcp(80)
        )
        
        alb_sg.add_ingress_rule(
            ec2.Peer.ipv4('0.0.0.0/0'),
            ec2.Port.tcp(443)
        )
        # Application Loadbalancer
        alb = elb.ApplicationLoadBalancer(self, "AWSALBECS",
            vpc=vpc,
            internet_facing=True,
            load_balancer_name=flaskconf["alb-name"],
            security_group= alb_sg,
            vpc_subnets=ec2.SubnetSelection(
                    subnet_type = ec2.SubnetType.PUBLIC
                ),
            
        )
        
        alb_target_http = elb.ApplicationTargetGroup(self,"ApplicationTargetGroupHttp",
          port=80,
          target_group_name=flaskconf["tg-name"],
          target_type=elb.TargetType.IP,
          health_check=elb.HealthCheck(
              port="80",
              protocol=elb.Protocol.HTTP,
              path="/"
          ),
          vpc=vpc
        )
        
        alb.add_listener("AWSAlbListenerHttp",
         port=80,
         default_target_groups= [alb_target_http]
        )
        
        alb.add_listener("AWSAlbListenerHttps",
         port=443,
         certificates= [certificate],
         default_target_groups= [alb_target_http]
        )
        
        # Alias Record
        route53.ARecord(self, "AliasRecord",
            zone=zone,
            target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb)),
            record_name=flaskconf["record"]
        )
        
        # ECS Cluster
        cluster = ecs.Cluster.from_cluster_attributes(self, "ECSCluster",
                vpc=vpc,
                cluster_name=flaskconf['name'],
            )
            
          
        # task role and excecution role  
        taskrole = iam.Role(self, "Role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="aws-ecs-task-role",
            managed_policies=[
                  iam.ManagedPolicy.from_aws_managed_policy_name("AWSXrayFullAccess"),
                  iam.ManagedPolicy.from_aws_managed_policy_name("AmazonPrometheusFullAccess"),
                ]
        )
        
        taskexecutionRolePolicy = iam.PolicyStatement( 
            effect=iam.Effect.ALLOW,
            actions=[
                "ecr:getauthorizationtoken",
                "ecr:batchchecklayeravailability",
                "ecr:getdownloadurlforlayer",
                "ecr:batchgetimage",
                "logs:createlogstream",
                "logs:putlogevents"
            ],
            resources=["*"]
        )
        
        
        # Flask ecs task definition
        apptaskDef = ecs.TaskDefinition(self, "FlaskTaskDefinition",
              compatibility=ecs.Compatibility.FARGATE,
              family=flaskconf["family"],
              task_role=taskrole,
              cpu="1024",
              memory_mib="2048"
            )
        
        apptaskDef.add_to_execution_role_policy(taskexecutionRolePolicy)
        
        apptaskDef.add_container("FlaskContainer",
              container_name="flask",
              image=ecs.ContainerImage.from_asset(
                   "../flaskapp" 
                 ),
              memory_reservation_mib= 1024,
              cpu= 512,
              port_mappings=[
                  ecs.PortMapping(
                      container_port=5000,
                      protocol=ecs.Protocol.TCP
                  )
              ],
              logging= ecs.LogDriver.aws_logs(
                    stream_prefix="ecs-flaskapp"
                  )
            )
            
        apptaskDef.add_container("NginxContainer",
              container_name="nginx",
              image=ecs.ContainerImage.from_asset(
                   "../flaskapp/nginx" 
                 ),
              memory_reservation_mib= 1024,
              cpu= 512,
              port_mappings=[
                  ecs.PortMapping(
                      container_port=80,
                      protocol=ecs.Protocol.TCP
                  )
              ],
              logging= ecs.LogDriver.aws_logs(
                    stream_prefix="ecs-nginxapp"
                  )
            )
        
        # Flask application security group
        
        app_ecs_service_sg = ec2.SecurityGroup(self, "FlaskServiceSG",
           vpc = vpc,
           security_group_name=flaskconf["sg-name"],
           allow_all_outbound=True,
        )
        
        appfargateService = ecs.FargateService(self,
                "FlaskEcsService",
                service_name=flaskconf["svc-name"],
                cluster=cluster,
                assign_public_ip=True,
                security_groups= [app_ecs_service_sg],
                task_definition=apptaskDef,
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type = ec2.SubnetType.PUBLIC
                )
                
            )
        
        appfargateService.attach_to_application_target_group(alb_target_http)
        
        
        # React App Section
        
        s3_bucket = s3.Bucket(
            self, "MyBucket",
            bucket_name= bucket_name,
            removal_policy= RemovalPolicy.DESTROY
        )
        
        distribution = cloudfront.Distribution(self, "AwsCloudfrontDistribution",
                default_behavior=cloudfront.BehaviorOptions(
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    origin=origins.S3Origin(s3_bucket)
                ),
                error_responses= [
                    cloudfront.ErrorResponse(
                          http_status=403,
                          response_http_status=200,
                          response_page_path="/index.html"
                        )
                    ],
                certificate=certificate,
                domain_names=[reactconf['record_name']],
                
        )
        
        # Route53
        route53.CfnRecordSetGroup(self,"AWSCloudFrontRecord",
           hosted_zone_id=reactconf['hostedzone_id'],
           comment="cloudfront route53 record",
           record_sets=[
               route53.CfnRecordSetGroup.RecordSetProperty(
                    name=reactconf['record_name'],
                    type='A',
                    alias_target=route53.CfnRecordSetGroup.AliasTargetProperty(
                      dns_name=distribution.domain_name,
                      hosted_zone_id="Z2FDTNDATAQYW2"
                    )
               )
               ]
        )
        
        # Output values
        CfnOutput(self, "distributionid", value=distribution.distribution_id)
        CfnOutput(self, "dbhost", value=rdsinstance.db_instance_endpoint_address)