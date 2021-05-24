### Pre Install
- Install aws cli, to communicate with the cloud via command line
- Install python3.6+ if not installed
- Create new virtualenv and activate
```
>> mkdir ~/Envs
>> python3 -m venv ~/Envs/env01
>> source ~/Envs/env01/bin/activate
```
- Install ansible
```
>> pip install ansible
```
- Install boto3
```
>> pip install boto3
```
- Install ansible addons for aws
```
>> ansible-galaxy collection install community.aws
```
- Download and install vagrant for local version from https://www.vagrantup.com/

### Project structure
This project contains 2 variants:

- aws-version: used to create a kubernetes cluster on AWS and deploy a flask-app on it
- vagrant-version: used to create a kubernetes cluster on Vagrant and deploy a flask-app on it

There is a sample app, which used to deploy on Kubernetes and tests:

- flask-app: pushed to docker hub to be used for this project, also can be ran standalone with docker-compose

```
>> docker build . -t <YOU_ON_DOCKERHUB>/flaskapp:1.0
>> docker push <YOU_ON_DOCKERHUB>/flaskapp:1.0
```

- For aws-version there is provision.yml ansible playbook to create all resources needed on aws
- Both versions have a master-playbook.yml to install kubernetes on master and node-playbook.yml to install kubernetes nodes
- There is a kube-deploy foder contains:
    - flaskapp-deployment.yaml: kubernetes yaml file for flaskapp (deployment, service, HorizontalPodAutoscaler)
    - mysql-deployment.yaml: kubernetes kubernetes yaml file for mysql (deployment, service, NetworkPolicy)
    - kustomization.yaml: combines two and a secretGenerator (we can use kubectl apply ./)

### Setting credetinals for AWS connection
Before begin set the following environment variables by the following bash commands, replace values <> placeholders with real values

```
>> export AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY>
>> export AWS_SECRET_ACCESS_KEY=<AWS_SECRET_KEY>
>> export AWS_SECURITY_TOKEN=<AWS_SECURITY_TOKEN>
>> export AWS_REGION=<AWS_REGION>
```

### Provision AWS resources
The following playbook will create all resources needed on aws for a kubernetes cluster.

- Will create keypair and download it on local
- Will create ELB, EC2 group with proper inbound, outbound rules (allowing on port 80 and 22), restrict this setting while using in production.
- Will create 3 EC2 instances, 1 for master and 2 for nodes, and will create and asssing Elastic IPs to them.
- Will add created nodes to ansible_hosts file and also known_hosts
```
>> ansible-playbook provision.yml
```

### Test AWS connectivity
```
>> ssh -i ~/.aws/my_keypair.pem ubuntu@<ip-address>
OR
>> ansible -m ping k8s_master -i ansible_hosts
>> ansible -m ping k8s_nodes -i ansible_hosts

```

### Provision Kubernetes master and nodes
- The following will install all prerequisites, docker, kubenetes and will start services, and will join nodes to the cluster.
- Also will deploy a python-flask simple application with autoscaler which connects to a mysql deploy.
```
>> ansible-playbook master-playbook.yml -i ansible_hosts
>> ansible-playbook node-playbook.yml -i ansible_hosts
```

### Provision Vagrant version
- We need some hypervisor (Like VirtualBox) to be installed
- Just cd into vagrant-version and run:
```
>> vagrant up
```

### Take snapshot from etcd
- ssh into master node
```
>> ssh -i ~/.aws/my_keypair.pem ubuntu@<ip-address>
OR
>> vagrant ssh k8s-master
```
- Check that etcd-k8s-master is there and running:
```
>> kubectl get pods -n kube-system
```
- Grab correct url for our operation:
```
>> kubectl describe pod etcd-k8s-master -n kube-system | grep advertise
>> export advertise_url=192.168.50.10:2379
```
- Take the snapshot
```
>> sudo ETCDCTL_API=3 etcdctl --endpoints $advertise_url \
--cacert /etc/kubernetes/pki/etcd/ca.crt --key /etc/kubernetes/pki/etcd/server.key \
--cert /etc/kubernetes/pki/etcd/server.crt get "" --prefix=true -w json > etcd.json
```
- See what we have got on etcd:
```
>> for k in $(cat etcd.json | jq '.kvs[].key' | cut -d '"' -f2); do echo $k | base64 --decode; echo; done
>> for k in $(cat etcd.json | jq '.kvs[].value' | cut -d '"' -f2); do echo $k | base64 --decode; echo; done
```

### Create a new user with permissions to create, list, get, update, and delete pods
- On master-playbook.yml we are created a Custom Service Account this only has access to the pods, this is the commands which we have executed:
```
>> kubectl create clusterrole custom-cluster-role --verb=list --verb=get --verb=watch --verb=update --verb=delete --verb=create  --resource=pods 
>> kubectl create serviceaccount custom-service-account
>> kubectl create clusterrolebinding custom-clusterrole-binding --clusterrole=custom-cluster-role --serviceaccount=default:custom-service-account
```
- Let's test the access:
```
>> kubectl auth can-i delete pods --as=system:serviceaccount:default:custom-service-account
yes
>> kubectl auth can-i list services --as=system:serviceaccount:default:custom-service-account
no
>> kubectl auth can-i delete configmaps --as=system:serviceaccount:default:custom-service-account
no
>> kubectl auth can-i create pods --as=system:serviceaccount:default:custom-service-account
yes
```

### Checking scalability of HSA
- Login to master node
```
>> kubectl get pods

>> kubectl get hpa -w
NAME       REFERENCE             TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
flaskapp   Deployment/flaskapp   0%/50%     1         3         1          38m
flaskapp   Deployment/flaskapp   235%/50%   1         3         1          39m
flaskapp   Deployment/flaskapp   235%/50%   1         3         3          40m
```
- Run a load on the applicaiton using busybox or just use node-ip:service-port
```
SSH another terminal to master:
>> kubectl run -i --tty load-generator --rm --image=busybox --restart=Never \
-- /bin/sh -c "while sleep 0.01; do wget -q -O- http://flaskapp:5000; done"
OR
Run locally
>> while true; do curl http://<master-node-ip>:<flask-app-node-port>; done
>> 
```
- Now will see after a while that hpa 0% / 50% is rising.
- Also if it exceed than 50% and we check the pods will see the increase
