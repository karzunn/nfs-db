![Logo](logo.png)

# nfs-db

nfs-db is *not* a database engine. It is a lightweight Python interface that lets you interact with an existing NFS server through familiar database-style operations.

### Why nfs-db?

For small projects already utilizing a NFS server, using nfs-db avoids the infrastructure complexity and operational requirements that traditional databases bring.

### What to expect

nfs-db is not intended to compete with traditional database engines. Filesystem operations introduce overhead, and performance will not be comparable to purpose-built database systems.

nfs-db is best suited for:

- Small applications and utilities.
- Shared application state across multiple machines.
- Data processing pipelines operating on shared NFS storage.
- Workloads where atomic operations matter more than raw throughput.

It is not intended for large datasets, high-throughput workloads, or applications requiring the advanced capabilities of a traditional database.
