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

## ✅ PHASE 7 — Review System (COMPLETE)

### Maintainer Review APIs

* [x] List PRs for maintainer's projects (with filtering/sorting)
* [x] Filter by state, project, repository
* [x] Sort by age, activity, last_updated
* [x] Transition PR states (OPEN → UNDER_REVIEW → APPROVED)
* [x] Add internal comments (platform-only)
* [x] Add quality ratings (1-5 stars)
* [x] Permission checks (maintainer only, not banned)

### Review Workflow & State Machine

* [x] Review state transitions (UNDER_REVIEW → CHANGES_REQUESTED/APPROVED)
* [x] GitHub merge/close overrides platform state
* [x] Notify contributors of review status
* [x] Track review history (immutable audit trail)
* [x] All review actions logged

### Multiple Maintainers & Conflict Resolution

* [x] Handle multiple maintainers reviewing same PR
* [x] Detect conflicting reviews (approval vs rejection)
* [x] Majority-based conflict resolution
* [x] Owner override capability
* [x] Conflict state visibility (explicit, not silent)
* [x] Deterministic final outcomes

### Maintainer Inactivity & Timeouts

* [x] Detect review timeouts (PRs stuck in UNDER_REVIEW)
* [x] Auto-release stale reviews (back to OPEN)
* [x] Notify contributors of delays
* [x] Background job for timeout detection

### Reviewer Abuse Detection

* [x] Review frequency limits (max 50/day)
* [x] Spam rejection detection (>80% rejection rate)
* [x] Targeted blocking detection (3+ same contributor)
* [x] Rating manipulation detection (>90% extreme ratings)
* [x] Audit flags for admin review
* [x] Temporary blocks on abuse detection

### Database Schema

* [x] Enhanced PRReview model (action, internalComment, isConflicting)
* [x] ReviewComment model (platform-only comments)
* [x] ReviewConflict model (conflict tracking & resolution)
* [x] Generate and apply Prisma migration

---

## ✅ PHASE 8 — Scoring & Leaderboard (COMPLETE)

### Advanced Scoring Engine

* [x] Define project-specific scoring rules
* [x] Apply contribution rules to new PRs
* [x] Quality multipliers (code review, tests, docs)
* [x] Negative points for spam/low-value PRs
* [x] Recalculate user ranks
* [x] Deterministic rank calculation with tie-breaking
* [x] Explainable score breakdowns
* [x] Exactly-once execution guarantee

### Leaderboards

* [x] Global leaderboard (all-time)
* [x] Monthly leaderboard (time-based)
* [x] Project-wise leaderboard
* [x] Skill/tag-based leaderboard
* [x] Leaderboard caching (Redis with TTLs)
* [x] Cache invalidation on score updates
* [x] Pagination support for all leaderboards

### Anti-Gaming Measures

* [x] Diff-size based spam detection
* [x] PR frequency throttling (max PRs per period)
* [x] Same-repo farming detection
* [x] Low-value PR penalty (typo-only, whitespace)
* [x] Admin override tools
* [x] Suspicious activity alerts
* [x] Score freeze capability
* [x] Transaction reversal system
* [x] Audit logging for all admin actions

---

## ✅ PHASE 9 — Contributor Dashboard (COMPLETE)

### PR Management (Backend Complete ✅)

* [x] Backend: PR list API with filtering (status, project, repo)
* [x] Backend: PR sorting (recent, score, oldest)
* [x] Backend: Pagination support
* [x] Backend: Include project/repo names, GitHub links, points
* [x] Frontend: View active PRs
* [x] Frontend: View PRs under review
* [x] Frontend: View merged PRs
* [x] Frontend: View rejected/closed PRs
* [x] Frontend: Filter by project/repository

### Profile & Progress (Backend Complete ✅)

