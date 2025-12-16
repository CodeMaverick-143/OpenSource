# Prisma Migration Guide

Complete guide for managing database migrations with Prisma and NeonDB.

## Prerequisites

1. NeonDB project created (see [NEONDB_SETUP.md](NEONDB_SETUP.md))
2. Connection strings configured in `.env`
3. Prisma installed: `pip install prisma`

## Initial Setup

### 1. Generate Prisma Client

Generate the Python client from the schema:

```bash
prisma generate
```

This creates the Prisma client in your Python environment based on `prisma/schema.prisma`.

### 2. Create Initial Migration

Create the first migration from your schema:

```bash
prisma migrate dev --name init
```

This will:
- Create `prisma/migrations/` directory
- Generate SQL migration files
- Apply the migration to your database
- Regenerate the Prisma client

## Development Workflow

### Creating a New Migration

When you change `schema.prisma`:

```bash
# 1. Update schema.prisma with your changes

# 2. Create and apply migration
prisma migrate dev --name describe_your_change

# 3. Prisma client is automatically regenerated
```

Example:
```bash
prisma migrate dev --name add_user_bio_field
```

### Applying Migrations

```bash
# Apply all pending migrations
prisma migrate deploy
```

Use `migrate deploy` in production (never `migrate dev`).

### Reset Database (Development Only)

**⚠️ WARNING: This deletes all data!**

```bash
prisma migrate reset
```

This will:
- Drop the database
- Create a new database
- Apply all migrations
- Run seed scripts (if configured)

## Production Migrations

### Safety First

1. **Never use `migrate dev` in production**
2. **Always use `migrate deploy`**
3. **Test migrations in staging first**
4. **Backup data before migrating**

### Production Migration Process

```bash
# 1. Create migration in development
prisma migrate dev --name your_change

# 2. Commit migration files to Git
git add prisma/migrations/
git commit -m "Add migration: your_change"

# 3. Deploy to production
# Set DIRECT_DATABASE_URL to production database
prisma migrate deploy
```

### Handling Migration Failures

If a migration fails:

```bash
# 1. Check migration status
prisma migrate status

# 2. Resolve the migration
prisma migrate resolve --applied MIGRATION_NAME  # If partially applied
prisma migrate resolve --rolled-back MIGRATION_NAME  # If needs rollback

# 3. Try deploying again
prisma migrate deploy
```

## Common Migration Scenarios

### Adding a New Model

1. Add model to `schema.prisma`:
```prisma
model NewModel {
  id        String   @id @default(uuid())
  name      String
  createdAt DateTime @default(now()) @map("created_at")
  
  @@map("new_models")
}
```

2. Create migration:
```bash
prisma migrate dev --name add_new_model
```

### Adding a Field

1. Update model in `schema.prisma`:
```prisma
model User {
  // ... existing fields
  bio String? @db.Text  // New field
}
```

2. Create migration:
```bash
prisma migrate dev --name add_user_bio
```

### Adding a Relation

1. Update models in `schema.prisma`:
```prisma
model User {
  id       String    @id @default(uuid())
  posts    Post[]    // New relation
}

model Post {
  id       String @id @default(uuid())
  authorId String @map("author_id")
  author   User   @relation(fields: [authorId], references: [id])
}
```

2. Create migration:
```bash
prisma migrate dev --name add_user_posts_relation
```

### Renaming a Field

Use `@map` to preserve database column name:

```prisma
model User {
  githubUsername String @map("github_username")  // Renamed in code, same in DB
}
```

No migration needed if only renaming in code!

### Making a Field Required

**⚠️ Requires data migration if existing rows have NULL values**

```prisma
model User {
  email String  // Changed from String? to String
}
```

Migration will fail if existing rows have NULL. Options:
1. Set default value: `email String @default("")`
2. Manually update existing rows before migration
3. Use multi-step migration

## Migration Files

### Structure

```
prisma/migrations/
├── 20250117000000_init/
│   └── migration.sql
├── 20250117000001_add_user_bio/
│   └── migration.sql
└── migration_lock.toml
```

### Migration SQL

Example `migration.sql`:
```sql
-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "github_id" BIGINT NOT NULL,
    "github_username" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_github_id_key" ON "users"("github_id");
```

## Prisma Studio

Explore your database with Prisma Studio:

```bash
prisma studio
```

Opens a web UI at `http://localhost:5555` to:
- View all tables
- Browse data
- Edit records
- Run queries

## Troubleshooting

### "Prisma Client not found"

```bash
# Regenerate client
prisma generate
```

### "Migration already applied"

```bash
# Check status
prisma migrate status

# Resolve if needed
prisma migrate resolve --applied MIGRATION_NAME
```

### "Connection timeout"

- Check `DIRECT_DATABASE_URL` is set correctly
- Ensure using direct connection (not pooled) for migrations
- Verify NeonDB is accessible

### "SSL required"

Ensure connection string includes `?sslmode=require`:
```
postgresql://user:pass@host/db?sslmode=require
```

## Best Practices

1. **Always test migrations locally first**
2. **Use descriptive migration names**
3. **One logical change per migration**
4. **Never edit migration files after creation**
5. **Commit migrations to version control**
6. **Use `migrate deploy` in production**
7. **Backup before destructive changes**
8. **Use staging environment for testing**

## Environment Variables

```bash
# For application (pooled)
DATABASE_URL="postgresql://...?pgbouncer=true"

# For migrations (direct)
DIRECT_DATABASE_URL="postgresql://...?sslmode=require"
```

Prisma automatically uses:
- `DATABASE_URL` for client operations
- `DIRECT_DATABASE_URL` for migrations

## Useful Commands

```bash
# Generate client
prisma generate

# Create migration (dev)
prisma migrate dev --name MIGRATION_NAME

# Apply migrations (prod)
prisma migrate deploy

# Check migration status
prisma migrate status

# Reset database (dev only)
prisma migrate reset

# Open Prisma Studio
prisma studio

# Validate schema
prisma validate

# Format schema
prisma format
```

## Next Steps

After setting up migrations:
1. Generate Prisma client: `prisma generate`
2. Apply migrations: `prisma migrate deploy`
3. Start application: `make run`
4. Verify database connectivity

## Additional Resources

- Prisma Migrate Docs: https://www.prisma.io/docs/concepts/components/prisma-migrate
- Prisma Python Client: https://prisma-client-py.readthedocs.io
- NeonDB + Prisma: https://neon.tech/docs/guides/prisma
