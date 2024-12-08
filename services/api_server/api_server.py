from flask import Flask, request, jsonify
import etcd3
import os
from datetime import datetime
import json
import yaml
import traceback
import subprocess

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

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running"}), 200

@app.route('/api/v1/<resource>', methods=['POST'])
def create_resource(resource):
    """Create a resource in etcd."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files["file"]
        
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        elif not file.filename.endswith(".yaml"):
            return jsonify({"error": "Expect YAML file"}), 400

        data = yaml.safe_load(file.stream)
        namespace = data.get("metadata", {}).get("namespace", "default")
        resource_name = data.get("metadata", {}).get("name", "")
        if not resource_name:
            return jsonify({"error": "Resource name is required"}), 400

        etcd_key = f"/registry/{resource}/{namespace}/{resource_name}"
        etcd.put(etcd_key, auger_encode(yaml.safe_dump(data).encode()))
        return jsonify({"message": f"{resource.capitalize()} '{resource_name}' created successfully"}), 201
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
            pod_data = yaml.safe_load(auger_decode(value))

            # Extract pod data
            pod_name = pod_data.get("metadata", {}).get("name", "")
            pod_phase = pod_data.get("status", {}).get("phase", "")
            container_statuses = pod_data.get("status", {}).get("containerStatuses", [])
            creation_timestamp = pod_data.get("metadata", {}).get("creationTimestamp")
            deletion_timestamp = pod_data["metadata"].get("deletionTimestamp")

            # Determine the number of ready containers
            ready_containers = [container for container in container_statuses if container.get("ready", False)]
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
            restart_count = sum(container.get("restartCount", 0) for container in container_statuses)

            # Calculate the age of the pod by comparing current time
            if creation_timestamp:
                current_time = datetime.now()
                creation_time = datetime.strptime(creation_timestamp, "%Y-%m-%dT%H:%M:%SZ")
                age = current_time - creation_time
                age_minutes = int(age.total_seconds() // 60)
                age_seconds = int(age.total_seconds() % 60)
            else:
                age_minutes = 0
                age_seconds = 0

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

def auger_encode(data: bytes) -> bytes:
    try:
        # Run the Auger subprocess, simulating the CLI behavior
        process = subprocess.run(
            ["./auger/build/auger", "encode"],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        print("Auger error:", e.stderr.decode('utf-8'))
        return None

def auger_decode(data: bytes) -> str:
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
