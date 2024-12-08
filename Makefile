NAMESPACE=raptorchoinl
PROJECT=serverless-k8s

build-push:
	@for name in $(shell ls services) ; do \
		cd ./services/$$name && docker build -t ${NAMESPACE}/serverless-k8s:latest . && docker push ${NAMESPACE}/serverless-k8s:latest && cd ../..; \
	done

build-deploy-api-server:
	@cd ./services/api_server && docker build -t ${NAMESPACE}/serverless-k8s-api-server:latest . && docker push ${NAMESPACE}/serverless-k8s-api-server:latest && kubectl delete ksvc api-server && kubectl apply -f api_server.yaml;

build-deploy-scheduler:
	@cd ./services/scheduler && docker build -t ${NAMESPACE}/serverless-k8s-scheduler:latest . && docker push ${NAMESPACE}/serverless-k8s-scheduler:latest && kubectl delete ksvc knative-scheduler && kubectl apply -f scheduler.yaml;

build-deploy-controller:
	@cd ./services/controller && docker build -t ${NAMESPACE}/serverless-k8s-controller:latest . && docker push ${NAMESPACE}/serverless-k8s-controller:latest && kubectl delete ksvc knative-controller && kubectl apply -f controller.yaml;

install-knative-dependencies:
	@kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.16.0/serving-crds.yaml;
	@kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.16.0/serving-core.yaml;
	@kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.16.0/kourier.yaml;
	@kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}';
	@kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.16.0/serving-default-domain.yaml;

# kubectl get ksvc api-server  --output=custom-columns=NAME:.metadata.name,DOMAIN:.status.domain

# Deploy
# kubectl apply -f api_server.yaml

# Get Knative Services
# kubectl get ksvc

# Delete Knative Services
# kubectl delete ksvc api-server

# Get Pods Logging
# kubectl get pods
# kubectl logs <pods-name>

# Install Knative and Kubernetes using kind, can delete and recreate
# kn quickstart kind

# Verify Installation
# kubectl get pods -n knative-serving

# sh
# docker exec -it knative-control-plane sh
# cat /etc/kubernetes/manifests/etcd.yaml

# Copy
# docker cp knative-control-plane:/etc/kubernetes/pki/etcd/ca.crt ./Documents/ca.crt
# docker cp knative-control-plane:/etc/kubernetes/pki/apiserver-etcd-client.crt ./Documents/client.crt
# docker cp knative-control-plane:/etc/kubernetes/pki/apiserver-etcd-client.key ./Documents/client.key

# ls /etc/kubernetes/pki

# curl -v 172.18.0.2:2379 --cacert /etc/kubernetes/pki/ca.crt --key /etc/kubernetes/pki/apiserver-etcd-client.key --cert /etc/kubernetes/pki/apiserver-etcd-client.crt 
# curl -v 172.18.0.2:2379 --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key
