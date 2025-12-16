# NeonDB Setup Guide

Complete guide for setting up NeonDB serverless PostgreSQL for ContriVerse.

## What is NeonDB?

NeonDB is a serverless PostgreSQL platform that provides:
- **Auto-scaling**: Automatically scales compute based on demand
- **Branching**: Create database branches like Git branches
- **Serverless**: Pay only for what you use, automatic pause on inactivity
- **Connection Pooling**: Built-in pooling for serverless environments
- **Point-in-time Recovery**: Restore to any point in time

## Step 1: Create NeonDB Account

1. Go to https://neon.tech
2. Sign up with GitHub (recommended) or email
3. Verify your email address

## Step 2: Create a New Project

1. Click **"New Project"** in the Neon console
2. Configure your project:
   - **Project name**: `contriverse` (or your preferred name)
   - **Region**: Choose closest to your users (e.g., `US East (Ohio)`)
   - **PostgreSQL version**: `16` (latest stable)
   - **Compute size**: Start with `0.25 CU` (can scale later)

3. Click **"Create Project"**

## Step 3: Understand Database Branches

NeonDB uses branches similar to Git:
- **main**: Production database
- **dev**: Development database (optional)
- **preview**: For testing migrations (optional)

For now, we'll use the default `main` branch.

## Step 4: Obtain Connection Strings

NeonDB provides two types of connection strings:

### Pooled Connection (for Application)
Used for application queries with connection pooling.

1. In your project dashboard, go to **"Connection Details"**
2. Select **"Pooled connection"**
3. Copy the connection string:
   ```
   postgresql://[user]:[password]@[host]/[database]?sslmode=require&pgbouncer=true
   ```

### Direct Connection (for Migrations)
Used for schema migrations and admin tasks.

1. In the same panel, select **"Direct connection"**
2. Copy the connection string:
   ```
   postgresql://[user]:[password]@[host]/[database]?sslmode=require
   ```

## Step 5: Configure Environment Variables

Add both connection strings to your `.env` file:

```bash
# NeonDB Pooled Connection (for application)
DATABASE_URL="postgresql://user:password@host/database?sslmode=require&pgbouncer=true"

# NeonDB Direct Connection (for migrations)
DIRECT_DATABASE_URL="postgresql://user:password@host/database?sslmode=require"
```

**Important**: 
- Keep these secrets secure
- Never commit them to Git
- Use different databases for dev/staging/production

## Step 6: SSL Configuration

NeonDB **requires** SSL connections. The connection strings include `sslmode=require` by default.

Verify SSL is enabled:
```bash
# The connection string should contain:
?sslmode=require
```

## Step 7: Test Connection

Test your connection using `psql`:

```bash
# Using pooled connection
psql "postgresql://user:password@host/database?sslmode=require&pgbouncer=true"

# Using direct connection
psql "postgresql://user:password@host/database?sslmode=require"
```

You should see:
```
psql (16.x)
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
Type "help" for help.

database=>
```

## Connection String Breakdown

```
postgresql://[user]:[password]@[host]/[database]?sslmode=require&pgbouncer=true
           │      │           │      │           │                │
           │      │           │      │           │                └─ Pooling enabled
           │      │           │      │           └─ SSL required
           │      │           │      └─ Database name
           │      │           └─ NeonDB host
           │      └─ Password
           └─ Username
```

## When to Use Each Connection Type

| Connection Type | Use Case | Example |
|----------------|----------|---------|
| **Pooled** | Application queries | FastAPI endpoints, background jobs |
| **Direct** | Migrations, admin tasks | Prisma migrate, database backups |

## NeonDB Features

### Auto-Scaling
- Compute automatically scales from 0.25 to 4 CU based on load
- Automatically pauses after 5 minutes of inactivity (free tier)
- Resumes instantly on new connections

### Branching
Create a database branch for development:
```bash
# In Neon console, click "Branches" → "Create Branch"
# Name: dev
# From: main
```

Use different connection strings for each branch.

### Monitoring
- View query performance in Neon console
- Monitor connection count
- Track compute usage
- Set up alerts for high usage

## Troubleshooting

### Connection Timeout
```
Error: connection timeout
```
**Solution**: Check that `sslmode=require` is in the connection string.

### Too Many Connections
```
Error: too many connections
```
**Solution**: Use the **pooled connection** string, not direct.

### SSL Required
```
Error: SSL connection required
```
**Solution**: Ensure `?sslmode=require` is in the connection string.

### Authentication Failed
```
Error: authentication failed
```
**Solution**: 
1. Verify username and password are correct
2. Check that you copied the full connection string
3. Ensure no extra spaces in the `.env` file

## Security Best Practices

1. **Use Environment Variables**: Never hardcode connection strings
2. **Rotate Passwords**: Regularly update database passwords
3. **Separate Databases**: Use different databases for dev/staging/prod
4. **Enable IP Allowlist**: Restrict access to known IPs (optional)
5. **Monitor Access**: Review connection logs regularly

## Next Steps

After setting up NeonDB:
1. Configure Prisma to use NeonDB connection strings
2. Generate Prisma client
3. Create initial migration
4. Apply migration to NeonDB

See [PRISMA_MIGRATION_GUIDE.md](PRISMA_MIGRATION_GUIDE.md) for migration instructions.

## Useful Links

- NeonDB Console: https://console.neon.tech
- NeonDB Documentation: https://neon.tech/docs
- Connection Pooling Guide: https://neon.tech/docs/connect/connection-pooling
- Branching Guide: https://neon.tech/docs/introduction/branching
