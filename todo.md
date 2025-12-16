# Open Contribution Platform - Roadmap

> Goal: Build a production-ready platform that tracks GitHub PR contributions, reviews them, and ranks contributors fairly.

---

## ✅ PHASE 1 — System Setup (COMPLETE)

### Repo & Tooling

* [x] Initialize git repository
* [x] Setup `.editorconfig`
* [x] Setup `.gitignore`
* [x] Setup pre-commit hooks (black, isort, ruff)
* [x] Setup basic CI (GitHub Actions with lint + tests)

### Infrastructure

* [x] Setup NeonDB (serverless PostgreSQL)
* [x] Setup Prisma ORM (replaced SQLAlchemy + Alembic)
* [x] Setup Redis
* [x] Setup background worker (Celery)
* [x] Setup environment config system (Pydantic Settings)
* [x] Setup logging + structured logs (structlog)

---

## ✅ PHASE 2 — Authentication & Identity (COMPLETE)

### GitHub OAuth

* [x] Register GitHub OAuth App
* [x] Implement OAuth login flow
* [x] Store GitHub user identity (github_id as primary)
* [x] Handle username changes (detected and logged)
* [x] Handle revoked access (graceful error handling)
* [x] Implement logout (refresh token invalidation)
* [x] JWT access tokens (30 min expiry)
* [x] JWT refresh tokens (7 days expiry with rotation)

### Edge Cases

* [x] Duplicate GitHub accounts prevention (unique constraint)
* [x] Soft-delete users (is_deleted flag)
* [x] Ban / unban users (is_banned flag)

---

## ✅ PHASE 3 — Core Data Models (COMPLETE)

### Database Migration to Prisma + NeonDB

* [x] Migrate from SQLAlchemy to Prisma ORM
* [x] Setup NeonDB serverless PostgreSQL
* [x] Create Prisma schema with 13 models
* [x] Generate and apply migrations
* [x] Prisma client integration

### Data Models (Schema Complete)

* [x] Users table (with GitHub OAuth identity)
* [x] RefreshTokens table (JWT session management)
* [x] Projects table (with slug, owner, versioned rules)
* [x] ProjectMaintainers table (RBAC)
* [x] Repositories table (with sync status)
* [x] PullRequests table (PR tracking)
* [x] PRReviews table (review system)
* [x] PointTransactions table (scoring history)
* [x] Badges table (achievement definitions)
* [x] UserBadges table (user achievements)
* [x] AuditLogs table (security logging)
* [x] GitHubTokens table (encrypted token storage)
* [x] WebhookDeliveries table (idempotency tracking)

### Service Layer Migration

* [x] Refactor UserService to use Prisma
* [x] Refactor AuthService to use Prisma
* [x] Remove SQLAlchemy models
* [x] Remove Alembic migrations
* [ ] Update test fixtures for Prisma

---

## ✅ PHASE 4 — GitHub Integration (COMPLETE)

### GitHub API Clients

* [x] Implement GitHub REST client (rate limiting, pagination, ETags)
* [x] Implement GitHub GraphQL client (bulk operations)
* [x] Handle API rate limits with exponential backoff
* [x] Token management and refresh logic

### Webhooks

* [x] Create webhook endpoint (`POST /api/v1/webhooks/github`)
* [x] Verify webhook signatures (HMAC-SHA256)
* [x] Handle `pull_request` events (opened, synchronize, reopened, closed)
* [x] Handle `push` events (default branch)
* [x] Handle `repository` events (renamed, transferred, privatized, deleted)
* [x] Implement retry logic with Celery

### Idempotency & Edge Cases

* [x] Webhook duplication handling (delivery ID tracking)
* [x] Out-of-order webhook events
* [x] GitHub downtime fallback
* [x] Manual resync job (skeleton)
* [x] Token validation and revocation detection

---

## ✅ PHASE 5 — Project & Repository Management (COMPLETE)

### Project CRUD

* [x] Create project with URL-safe slug generation
* [x] List/get projects with pagination
* [x] Update project metadata
* [x] Archive/unarchive project (soft delete)
* [x] Versioned contribution rules (never retroactive)

### Maintainer Management

* [x] Add/remove maintainers with validation
* [x] List maintainers
* [x] RBAC permissions (owner > maintainer > contributor)
* [x] Permission decorators (`@require_project_owner`, etc.)
* [x] Prevent owner removal

### Repository Management

