reactconf = {
    "hostedzone_id": "Z05045244G4M5OFGHB4C",
    "record_name": "reactapp.abdelalitraining.com",
    "certificate_arn": "arn:aws:acm:us-east-1:080266302756:certificate/326d29bd-95af-4139-ace0-eccb94dbbcfe"
}

flaskconf = {
     "vpcid": "vpc-060e19e5c5dc35413",
      "name": "ecs-cluster",
      "family": "Flasktaskdefinition",
      "alb-name":"aws-alb-flask-ecs",
      "svc-name":"flask-service",
      "tg-name":"aws-flask-tg",
      "sg-name":"aws-flask-service-sg",
      "domaine": "abdelalitraining.com",
      "zone_id": "Z05045244G4M5OFGHB4C",
      "record": "flaskapp.abdelalitraining.com",
      "certificatearn": "arn:aws:acm:us-west-2:080266302756:certificate/7048596d-aa16-49f5-8399-2b2e53a4fc5f"
}
