# PostgreSQL 16/17 Production Hardening & Network Isolation Guide

This document details how PostgreSQL is hardened to ensure **zero unauthorized external exposure**, restricting access strictly to `localhost` or private internal VPC subnets.

---

## 1. Restrict Listening Addresses (`postgresql.conf`)

By default, an improperly configured PostgreSQL instance listens on `0.0.0.0` or `*`, exposing port 5432 to the public internet.

In production:
Locate `postgresql.conf` (e.g. `/etc/postgresql/17/main/postgresql.conf` on Linux or `C:\Program Files\PostgreSQL\17\data\postgresql.conf` on Windows):

```ini
# Only listen on local loopback interface
listen_addresses = '127.0.0.1'

# Port
port = 5432

# Max connections tuned for workforce app
max_connections = 100

# Password encryption - enforce modern SCRAM-SHA-256
password_encryption = scram-sha-256

# SSL for internal database transport
ssl = on
```

If deployed on AWS / GCP / Azure in a VPC, set:
```ini
# Internal VPC IP only (e.g. 10.0.1.50)
listen_addresses = 'localhost, 10.0.1.50'
```

---

## 2. Restrict Client Authentication (`pg_hba.conf`)

Locate `pg_hba.conf` and replace permissive settings with strict rules:

```ini
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             postgres                                peer
local   all             all                                     scram-sha-256

# IPv4 local connections: ONLY loopback
host    prashant_group  all             127.0.0.1/32            scram-sha-256

# IPv6 local connections: ONLY loopback
host    prashant_group  all             ::1/128                 scram-sha-256

# VPC Private Subnet (Optional, if app and DB are on separate VPC nodes)
# host    prashant_group  all           10.0.0.0/16             scram-sha-256

# REJECT ALL OTHER CONNECTIONS EXPLICITLY
host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
```

---

## 3. Dedicated Least-Privilege Production Role

Do not run the application as the `postgres` superuser. Run the hardening SQL script:

```sql
-- Create dedicated application user with strong password
CREATE USER prashant_prod_user WITH PASSWORD 'STRONG_PRODUCTION_PASSWORD_HERE';

-- Grant access only to the prashant_group database
GRANT CONNECT ON DATABASE prashant_group TO prashant_prod_user;

-- Switch to the database and grant table privileges
\c prashant_group

GRANT USAGE ON SCHEMA public TO prashant_prod_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO prashant_prod_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO prashant_prod_user;

-- Ensure future migrations also grant privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO prashant_prod_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO prashant_prod_user;

-- Revoke dangerous superuser capabilities
ALTER USER prashant_prod_user NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
```

---

## 4. Verification Check

To verify PostgreSQL is NOT accessible remotely:

```bash
# On external machine or terminal:
nc -zv <YOUR_SERVER_PUBLIC_IP> 5432
# Result MUST be: Connection refused or timeout (filtered by firewall)

# On local server:
netstat -ano | grep 5432
# Result MUST show: 127.0.0.1:5432 (NOT 0.0.0.0:5432)
```