* [x] Backend: Points history API (ledger view)
* [x] Backend: Rank info API (from snapshots)
* [x] Backend: Badges API (earned + available)
* [x] Backend: Contribution graph API (30d, 90d, all)
* [x] Backend: Skills API (computed from project tags)
* [x] Backend: Dashboard stats API (summary)
* [x] Frontend: View points history
* [x] Frontend: View earned badges
* [x] Frontend: View rank & progress
* [x] Frontend: View contribution graph
* [x] Frontend: View skill tags
* [x] Frontend: TypeScript types for dashboard APIs (BadgeResponse, snake_case properties)

---

## 🧑‍🔧 PHASE 10 — Maintainer Dashboard (Backend Complete ✅)

### Project Management (Backend Complete ✅)

* [x] Backend: List maintainer projects API
* [x] Backend: PR list API with filtering/sorting
* [x] Backend: PR detail API with full context
* [x] Backend: Internal comments API
* [x] Backend: Contributor stats API (per-project)
* [x] Backend: Project analytics API
* [x] Backend: RBAC middleware for maintainer access
* [x] Frontend: View project PRs
* [ ] Frontend: Filter PRs by status (open, under review, approved, etc.)
* [ ] Frontend: Review PR details
* [ ] Frontend: Add internal comments
* [ ] Frontend: Approve / reject PRs
* [ ] Frontend: View contributor stats

### Analytics (Backend Complete ✅)

* [x] Backend: Contribution volume over time
* [x] Backend: Top contributors query
* [x] Backend: PR merge rate calculation
* [x] Backend: Average review time
* [x] Backend: Quality trends (rating distribution)
* [ ] Frontend: Project contribution metrics
* [ ] Frontend: Top contributors display
* [ ] Frontend: PR merge rate chart
* [ ] Frontend: Average review time chart
* [ ] Frontend: Quality trends visualization

---

## ✅ PHASE 11 — Badges & Achievements (COMPLETE)

### Badge System (Backend Complete ✅)

* [x] Backend: Enhanced Badge model (rarity, category, version)
* [x] Backend: UserBadge model with manual/auto tracking
* [x] Backend: BadgeAuditLog model for full audit trail
* [x] Backend: Badge service (award, revoke, stats)
* [x] Backend: Badge evaluator (criteria evaluation)
* [x] Backend: Badge APIs (list, get, user badges, progress)
* [x] Backend: Admin APIs (manual award, revoke, audit logs)
* [x] Backend: Celery tasks for auto-award
* [x] Backend: 12 initial badge definitions
* [x] Frontend: TypeScript types (BadgeResponse interface matching backend schema)
* [x] Frontend: Define badge criteria (JSON schema)
* [x] Frontend: Badge display on profile
* [x] Frontend: Badge rarity styling
* [x] Frontend: Badge progress tracking

### Achievement Types (Backend Complete ✅)

* [x] Backend: First PR merged badge
* [x] Backend: 10/50/100/500 PRs merged badges
* [x] Backend: Quality contributor badges (rating-based)
* [x] Backend: Project champion badge (dominance-based)
* [x] Backend: Streak achievements (3/6/12/24 months)
* [x] Backend: Auto-award engine with idempotency
* [x] Frontend: Achievement display
* [x] Frontend: Achievement notifications
* [x] Frontend: Achievement progress tracking

---

## 🛡️ PHASE 12 — Security & Abuse Protection

### Security

* [x] Webhook signature validation (HMAC-SHA256)
* [x] JWT token security
* [x] GitHub token encryption (placeholder)
* [x] Rate limiting (API endpoints)
* [x] IP throttling
* [x] Audit logging (AuditLog model)
* [x] CORS configuration
* [x] SQL injection prevention (Prisma handles this)

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

**Completed Phases**: 1, 2, 3, 4, 5, 6, 7, 8, 9 (Backend + Frontend), 10 (Backend), 11 (Backend + Frontend) (11/15 phases)

**In Progress**: Phase 10 (Frontend - Maintainer Tools)

**Next Up**: Complete maintainer tools and start Phase 12 (Security)

