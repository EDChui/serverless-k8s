from flask import Flask, jsonify
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.message import DecodeError
import etcd3
import os
import traceback
import json
import yaml

# Initialize Flask App
app = Flask(__name__)

dirname = os.path.dirname(__file__)
ca_cert = os.path.join(dirname, 'certs/ca.crt')
cert_cert = os.path.join(dirname, 'certs/client.crt')
cert_key = os.path.join(dirname, 'certs/client.key')

# Initialize etcd3 Client
etcd = etcd3.client(
    host="172.18.0.2",
    port=2379,
    ca_cert=ca_cert,
    cert_cert=cert_cert,
    cert_key=cert_key
)

# List of available nodes (hardcoded for simplicity)
available_nodes = ["node1", "node2", "node3"]
current_node_index = 0

def parse_protobuf(value):
    """
    Parse Protobuf data and convert to dictionary.
    """
    try:
        # Dynamically decode the Protobuf (replace with your Pod Protobuf class)
        from kubernetes.generated import Pod
        pod = Pod()
        pod.ParseFromString(value)
        return MessageToDict(pod)
    except DecodeError:
        print("Error decoding Protobuf data.")
        return None

def detect_and_parse(value):
    """
    Detect and parse the format of the data (JSON, YAML).
    Returns a Python dictionary or None if parsing fails.
    """
    try:
        # Try parsing as Protobuf
        return parse_protobuf(value)
    except Exception:
        pass

    try:
        # Try parsing as JSON
        return json.loads(value.decode("utf-8"))
    except Exception:
        pass

    # Return None if parsing fails
    return None


def fetch_pod(key):
    """
    Fetch and parse a Pod from etcd.
    Handles JSON and YAML formats.
    """
    value, metadata = etcd.get(key)
    if value:
        pod_dict = detect_and_parse(value)
        if pod_dict:
            return pod_dict
        else:
            print(f"Error: Unable to parse Pod at key {key}")
    return None


def update_pod(key, pod):
    """
    Update a Pod in etcd as JSON.
    """
    serialized_pod = json.dumps(pod).encode("utf-8")
    etcd.put(key, serialized_pod)


def get_pending_pods():
    """
    Retrieve all Pods in the Pending state (no nodeName).
    """
    prefix = "/registry/pods/"
    pending_pods = []

    for value, metadata in etcd.get_prefix(prefix):
        pod_key = metadata.key.decode()
        pod_dict = fetch_pod(pod_key)
        if pod_dict and not pod_dict.get("spec", {}).get("nodeName"):
            pending_pods.append((pod_key, pod_dict))

    return pending_pods


def assign_node_to_pod(pod_key, pod):
    """
    Assign a node to a pending Pod and update it in etcd.
    """
    global current_node_index
    node_name = available_nodes[current_node_index]

    # Round-robin scheduling
    current_node_index = (current_node_index + 1) % len(available_nodes)

    # Update the Pod spec with the assigned node
    pod["spec"]["nodeName"] = node_name
    update_pod(pod_key, pod)

    return node_name

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "Scheduler is running"}), 200

@app.route('/schedule', methods=['POST'])
def schedule_pods():
    try:
        """Endpoint to trigger Pod scheduling."""
        pending_pods = get_pending_pods()
        if not pending_pods:
            return jsonify({"message": "No pending pods to schedule"}), 200

        results = []
        for pod_key, pod_dict in pending_pods:
            node_name = assign_node_to_pod(pod_key, pod_dict)
            results.append({"pod_key": pod_key, "assigned_node": node_name})

        return jsonify({"message": "Pods scheduled", "results": results}), 200

    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Error occurs"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
