from flask import Flask, jsonify, request
import requests
import logging
import traceback

app = Flask(__name__)

# Configurations for other services (API Server or Scheduler)
API_SERVER_URL = "http://api-server-knative-service-url"
SCHEDULER_URL = "http://scheduler-knative-service-url"

# Logging setup
logging.basicConfig(level=logging.INFO)

@app.route('/')
def health_check():
    """
    Health check endpoint for the controller.
    """
    return jsonify({"status": "healthy"}), 200


@app.route('/trigger-scheduler', methods=['POST'])
def trigger_scheduler():
    """
    Trigger the scheduler to assign nodes to pending pods.
    """
    try:
        # Example request to Scheduler Knative Service to schedule Pods
        response = requests.post(f"{SCHEDULER_URL}/schedule")
        if response.status_code == 200:
            return jsonify({"message": "Scheduler triggered successfully", "data": response.json()}), 200
        else:
            logging.error(f"Failed to trigger scheduler: {response.status_code}")
            return jsonify({"error": "Failed to trigger scheduler"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal System Error"}), 500


@app.route('/trigger-api', methods=['POST'])
def trigger_api_server():
    """
    Trigger the API Server to create a new pod or resource.
    """
    try:
        # Example request to API Server Knative Service to create or manage Pods
        payload = request.json  # Get the input payload
        response = requests.post(f"{API_SERVER_URL}/create-pod", json=payload)
        if response.status_code == 200:
            return jsonify({"message": "API Server triggered successfully", "data": response.json()}), 200
        else:
            logging.error(f"Failed to trigger API server: {response.status_code}")
            return jsonify({"error": "Failed to trigger API server"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal System Error"}), 500


@app.route('/create-pod', methods=['POST'])
def create_pod():
    """
    Endpoint to create a new Pod via the API Server and then trigger the Scheduler.
    """
    try:
        # Step 1: Trigger the API Server to create the Pod
        payload = request.json  # Get the input payload for Pod creation
        logging.info("Creating Pod via API Server.")
        response = requests.post(f"{API_SERVER_URL}/create-pod", json=payload)

        if response.status_code == 200:
            pod_data = response.json()
            pod_key = pod_data.get('pod_key', None)

            if pod_key:
                # Step 2: Trigger the Scheduler to assign the Pod to a node
                logging.info(f"Scheduling Pod with key {pod_key}.")
                scheduler_response = requests.post(f"{SCHEDULER_URL}/schedule", json={"pod_key": pod_key})

                if scheduler_response.status_code == 200:
                    scheduler_data = scheduler_response.json()
                    return jsonify({
                        "message": "Pod created and scheduled successfully",
                        "pod_data": pod_data,
                        "scheduler_data": scheduler_data
                    }), 200
                else:
                    logging.error(f"Failed to trigger scheduler for Pod {pod_key}: {scheduler_response.status_code}")
                    return jsonify({"error": "Failed to trigger scheduler"}), 500
            else:
                logging.error("Pod creation failed: Pod key is missing in response.")
                return jsonify({"error": "Pod creation failed, no pod_key returned"}), 500
        else:
            logging.error(f"Failed to create Pod via API Server: {response.status_code}")
            return jsonify({"error": "Failed to create Pod via API Server"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Error during Pod creation or scheduling"}), 500

if __name__ == "__main__":
    # Running the Flask app on port 8082
    app.run(host="0.0.0.0", port=8082)
