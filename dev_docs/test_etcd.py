# requirements:
# etcd3
# protobuf == 3.19.0

import etcd3

etcd = etcd3.client()

# List all key-value pairs.
for value, metadata in etcd.get_prefix("/"):
    print(metadata.key.decode(), value.decode())