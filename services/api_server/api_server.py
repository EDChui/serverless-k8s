from flask import Flask, request, jsonify
import etcd3
import os
from datetime import datetime
import json
import yaml
import traceback
import subprocess
import requests
import uuid
from datetime import datetime

# Initialize Flask App
app = Flask(__name__)

# Constant
SCHEDULER_URL = "http://knative-scheduler.default.127.0.0.1.sslip.io"

# etcd Configuration
ETCD_HOST = "172.18.0.2"
ETCD_PORT = 2379

# Path to certificates
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
    return jsonify({"status": "API is running"}), 200

@app.route('/api/v1/<resource>', methods=['POST'])
def create_resource(resource):
    """Create a resource in etcd."""
    try:
        data = request.json
        resource_name = data.get("metadata", {}).get("name", "")
        if not resource_name:
            return jsonify({"error": "Resource name is required"}), 400

        namespace = data.get("metadata", {}).get("namespace", "default")
        etcd_key = f"/registry/{resource}/{namespace}/{resource_name}"

        # Step 1: Store Pod in etcd
        etcd.put(etcd_key, json.dumps(data))

        # Step 2: Trigger the Scheduler to assign a node to the Pod
        scheduling_response = trigger_scheduler(etcd_key)
        
        if scheduling_response.get("status") == "success":
            return jsonify({
                "message": f"{resource.capitalize()} '{resource_name}' created and scheduled successfully",
                "assigned_node": scheduling_response["assigned_node"]
            }), 201
        else:
            return jsonify({
                "error": "Failed to schedule resource",
                "details": scheduling_response
            }), 500

    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Internal System Error"}), 500  

@app.route('/api/v1/<resource>/<name>', methods=['GET'])
def get_resource(resource, name):
    """Retrieve a resource from etcd."""
    try:
        namespace = request.args.get("namespace", "default")
        etcd_key = f"/registry/{resource}/{namespace}/{name}"

        value, _ = etcd.get(etcd_key)
        if value:
            return jsonify({"data": auger_decode(value)}), 200
        else:
            return jsonify({"error": f"{resource.capitalize()} '{name}' not found"}), 404
        
    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Internal System Error"}), 500

@app.route('/api/v1/pods/<name>/status', methods=['GET'])
def get_resource_status(name):
    """Retrieve the pod status from etcd. This simulate the `kubectl get pods` command."""
    try:
        namespace = request.args.get("namespace", "default")
        etcd_key = f"/registry/pods/{namespace}/{name}"

        value, _ = etcd.get(etcd_key)

        if value:
            pod_data = detect_and_parse(value)

            # Extract pod data
            pod_name = pod_data["metadata"]["name"]
            pod_phase = pod_data["status"]["phase"]
            container_statuses = pod_data["status"]["containerStatuses"]
            creation_timestamp = pod_data["metadata"]["creationTimestamp"]
            deletion_timestamp = pod_data["metadata"].get("deletionTimestamp")

            # Determine the number of ready containers
            ready_containers = [container for container in container_statuses if container["ready"]]
            total_container_count = len(container_statuses)
            ready_container_count = len(ready_containers)

            # Determine the pod status
            if deletion_timestamp:
                pod_status = "Terminating"
            elif pod_phase == "Running":
                pod_status = "Running"
            else:
                pod_status = "Unknown"

            # Calculate restarts
            restart_count = sum(container["restartCount"] for container in container_statuses)

            # Calculate the age of the pod by comparing current time
            current_time = datetime.now()
            creation_time = datetime.strptime(creation_timestamp, "%Y-%m-%dT%H:%M:%SZ")
            age = current_time - creation_time
            age_minutes = int(age.total_seconds() // 60)
            age_seconds = int(age.total_seconds() % 60)

            status = {
                "pod_name": pod_name,
                "ready_container_count": ready_container_count,
                "total_container_count": total_container_count,
                "pod_status": pod_status,
                "restart_count": restart_count,
                "age": f"{age_minutes}m{age_seconds}s"
            }
            
            return jsonify({"data": status}), 200
        else:
            return jsonify({"error": f"pod '{name}' not found"}), 404
        
    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Internal System Error"}), 500

@app.route('/api/v1/<resource>', methods=['GET'])
def list_resources(resource):
    """List all resources of a type."""
    try:
        namespace = request.args.get("namespace", "default")
        prefix = f"/registry/{resource}/{namespace}/"

        resources = []
        for value, metadata in etcd.get_prefix(prefix):
            resources.append(metadata.key.decode())

        return jsonify({"data": resources}), 200
    
    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Internal System Error"}), 500

@app.route('/api/v1/<resource>/<name>', methods=['DELETE'])
def delete_resource(resource, name):
    """Delete a resource from etcd."""
    try:
        namespace = request.args.get("namespace", "default")
        etcd_key = f"/registry/{resource}/{namespace}/{name}"

        deleted = etcd.delete(etcd_key)
        if deleted:
            return jsonify({"message": f"{resource.capitalize()} '{name}' deleted successfully"}), 200
        else:
            return jsonify({"error": f"{resource.capitalize()} '{name}' not found"}), 404
    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Internal System Error"}), 500

def trigger_scheduler(pod_key):
    """
    Trigger the Scheduler Knative Service to assign the Pod to a node.
    """
    try:
        response = requests.post(f"{SCHEDULER_URL}/schedule", json={"pod_key": pod_key})
        if response.status_code == 200:
            return {"status": "success", "assigned_node": response.json()["assigned_node"]}
        else:
            return {"status": "failure", "error": "Failed to schedule Pod"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

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
    try:
        # Run the Auger subprocess, simulating the CLI behavior
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
