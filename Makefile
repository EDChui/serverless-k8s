NAMESPACE=raptorchoinl
PROJECT=serverless-k8s
#ghcr.io/${PROJECT}/$$name:latest

build-push:
	@for name in $(shell ls services) ; do \
		cd ./services/$$name && docker build -t ${NAMESPACE}/serverless-k8s:latest . && docker push ${NAMESPACE}/serverless-k8s:latest && cd ../..; \
	done

# kubectl get ksvc api-server  --output=custom-columns=NAME:.metadata.name,DOMAIN:.status.domain

# Deploy
# kn service create --force api-server --image raptorchoinl/serverless-k8s:latest --port 8080

# Verify Installation
# kubectl get pods -n knative-serving

# Copy
# docker cp knative-control-plane:/etc/kubernetes/pki/ca.crt ./Documents/ca.crt
# docker cp knative-control-plane:/etc/kubernetes/pki/apiserver-etcd-client.crt ./Documents/client.crt
# docker cp knative-control-plane:/etc/kubernetes/pki/apiserver-etcd-client.key ./Documents/client.key