NAMESPACE=raptorchoinl
PROJECT=serverless-k8s
#ghcr.io/${PROJECT}/$$name:latest

build-push:
	@for name in $(shell ls services) ; do \
		cd ./services/$$name && docker build -t ${NAMESPACE}/serverless-k8s:latest . && docker push ${NAMESPACE}/serverless-k8s:latest && cd ../..; \
	done

build-deploy-api-server:
	@cd ./services/api_server && docker build -t ${NAMESPACE}/serverless-k8s:latest . && docker push ${NAMESPACE}/serverless-k8s:latest && kubectl delete ksvc api-server && kubectl apply -f api_server.yaml;

# kubectl get ksvc api-server  --output=custom-columns=NAME:.metadata.name,DOMAIN:.status.domain

# Deploy
# kubectl apply -f api_server.yaml

# Get Knative Services
# kubectl get ksvc

# Delete Knative Services
# kubectl delete ksvc api_server

# Get Pods Logging
# kubectl get pods
# kubectl logs <pods-name>

# Verify Installation
# kubectl get pods -n knative-serving

# Copy
# docker cp knative-control-plane:/etc/kubernetes/pki/ca.crt ./Documents/ca.crt
# docker cp knative-control-plane:/etc/kubernetes/pki/apiserver-etcd-client.crt ./Documents/client.crt
# docker cp knative-control-plane:/etc/kubernetes/pki/apiserver-etcd-client.key ./Documents/client.key

# curl -v https://127.0.0.1:2379 --cacert /etc/kubernetes/pki/ca.crt --key /etc/kubernetes/pki/apiserver-etcd-client.key --cert /etc/kubernetes/pki/apiserver-etcd-client.crt 