**Total Progress**: ~75% complete (backend ~85%, frontend ~65%)

---

## 🎯 Recent Milestones

**Phase 9 & 11 - Frontend Implementation** ✅ (Dec 19, 2024)
- Implemented Contributor Dashboard pages (`/dashboard`, `/dashboard/prs`)
- Implemented Badge Gallery and filtering (`/badges`)
- Created reusable components: `PRCard`, `PointsHistory`, `ContributionGraph`, `BadgeGrid`, `RankDisplay`
- Integrated frontend with backend APIs using typed `api` client
- Fully responsive design with Tailwind CSS
- Resolved all TypeScript errors in dashboard and badge components

**TypeScript Type Fixes - Frontend** ✅ (Dec 19, 2024)
- Fixed implicit `any[]` type error in `badges/index.astro` by adding explicit `Badge[]` type annotation
- Created `BadgeResponse` interface matching backend dashboard API schema (snake_case properties)
- Updated `BadgesResponse` to use `BadgeResponse[]` instead of `Badge[]`
- Resolved property name mismatches between frontend types and backend responses
- Distinguished between full `Badge` entity (database model) and `BadgeResponse` DTO (API response)
- Fixed `BadgeGrid.astro` component to work with correct types
- All TypeScript errors in badge-related components resolved

**Phase 10 & 11 - Maintainer Dashboard + Badges (Backend)** ✅
- Enhanced database schema with badge rarity, categories, versioning, and audit logging
- BadgeService with award/revoke, duplicate prevention, and full audit trail
- BadgeEvaluator with 5 criteria types (PR count, quality, streaks, project champion, first PR)
- MaintainerDashboardService with PR management, contributor stats, and analytics
- 7 maintainer API endpoints (`/api/v1/maintainer/*`)
- 9 badge API endpoints (`/api/v1/badges/*`) with public + admin routes
- 3 Celery tasks for auto-award engine (idempotent, safe to re-run)
- 12 initial badge definitions (4 categories × 3-4 rarity levels)
- RBAC middleware for maintainer access control
- Migration applied: `20251219112432_add_badge_enhancements_and_audit`
- ~2,500 lines of production code
- Frontend implementation pending

**Phase 9 - Contributor Dashboard (Backend)** ✅
- 7 REST API endpoints for dashboard data (`/api/v1/dashboard/*`)
- DashboardService with PR filtering, sorting, pagination
- ContributionGraphService with streak calculation (30d/90d/all-time)
- SkillTagger with weighted skill computation (60% count + 40% points)
- Points history ledger view (immutable, append-only)
- Rank tracking from snapshots with change detection
- Comprehensive Pydantic schemas for type safety
- Edge case handling (zero PRs, banned users, archived projects)
- ~1,200 lines of production code
- Frontend implementation pending

**Phase 8 - Scoring & Leaderboard** ✅
- Advanced scoring engine with versioned project-specific rules
- Deterministic rank calculation with tie-breaking logic
- Multiple leaderboard types (Global, Monthly, Project, Skill-based)
- Redis caching layer with smart invalidation
- Comprehensive anti-gaming measures (spam detection, frequency throttling, repo farming)
- Admin controls (score freeze, transaction reversal, audit logging)
- Explainable score breakdowns for transparency
- ~2,000 lines of production code

**Phase 7 - Review System** ✅
- Maintainer review APIs (list/filter/sort PRs, state transitions)
- Internal comments and quality ratings (1-5 stars)
- Conflict resolution (majority-based + owner override)
- Abuse detection (frequency limits, spam, targeting, manipulation)
- Review timeout detection and auto-release
- ~1,800 lines of production code

**Phase 6 - PR Tracking Engine** ✅
- Production-grade state machine with 6 states
- Event fingerprinting for idempotency (exactly-once scoring)
- Advanced scoring engine with gaming prevention
- Append-only point ledger with atomic updates
- Background jobs for PR sync and stale detection
- ~1,200 lines of hardened production code