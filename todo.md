# Open Contribution Platform

> Goal: Build a production-ready platform that tracks GitHub PR contributions, reviews them, and ranks contributors fairly.

---

## 🏗️ PHASE 1 — System Setup

### Repo & Tooling

### Repo & Tooling

* [x] Initialize git repository
* [x] Setup `.editorconfig`
* [x] Setup `.gitignore`
* [x] Setup pre-commit hooks
* [x] Setup basic CI (lint + tests)

### Infrastructure

* [x] Setup PostgreSQL (local + prod)
* [x] Setup Redis
* [x] Setup background worker (Celery / Go worker)
* [x] Setup environment config system
* [x] Setup logging + structured logs

---

## 🔐 PHASE 2 — Authentication & Identity

### GitHub OAuth

* [ ] Register GitHub OAuth App
* [ ] Implement OAuth login flow
* [ ] Store GitHub user identity
* [ ] Handle username changes
* [ ] Handle revoked access
* [ ] Implement logout

### Edge Cases

* [ ] Duplicate GitHub accounts prevention
* [ ] Soft-delete users
* [ ] Ban / unban users

---

## 📦 PHASE 3 — Core Data Models

* [ ] Users table
* [ ] Projects table
* [ ] Project maintainers table
* [ ] Repositories table
* [ ] Pull requests table
* [ ] PR reviews table
* [ ] Point transactions table
* [ ] Badges tables
* [ ] Audit logs

---

## 🔌 PHASE 4 — GitHub Integration

### GitHub API

* [ ] Implement GitHub REST client
* [ ] Implement GitHub GraphQL client
* [ ] Handle API rate limits
* [ ] Token refresh logic

### Webhooks

* [ ] Create webhook endpoint
* [ ] Verify webhook signatures
* [ ] Handle `pull_request` events
* [ ] Handle `push` events
* [ ] Handle `repository` events
* [ ] Handle retry logic

### Edge Cases

* [ ] Webhook duplication handling
* [ ] Out-of-order webhook events
* [ ] GitHub downtime fallback
* [ ] Manual resync job

---

## 📄 PHASE 5 — Project & Repo Management

### Projects

* [ ] Create project
* [ ] Edit project
* [ ] Archive project
* [ ] Assign maintainers
* [ ] Define contribution rules

### Repositories

* [ ] Register GitHub repo
* [ ] Validate repo ownership
* [ ] Sync repo metadata
* [ ] Detect repo deletion/private switch
* [ ] Disable inactive repos

---

## 🔄 PHASE 6 — PR Tracking Engine (CORE)

* [ ] Detect new PRs via webhook
* [ ] Map PR to project/repo
* [ ] Store PR metadata
* [ ] Track PR state transitions
* [ ] Detect merge events
* [ ] Detect PR closures
* [ ] Handle re-opens
* [ ] Update PR scores
* [ ] Prevent duplicate PR entries

---

## 👀 PHASE 7 — Review System

### Maintainers

* [ ] View PRs for their projects
* [ ] Mark PR as under review
* [ ] Request changes
* [ ] Approve PR internally
* [ ] Rate PR quality

### Edge Cases

* [ ] Multiple maintainers reviewing same PR
* [ ] Conflicting reviews
* [ ] Maintainer inactivity timeout
* [ ] Reviewer abuse detection

---

## 📊 PHASE 8 — Scoring & Leaderboard

### Scoring Engine

* [ ] Define scoring rules
* [ ] Award points on PR open
* [ ] Award points on PR merge
* [ ] Bonus points for quality
* [ ] Negative points for spam

### Leaderboards

* [ ] Global leaderboard
* [ ] Monthly leaderboard
* [ ] Project-wise leaderboard
* [ ] Skill/tag-based leaderboard

### Anti-Gaming

* [ ] Diff-size based spam detection
* [ ] PR frequency throttling
* [ ] Same-repo farming detection
* [ ] Low-value PR penalty
* [ ] Admin override tools

---

## 🧑‍💻 PHASE 9 — Contributor Dashboard

* [ ] View active PRs
* [ ] View PR under review
* [ ] View merged PRs
* [ ] View rejected PRs
* [ ] View points history
* [ ] View badges
* [ ] View rank & progress

---

## 🧑‍🔧 PHASE 10 — Maintainer Dashboard

* [ ] View project PRs
* [ ] Filter PRs by status
* [ ] Review PR details
* [ ] Add internal comments
* [ ] Approve / reject PRs
* [ ] View contributor stats

---

## 🔔 PHASE 11 — Notifications

* [ ] In-app notification system
* [ ] PR status updates
* [ ] Review comments
* [ ] Merge confirmations
* [ ] Rank changes
* [ ] Badge unlocks

---

## 🛡️ PHASE 12 — Security & Abuse Protection

* [ ] Rate limiting
* [ ] Webhook signature validation
* [ ] IP throttling
* [ ] Audit logging
* [ ] Admin moderation panel
* [ ] Dispute resolution workflow

---

## 🚀 PHASE 13 — Deployment & Ops

* [ ] Production database setup
* [ ] Background workers deployment
* [ ] Webhook endpoint exposure
* [ ] Health checks
* [ ] Monitoring & alerts
* [ ] Backup & restore strategy

---

## 🧪 PHASE 14 — Testing

* [ ] Unit tests (core logic)
* [ ] Integration tests (GitHub events)
* [ ] Webhook replay tests
* [ ] Abuse scenario tests
* [ ] Load testing leaderboard queries

---

## 📢 PHASE 15 — Launch & Growth

* [ ] Seed with demo projects
* [ ] Invite maintainers
* [ ] Write contributor guide
* [ ] Publish docs
* [ ] Announce on GitHub / Twitter / Reddit
* [ ] Collect feedback
* [ ] Iterate fast

---