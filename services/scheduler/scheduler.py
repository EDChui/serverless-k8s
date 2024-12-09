from flask import Flask, jsonify, request
import etcd3
import json
import os
import traceback
import subprocess
import yaml
from datetime import datetime

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

@app.route('/', methods=['GET'])
def health_check():
    """
    Health check endpoint for the scheduler service.
    """
    return jsonify({"status": "Scheduler is running"}), 200

@app.route('/schedule', methods=['POST'])
def schedule_pod():
    """
    Endpoint to trigger Pod scheduling. This endpoint receives a pod_key and schedules the pod on an available node.
    """
    try:
        # Get the pod_key from the request payload
        pod_key = request.json.get("pod_key")
        if not pod_key:
            return jsonify({"error": "pod_key is required"}), 400

        # Fetch the pod from etcd using the pod_key
        pod_dict = fetch_pod(pod_key)
        if not pod_dict:
            return jsonify({"error": f"Pod with key {pod_key} not found"}), 404

        # Assign a node to the Pod
        node_name = assign_node_to_pod(pod_key, pod_dict)

        # Return the scheduling result
        return jsonify({
            "message": f"Pod {pod_key} scheduled to {node_name}",
            "pod_key": pod_key,
            "assigned_node": node_name
        }), 200

    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Internal system error during scheduling"}), 500

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
    
def auger_encode(data_dict):
    """
    Encode a Python dictionary to Protobuf format using Auger.
    The dictionary is first converted to YAML, then encoded to Protobuf.
    """
    try:
        # Convert the dictionary to YAML format
        yaml_data = yaml.dump(data_dict, default_flow_style=False)

        # Use Auger to encode the YAML into Protobuf
        process = subprocess.run(
            ["./auger/build/auger", "encode"],
            input=yaml_data.encode("utf-8"),  # Provide YAML as input
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        # The output of the Auger process is the Protobuf encoded data
        return process.stdout
    except subprocess.CalledProcessError as e:
        print("Auger encoding error:", e.stderr.decode('utf-8'))
        return None

def assign_node_to_pod(pod_key, pod):
    """
    Assign a node to a specific Pod (by pod_key) and update it in etcd.
    """
    # Fetch real available nodes from etcd dynamically
    available_nodes = fetch_available_nodes_from_etcd()

    if not available_nodes:
        raise Exception("No available nodes found for scheduling.")

    # Round-robin scheduling (simple, could be expanded based on actual resource availability)
    node_name = available_nodes[0]  # Just assign the first node for simplicity

    # Update the Pod's nodeName field
    pod["spec"]["nodeName"] = node_name
    # Add creationTimestamp to the metadata of the resource
    pod["metadata"]["creationTimestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    update_pod(pod_key, pod)

    return node_name

def fetch_available_nodes_from_etcd():
    """
    Fetch the list of available nodes from etcd.
    Assuming the nodes are stored in '/registry/nodes' in etcd.
    """
    available_nodes = []
    for nodes_prefix in ['/registry/nodes/', '/registry/csinodes/', '/registry/minions/']:
        try:
            # Query etcd for available node names
            for value, metadata in etcd.get_prefix(nodes_prefix):
                node_name = metadata.key.decode().split('/')[-1]  # Extract node name from the key
                available_nodes.append(node_name)
            if available_nodes:
                break
        except Exception as e:
            print(f"Error fetching nodes from etcd: {e}")
    
    return available_nodes

def update_pod(key, pod):
    """
    Update a Pod in etcd as Protobuf encoded yaml.
    """
    etcd.put(key, auger_encode(pod))

if __name__ == "__main__":
    # Running the Flask app on port 8081
    app.run(host="0.0.0.0", port=8081)