* [x] Register GitHub repository with validation
* [x] Validate ownership & permissions (admin/maintain required)
* [x] Auto-create webhooks on GitHub
* [x] Sync repository metadata from GitHub
* [x] Disable/enable repositories with reasons
* [x] Handle forks & private repos
* [x] Prevent duplicate registration (one repo = one project)

---

## ✅ PHASE 6 — PR Tracking Engine (COMPLETE)

### PR State Machine & Lifecycle

* [x] Define PR states (OPEN, UNDER_REVIEW, CHANGES_REQUESTED, APPROVED, MERGED, CLOSED)
* [x] Implement state transition validator
* [x] Add lifecycle timestamps (openedAt, reviewedAt, approvedAt, mergedAt, closedAt)
* [x] Prevent invalid state transitions
* [x] Track PR state transitions with logging

### Idempotency & Duplicate Safety

* [x] Event fingerprinting system (SHA-256 hash)
* [x] Store processed webhook events with fingerprints
* [x] Prevent double-scoring on webhook retries
* [x] Handle out-of-order events
* [x] Ensure exactly-once scoring guarantee
* [x] Track scoring application per event

### Advanced Scoring Engine

* [x] Rule-based scoring with project contribution rules
* [x] Quality bonus based on diff size (100/500/1000+ lines)
* [x] Gaming prevention (caps per repo per month)
* [x] Diminishing returns after threshold
* [x] Score modifiers (PR type, diff size, files changed)
* [x] Reviewer rating integration (ready)

### Point Transaction Ledger

* [x] Append-only transaction ledger
* [x] Atomic user total_points updates
* [x] Transaction types (AWARD, BONUS, PENALTY, REVERSAL)
* [x] Never mutate transaction history
* [x] Reversal transactions for corrections
* [x] Ledger integrity verification

### Background Jobs

* [x] Repository PR sync job (fetch all PRs from GitHub)
* [x] Stale PR detection job (inactive for X days)
* [x] Idempotent job design (safe to re-run)
* [ ] Periodic PR status sync job
* [ ] Abandoned PR auto-handling job

### Database Schema

* [x] Add lifecycle timestamps to PullRequest model
* [x] Add scoringMetadata JSON field
* [x] Add event fingerprint to WebhookDelivery
* [x] Add scoringApplied flag to WebhookDelivery
* [x] Add transactionType to PointTransaction
* [x] Generate and apply Prisma migration

---

## 👀 PHASE 7 — Review System

### Maintainer Reviews

* [ ] View PRs for their projects
* [ ] Mark PR as under review
* [ ] Request changes
* [ ] Approve PR internally
* [ ] Rate PR quality (1-5 stars)
* [ ] Add internal comments

### Review Workflow

* [ ] PR status: OPEN → UNDER_REVIEW → CHANGES_REQUESTED/APPROVED → MERGED/CLOSED
* [ ] Notify contributors of review status
* [ ] Track review history

### Edge Cases

* [ ] Multiple maintainers reviewing same PR
* [ ] Conflicting reviews (approval vs rejection)
* [ ] Maintainer inactivity timeout
* [ ] Reviewer abuse detection

---

## 📊 PHASE 8 — Scoring & Leaderboard

### Advanced Scoring Engine

* [ ] Define project-specific scoring rules
* [ ] Apply contribution rules to new PRs
* [ ] Quality multipliers (code review, tests, docs)
* [ ] Negative points for spam/low-value PRs
* [ ] Recalculate user ranks

### Leaderboards

* [ ] Global leaderboard (all-time)
* [ ] Monthly leaderboard (time-based)
* [ ] Project-wise leaderboard
* [ ] Skill/tag-based leaderboard
* [ ] Leaderboard caching (Redis)

### Anti-Gaming Measures

* [ ] Diff-size based spam detection
* [ ] PR frequency throttling (max PRs per period)
* [ ] Same-repo farming detection
* [ ] Low-value PR penalty (typo-only, whitespace)
* [ ] Admin override tools
* [ ] Suspicious activity alerts

---

## 🧑‍💻 PHASE 9 — Contributor Dashboard

### PR Management

* [ ] View active PRs
* [ ] View PRs under review
* [ ] View merged PRs
* [ ] View rejected/closed PRs
* [ ] Filter by project/repository

### Profile & Progress

* [ ] View points history
* [ ] View earned badges
* [ ] View rank & progress
* [ ] View contribution graph
* [ ] View skill tags

