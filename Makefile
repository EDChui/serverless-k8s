NAMESPACE=YOUR_NAMESPACE_HERE
PROJECT=serverless-k8s

# Setup commands
TEMP_CERTS_DIR=certs

install-knative-dependencies:
	@kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.16.0/serving-crds.yaml;
	@kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.16.0/serving-core.yaml;
	@kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.16.0/kourier.yaml;
	@kubectl patch configmap/config-network \
		--namespace knative-serving \
		--type merge \
		--patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}';
	@kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.16.0/serving-default-domain.yaml;

update-namespace:
	@for name in $(shell ls services) ; do \
		perl -pi -e 's/{{namespace}}/$(NAMESPACE)/g' ./services/$$name/$$name.yaml; \
	done

get-etcd-certs:
	@mkdir -p $(TEMP_CERTS_DIR);
	@docker cp knative-control-plane:/etc/kubernetes/pki/etcd/ca.crt $(TEMP_CERTS_DIR)/ca.crt;
	@docker cp knative-control-plane:/etc/kubernetes/pki/apiserver-etcd-client.crt $(TEMP_CERTS_DIR)/client.crt;
	@docker cp knative-control-plane:/etc/kubernetes/pki/apiserver-etcd-client.key $(TEMP_CERTS_DIR)/client.key;
	@for name in $(shell ls services) ; do \
		cp -r $(TEMP_CERTS_DIR) ./services/$$name; \
	done
	@rm -r $(TEMP_CERTS_DIR)

# Deployment commands

build-push-all:
	@for name in $(shell ls services) ; do \
		cd ./services/$$name && \
		docker build -t ${NAMESPACE}/serverless-k8s:latest . && \
		docker push ${NAMESPACE}/serverless-k8s:latest \
		&& cd ../..; \
	done

build-deploy-all: build-deploy-api-server build-deploy-scheduler build-deploy-controller
	@echo "All services built and deployed successfully!"

take-down-all:
	@(kubectl get ksvc api-server > /dev/null 2>&1 && kubectl delete ksvc api-server || echo "api-server does not exist, skipping delete") && \
	(kubectl get ksvc knative-scheduler > /dev/null 2>&1 && kubectl delete ksvc knative-scheduler || echo "knative-scheduler does not exist, skipping delete") && \
	(kubectl get ksvc knative-controller > /dev/null 2>&1 && kubectl delete ksvc knative-controller || echo "knative-controller does not exist, skipping delete");

build-deploy-api-server:
	@cd ./services/api_server && \
	docker build -t ${NAMESPACE}/serverless-k8s-api-server:latest . && \
	docker push ${NAMESPACE}/serverless-k8s-api-server:latest && \
	(kubectl get ksvc api-server > /dev/null 2>&1 && kubectl delete ksvc api-server || echo "api-server does not exist, skipping delete") && \
	kubectl apply -f api_server.yaml;

build-deploy-scheduler:
	@cd ./services/scheduler && \
	docker build -t ${NAMESPACE}/serverless-k8s-scheduler:latest . && \
	docker push ${NAMESPACE}/serverless-k8s-scheduler:latest && \
	(kubectl get ksvc knative-scheduler > /dev/null 2>&1 && kubectl delete ksvc knative-scheduler || echo "knative-scheduler does not exist, skipping delete") && \
	kubectl apply -f scheduler.yaml;

build-deploy-controller:
	@cd ./services/controller && \
	docker build -t ${NAMESPACE}/serverless-k8s-controller:latest . && \
	docker push ${NAMESPACE}/serverless-k8s-controller:latest && \
	(kubectl get ksvc knative-controller > /dev/null 2>&1 && kubectl delete ksvc knative-controller || echo "knative-controller does not exist, skipping delete") && \
	kubectl apply -f controller.yaml;
