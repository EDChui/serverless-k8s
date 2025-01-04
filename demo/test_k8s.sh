#!/bin/bash

# Step 0: Start k8s proxy (manually)
# kubectl proxy --port=8080 &

# Function to handle the deployment process for each pod
deploy_pod() {
  local i=$1
  
  # Step 1: Record start time
  start_time=$(gdate +%s%N)

  # Step 2: Create deployment using curl
  deployment_start=$(gdate +%s%N)

  yaml="apiVersion: v1
kind: Pod
metadata:
  name: demo$i
  labels:
    app: demo$i
  namespace: default
spec:
  containers:
    - name: nginx
      image: nginx
      resources:
        requests:
          memory: "1Mi"
          cpu: 0.01
      ports:
        - containerPort: 80
"
  
  # Perform the curl call to create the deployment
  curl -X POST \
    -H "Content-Type: application/yaml" \
    -d "${yaml}" \
    http://localhost:8080/api/v1/namespaces/default/pods
  deployment_end=$(gdate +%s%N)

  # Step 3: Wait for the pod to be ready
  pod_start=$(gdate +%s%N)
  while true; do
    pod_status=$(kubectl get pods -l app=demo${i} -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    if [[ "$pod_status" == "Running" ]]; then
      break
    fi
    # Wait 100ms before next check
    sleep 0.1
  done
  pod_end=$(gdate +%s%N)

  # Step 4: Record end time
  end_time=$(gdate +%s%N)

  # Step 5: Calculate times
  total_time=$((( end_time - start_time ) / 1000000 )) # Total time in ms
  deployment_time=$((( deployment_end - deployment_start ) / 1000000 )) # Deployment creation time in ms
  pod_ready_time=$((( pod_end - pod_start ) / 1000000 )) # Pod readiness time in ms

  # Step 6: Print results
  echo "$i,$start_time,$deployment_start,$deployment_end,$pod_start,$pod_end,$end_time,$total_time,$deployment_time,$pod_ready_time" | tee -a output.csv

  # Step 7: Delete the pod after testing
  kubectl delete pod demo${i}
}

# Run the deployment for each pod in parallel
for i in {1..10}; do
  deploy_pod $i &  # Run the deployment in the background
done
