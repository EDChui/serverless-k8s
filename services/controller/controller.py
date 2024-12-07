import json
import traceback
from flask import Flask, jsonify, request
from kubernetes import client, config
from kubernetes.client.rest import ApiException

app = Flask(__name__)

# Load kube config (ensure you have your kube config set up)
config.load_kube_config()  # Or use load_incluster_config() if running inside a pod

# Initialize the Kubernetes API client
v1 = client.CoreV1Api()

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "Controller is running"}), 200

@app.route('/pods', methods=['GET'])
def get_pods():
    """
    List all Pods in the default namespace
    """
    try:
      try:
          pods = v1.list_namespaced_pod(namespace='default')
          pods_list = [{"name": pod.metadata.name, "status": pod.status.phase} for pod in pods.items]
          return jsonify(pods_list), 200
      except ApiException as e:
          return jsonify({"error": f"Error fetching pods: {e}"}), 500
    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Error occurs"}), 500


@app.route('/pod', methods=['POST'])
def create_pod():
    """
    Create a Pod in the default namespace
    """
    try:
      data = request.get_json()

      # Create Pod Spec
      pod = client.V1Pod(
          metadata=client.V1ObjectMeta(name=data['name']),
          spec=client.V1PodSpec(containers=[client.V1Container(name='nginx', image='nginx')])
      )

      try:
          # Create Pod in Kubernetes
          created_pod = v1.create_namespaced_pod(namespace='default', body=pod)
          return jsonify({"message": "Pod created", "pod_name": created_pod.metadata.name}), 201
      except ApiException as e:
          return jsonify({"error": f"Error creating pod: {e}"}), 500
    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Error occurs"}), 500


@app.route('/pod/<name>', methods=['DELETE'])
def delete_pod(name):
    """
    Delete a Pod by name from the default namespace
    """
    try:
      try:
          v1.delete_namespaced_pod(name=name, namespace='default')
          return jsonify({"message": f"Pod {name} deleted"}), 200
      except ApiException as e:
          return jsonify({"error": f"Error deleting pod: {e}"}), 500
    except Exception as error:
        traceback.print_exc()
        return jsonify({"error": "Error occurs"}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8082, debug=True)
