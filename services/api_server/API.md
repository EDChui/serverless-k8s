# API Endpoints for API Server

# POST /api/v1/{resource}

Create a resource in etcd.

## Example

Request: `POST /api/v1/pods`

form-data:
`key: file, value: xxx.yaml`

Response: `201 Created`

```json
{
  "message": "Pods 'mypod' created successfully"
}
```

# GET /api/v1/{resource}

Retrieve all resources of a type.

Query parameter: `namespace`

## Example

Request: `GET /api/v1/pods`

Response: `200 OK`

```json
{
  "data": [
    "/registry/pods/default/api-server-00001-deployment-6644f986c8-pt8gk",
    "/registry/pods/default/api-server-00001-deployment-7477b4cf49-grm75",
    "/registry/pods/default/api-server-00001-deployment-7477b4cf49-kscms"
  ]
}
```

# GET /api/v1/{resource}/{name}

Retrieve a resource. The response is the resource details in yaml format.

Query parameter: `namespace`

## Example

Request: `GET /api/v1/pods/api-server-00001-deployment-6644f986c8-pt8gk`

Response: `200 OK`

```json
{
    {
        "data": "apiVersion: v1\nkind: Pod\nmetadata:\n  annotations:\n..."
    }
}
```

# GET /api/v1/pods/{name}/status

Retrieve a pod resource status. This simulate the `kubectl get pods` command.

Query parameter: `namespace`

## Example

Request: `GET /api/v1/pods/api-server-00001-deployment-6644f986c8-pt8gk/status`

Response: `200 OK`

```json
{
  "data": {
    "pod_name": "api-server-00001-deployment-7477b4cf49-5p4x5",
    "pod_status": "Running",
    "ready_container_count": 2,
    "total_container_count": 2,
    "restart_count": 0,
    "age": "0m23s"
  }
}
```

# DELETE /api/v1/{resource}/{name}

Delete a resource from etcd.

Query parameter: `namespace`

## Example

Request: `DELETE /api/v1/pods/api-server-00001-deployment-6644f986c8-pt8gk`

Response: `200 OK`

```json
{
  "message": "Pods 'api-server-00001-deployment-6644f986c8-pt8gk' deleted successfully"
}
```