---

## 🧑‍🔧 PHASE 10 — Maintainer Dashboard

### Project Management

* [ ] View project PRs
* [ ] Filter PRs by status (open, under review, approved, etc.)
* [ ] Review PR details
* [ ] Add internal comments
* [ ] Approve / reject PRs
* [ ] View contributor stats

### Analytics

* [ ] Project contribution metrics
* [ ] Top contributors
* [ ] PR merge rate
* [ ] Average review time
* [ ] Quality trends

---

## 🏆 PHASE 11 — Badges & Achievements

### Badge System

* [ ] Define badge criteria (JSON schema)
* [ ] Auto-award badges on milestones
* [ ] Manual badge awards (admin)
* [ ] Badge rarity levels
* [ ] Badge display on profile

### Achievement Types

* [ ] First PR merged
* [ ] 10/50/100 PRs merged
* [ ] Quality contributor (high avg rating)
* [ ] Project champion (most PRs in project)
* [ ] Streak achievements (consecutive months)

---

## 🛡️ PHASE 12 — Security & Abuse Protection

### Security

* [x] Webhook signature validation (HMAC-SHA256)
* [x] JWT token security
* [x] GitHub token encryption (placeholder)
* [ ] Rate limiting (API endpoints)
* [ ] IP throttling
* [x] Audit logging (AuditLog model)
* [ ] CORS configuration
* [ ] SQL injection prevention (Prisma handles this)

### Abuse Protection

* [ ] Admin moderation panel
* [ ] Ban/unban users
* [ ] Flag suspicious PRs
* [ ] Dispute resolution workflow
* [ ] Appeal system
* [ ] Automated spam detection

---

## 🚀 PHASE 13 — Deployment & Ops

### Production Setup

* [ ] Production database configuration (NeonDB)
* [ ] Background workers deployment (Celery + Redis)
* [ ] Webhook endpoint exposure (public URL)
* [ ] Environment variables management
* [ ] SSL/TLS certificates

### Monitoring & Reliability

* [ ] Health checks (database, Redis, Celery)
* [ ] Monitoring & alerts (Sentry, Datadog, etc.)
* [ ] Logging aggregation
* [ ] Performance monitoring
* [ ] Error tracking

### Backup & Recovery

* [ ] Database backup strategy
* [ ] Point-in-time recovery
* [ ] Disaster recovery plan
* [ ] Data retention policy

---

## 🧪 PHASE 14 — Testing

### Unit Tests

* [ ] Service layer tests (ProjectService, RepositoryService, etc.)
* [ ] Permission decorator tests
* [ ] Slug generation tests
* [ ] Scoring algorithm tests

### Integration Tests

* [ ] GitHub webhook integration tests
* [ ] OAuth flow tests
* [ ] PR tracking end-to-end tests
* [ ] Repository registration tests

### Edge Case Tests

* [ ] Webhook replay tests
* [ ] Out-of-order event tests
* [ ] Abuse scenario tests
* [ ] Race condition tests
* [ ] Load testing leaderboard queries

---

## 📢 PHASE 15 — Launch & Growth

### Pre-Launch

* [ ] Seed with demo projects
* [ ] Invite maintainers
* [ ] Write contributor guide
* [ ] Write maintainer guide
* [ ] Publish API documentation
* [ ] Create demo video

### Launch

* [ ] Announce on GitHub
* [ ] Announce on Twitter/X
* [ ] Post on Reddit (r/opensource, r/programming)
* [ ] Product Hunt launch
* [ ] Hacker News post

### Post-Launch

* [ ] Collect feedback
* [ ] Monitor metrics (signups, PRs, engagement)
* [ ] Iterate based on feedback
* [ ] Fix bugs quickly
* [ ] Add requested features

---

## 📝 Current Status

**Completed Phases**: 1, 2, 3, 4, 5, 6 (6/15)

**In Progress**: Phase 7 (Review System)

**Next Up**: Build review system, then advanced scoring & leaderboards

**Total Progress**: ~40% complete

---

## 🎯 Recent Milestones

**Phase 6 - PR Tracking Engine** ✅
- Implemented production-grade state machine with 6 states
- Event fingerprinting for idempotency (exactly-once scoring)
- Advanced scoring engine with gaming prevention
- Append-only point ledger with atomic updates
- Background jobs for PR sync and stale detection
- ~1,200 lines of hardened production code