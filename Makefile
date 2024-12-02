PROJECT=serverless-k8s
#ghcr.io/${PROJECT}/$$name:latest

local-build:
	@for name in $(shell ls services) ; do \
		cd ./services/$$name && docker build -t raptorchoinl/serverless-k8s:latest . && cd ../..; \
	done

# kubectl get ksvc api-server  --output=custom-columns=NAME:.metadata.name,DOMAIN:.status.domain

# Deploy
# kn service create --force api-server --image raptorchoinl/serverless-k8s:latest --port 8080

# Verify Installation
# kubectl get pods -n knative-serving