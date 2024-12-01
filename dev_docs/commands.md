# Commands For Self-Reference

# etcd

## Get endpoint status

`etcdctl endpoint status`

## Put key-value pair

`etcdctl put /foo "Hello world"`

## Get value using key

`etcdctl get /foo`

## Access with cert

```sh
etcdctl --cacert=./run/config/pki/etcd/ca.crt \
        --cert=./run/config/pki/etcd/server.crt \
        --key=./run/config/pki/etcd/server.key \
        endpoint status
```

# Kubernetes (k8s)

## Get current cluster context

`kubectl config current-context`

## Switch cluster context

`kubectl config use-context docker-desktop `

## etcd

### List etcd pods

`kubectl get pods -n kube-system | grep etcd`

### Connect to the etcd pod

`kubectl exec -n kube-system -it etcd-your-node-name -- /bin/sh`

Example:

`kubectl -n kube-system exec -ti etcd-docker-desktop -- sh`
