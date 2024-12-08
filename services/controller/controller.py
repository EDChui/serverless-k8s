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
    The controller watches etcd for changes and ensures the desired state is maintained.
    This endpoint can be called periodically (via a cron job or similar).
    """
    try:
        # Step 1: Watch for Pods in the "Pending" state (no nodeName assigned)
        pending_pods = get_pending_pods()

        if not pending_pods:
            return jsonify({"message": "No pending Pods to reconcile"}), 200

        results = []
        for pod_key, pod_dict in pending_pods:
            # Step 2: Trigger scheduling for each pending Pod
            scheduling_response = trigger_scheduler(pod_key)

            if scheduling_response.get("status") == "success":
                results.append({
                    "pod_key": pod_key,
                    "assigned_node": scheduling_response["assigned_node"]
                })
            else:
                results.append({
                    "pod_key": pod_key,
                    "error": "Failed to schedule Pod"
                })

        return jsonify({"message": "Reconciliation completed", "results": results}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal System Error"}), 500

@app.route('/scale-replicaset', methods=['POST'])
def scale_replicaset():
    """
    Scale a ReplicaSet by ensuring it has the desired number of Pods.
    This will watch etcd for ReplicaSets and scale them based on the desired state.
    """
    try:
        data = request.json
        replicaset_name = data.get("name")
        namespace = data.get("namespace", "default")
        desired_replicas = data.get("desired_replicas", 1)

        # Step 4: Check current state of the ReplicaSet in etcd
        replicaset_key = f"/registry/replicasets/{namespace}/{replicaset_name}"
        value, _ = etcd.get(replicaset_key)

        if not value:
            return jsonify({"error": "ReplicaSet not found"}), 404

        replicaset = json.loads(value.decode('utf-8'))
        current_replicas = len([pod for pod in replicaset["status"]["pods"]])

        # Step 5: Scale the ReplicaSet by adding or removing Pods
        if current_replicas < desired_replicas:
            for _ in range(desired_replicas - current_replicas):
                # Create and schedule new Pods for the ReplicaSet
                pod_key = create_pod_for_replicaset(replicaset_name, namespace)
                trigger_scheduler(pod_key)

        return jsonify({
            "message": f"ReplicaSet '{replicaset_name}' scaled to {desired_replicas} Pods"
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

def get_pending_pods():
    """
    Fetch all Pods in the "Pending" state (no nodeName assigned).
    """
    prefix = "/registry/pods/"
    pending_pods = []

    # Step 3: Query etcd for Pods in "Pending" state (i.e., no nodeName)
    for value, metadata in etcd.get_prefix(prefix):
        pod_key = metadata.key.decode()
        pod_dict = fetch_pod(pod_key)
        if pod_dict and not pod_dict.get("spec", {}).get("nodeName"):
            pending_pods.append((pod_key, pod_dict))

    return pending_pods

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
