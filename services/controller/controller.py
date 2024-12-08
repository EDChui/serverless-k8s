import os
import json
import requests
import etcd3
from flask import Flask, jsonify, request
import traceback
import datetime
import subprocess
import yaml

# Initialize Flask App
app = Flask(__name__)

# etcd Configuration
ETCD_HOST = "172.18.0.2"
ETCD_PORT = 2379

# Path to certificates (assumes they're present in 'certs' directory)
dirname = os.path.dirname(__file__)
ca_cert = os.path.join(dirname, 'certs/ca.crt')
cert_cert = os.path.join(dirname, 'certs/client.crt')
cert_key = os.path.join(dirname, 'certs/client.key')

# Initialize etcd3 Client
etcd = etcd3.client(
    host=ETCD_HOST,
    port=ETCD_PORT,
    ca_cert=ca_cert,
    cert_cert=cert_cert,
    cert_key=cert_key
)

# Constant
API_SERVER_URL = "http://api-server.default.127.0.0.1.sslip.io"
SCHEDULER_URL = "http://knative-scheduler.default.127.0.0.1.sslip.io"

# Initialize available nodes (can be dynamically fetched)
available_nodes = ["node1", "node2", "node3"]
current_node_index = 0

@app.route('/')
def health_check():
    """
    Health check endpoint for the Controller service.
    """
    return jsonify({"status": "Controller service is running"}), 200

