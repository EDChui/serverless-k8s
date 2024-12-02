from flask import Flask, request, jsonify
import etcd3
import os

dirname = os.path.dirname(__file__)
ca_cert = os.path.join(dirname, 'certs/ca.crt')
cert_cert = os.path.join(dirname, 'certs/client.crt')
cert_key = os.path.join(dirname, 'certs/client.key')

# Initialize Flask App
app = Flask(__name__)

# Initialize etcd3 Client
etcd = etcd3.client(
    host="https://127.0.0.1",
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
    data = request.json
    resource_name = data.get("metadata", {}).get("name", "")
    if not resource_name:
        return jsonify({"error": "Resource name is required"}), 400

    namespace = data.get("metadata", {}).get("namespace", "default")
    etcd_key = f"/registry/{resource}/{namespace}/{resource_name}"

    etcd.put(etcd_key, jsonify(data))
    return jsonify({"message": f"{resource.capitalize()} '{resource_name}' created successfully"}), 201

@app.route('/api/v1/<resource>/<name>', methods=['GET'])
def get_resource(resource, name):
    """Retrieve a resource from etcd."""
    namespace = request.args.get("namespace", "default")
    etcd_key = f"/registry/{resource}/{namespace}/{name}"

    value, _ = etcd.get(etcd_key)
    if value:
        return jsonify({"data": value.decode()}), 200
    else:
        return jsonify({"error": f"{resource.capitalize()} '{name}' not found"}), 404

@app.route('/api/v1/<resource>', methods=['GET'])
def list_resources(resource):
    """List all resources of a type."""
    namespace = request.args.get("namespace", "default")
    prefix = f"/registry/{resource}/{namespace}/"

    resources = []
    for value, metadata in etcd.get_prefix(prefix):
        resources.append(value.decode())

    return jsonify({"data": resources}), 200

@app.route('/api/v1/<resource>/<name>', methods=['DELETE'])
def delete_resource(resource, name):
    """Delete a resource from etcd."""
    namespace = request.args.get("namespace", "default")
    etcd_key = f"/registry/{resource}/{namespace}/{name}"

    deleted = etcd.delete(etcd_key)
    if deleted:
        return jsonify({"message": f"{resource.capitalize()} '{name}' deleted successfully"}), 200
    else:
        return jsonify({"error": f"{resource.capitalize()} '{name}' not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