@app.route('/reconcile', methods=['POST'])
def reconcile():
    """
    The controller listens for reconciliation requests and performs actions
    like scaling, pod scheduling, or resource management.
    """
    try:
        resource_type = request.json.get("resource_type")
        resource_name = request.json.get("resource_name")
        namespace = request.json.get("namespace", "default")

        # Fetch resource details dynamically from etcd based on type
        resource_key = f"/registry/{resource_type}/{namespace}/{resource_name}"
        value, _ = etcd.get(resource_key)
        
        if not value:
            return jsonify({"error": f"{resource_type.capitalize()} '{resource_name}' not found in etcd"}), 404

        resource_data = detect_and_parse(value)

        # Perform reconciliation (scale, create, or update resources)
        if resource_type == "replicasets":
            scale_replicaset(resource_data, namespace)
        elif resource_type == "deployments":
            handle_deployment(resource_data, namespace)
        elif resource_type == "pods":
            handle_pod(resource_data, namespace)
        else:
            return jsonify({"error": f"Unsupported resource type '{resource_type}'"}), 400

        return jsonify({"message": f"Resource {resource_name} reconciled successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def scale_replicaset(replicaset, namespace):
    """
    Scale the ReplicaSet to the desired number of replicas.
    """
    desired_replicas = replicaset["spec"]["replicas"]
    current_pods = fetch_current_pods(namespace, replicaset["metadata"]["name"])

    current_replicas = len(current_pods)
    
    # Scale up if needed
    if current_replicas < desired_replicas:
        for _ in range(desired_replicas - current_replicas):
            create_and_schedule_pod(namespace, replicaset)
    # Optionally, scale down if needed (not implemented here)
    elif current_replicas > desired_replicas:
        for excess_pod in current_pods[:current_replicas - desired_replicas]:
            delete_pod(excess_pod)

def handle_deployment(deployment, namespace):
    """
    Handle deployment operations like scaling or updating deployments.
    """
    # Assume scaling logic or rollout logic for Deployments
    scale_replicaset(deployment, namespace)  # Simplifying for this example

def handle_pod(pod, namespace):
    """
    Handle Pod operations such as scheduling a pod if it's not scheduled yet.
    """
    if "nodeName" not in pod["spec"]:  # Check if pod is unscheduled
        schedule_pod_on_node(pod, namespace)

def fetch_current_pods(namespace, replicaset_name):
    """
    Fetch the current Pods managed by the ReplicaSet from etcd.
    """
    prefix = f"/registry/pods/{namespace}/"
    pods = []

    for value, metadata in etcd.get_prefix(prefix):
        pod_key = metadata.key.decode()
        pod_data = detect_and_parse(value)
        if pod_data.get("metadata", {}).get("labels", {}).get("replicaset", "") == replicaset_name:
            pods.append(pod_data)
    
    return pods

def create_and_schedule_pod(namespace, replicaset):
    """
    Dynamically create a Pod based on the ReplicaSet's spec and assign a node.
    """
    pod_name = f"{replicaset['metadata']['name']}-pod-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    pod_data = {
        "metadata": {"name": pod_name, "namespace": namespace},
        "spec": {
            "containers": replicaset['spec']['template']['spec']['containers'],  # Using ReplicaSet's container spec
            "nodeName": assign_node_to_pod()  # Assign the Pod to a node
        }
    }

    # Create the Pod using API Server
    response = requests.post(f"{API_SERVER_URL}/api/v1/pods", json=pod_data)
    if response.status_code == 201:
        return jsonify({
            "message": f"Pod {pod_name} created and scheduled successfully",
            "assigned_node": response["assigned_node"]
        })
    else:
        return jsonify({"error": "Failed to create and schedule pod"}), 500

def schedule_pod_on_node(pod, namespace):
    """
    Schedule the Pod on a node if it is not already scheduled.
    This will trigger the Scheduler Knative Service to assign the Pod to a node.
    """
    # Check if the Pod already has a node assigned
    if "nodeName" not in pod["spec"]:
        # Call the Scheduler Service to assign a node
        pod_key = pod["metadata"]["name"]
        schedule_response = trigger_scheduler(pod_key)

        if schedule_response.get("status") == "success":
            # Update the Pod with the assigned node
            pod["spec"]["nodeName"] = schedule_response["assigned_node"]
            # Update the Pod in etcd
            update_pod_in_etcd(pod_key, pod)

def assign_node_to_pod():
    """
    Assign a node to a specific Pod (by pod_key) using round-robin scheduling.
    """
    global current_node_index
    node_name = available_nodes[current_node_index]

    # Round-robin scheduling
    current_node_index = (current_node_index + 1) % len(available_nodes)

    return node_name

def update_pod_in_etcd(pod_key, pod):
    """
    Update the Pod in etcd with the assigned node.
    """
    serialized_pod = json.dumps(pod).encode("utf-8")
    etcd.put(f"/registry/pods/default/{pod_key}", serialized_pod)

def delete_pod(pod_data):
    """
    Delete a Pod from etcd by calling the API Server's DELETE API.
    """
    pod_key = pod_data["metadata"]["name"]
    
    # Call the API Server's DELETE API to delete the Pod
    response = requests.delete(f"{API_SERVER_URL}/api/v1/pods/{pod_key}")
    if response.status_code == 200:
        return jsonify({"message": f"Pod {pod_key} deleted successfully"}), 200
    else:
        return jsonify({"error": f"Failed to delete Pod {pod_key}"}), 500

def fetch_pod(key):
    """
    Fetch and parse a Pod from etcd.
    Handles Protobuf, JSON formats.
    """
    value, metadata = etcd.get(key)
    if value:
        pod_dict = detect_and_parse(value)
        print(pod_dict)
        if pod_dict:
            return pod_dict
        else:
            print(f"Error: Unable to parse Pod at key {key}")
    return None

def detect_and_parse(value):
    """
    Detect and parse the format of the data (Protobuf, JSON).
    Returns a Python dictionary or None if parsing fails.
    """
    try:
        # Try parsing as JSON
        return json.loads(value.decode("utf-8"))
    except Exception:
        pass
    
    try:
        # Try parsing as Protobuf
        return yaml.safe_load(auger_decode(value))
    except Exception:
        traceback.print_exc()
        pass

    return None

def auger_decode(data):
    """Simulates decoding Protobuf using Auger."""
    try:
        process = subprocess.run(
            ["./auger/build/auger", "decode"],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return process.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        print("Auger error:", e.stderr.decode('utf-8'))
        return None
    
def trigger_scheduler(pod_key):
    """
    Trigger the Scheduler Knative Service to assign a node to the Pod.
    """
    try:
        response = requests.post(f"{SCHEDULER_URL}/schedule", json={ "pod_key": pod_key })
        if response.status_code == 200:
            return {"status": "success", "assigned_node": response.json()["assigned_node"]}
        else:
            return {"status": "failure", "error": "Failed to schedule Pod"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

def create_pod_for_replicaset(replicaset_name, namespace):
    """
    Create a Pod for the ReplicaSet in etcd (simulated for this example).
    """
    pod_name = f"{replicaset_name}-pod-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pod_data = {
        "metadata": {
            "name": pod_name,
            "namespace": namespace
        },
        "spec": {
            "containers": [{"name": "nginx", "image": "nginx"}]
        }
    }

    pod_key = f"/registry/pods/{namespace}/{pod_name}"
    etcd.put(pod_key, json.dumps(pod_data).encode('utf-8'))
    return pod_key

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
