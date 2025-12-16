# 📄 PRD — Open Contribution Platform (Working Title: **ContriVerse**)

## 1. 🎯 Product Vision

A platform where:

* Projects + repos are listed
* Contributors log in with GitHub
* Raise PRs directly on GitHub
* Platform **tracks PR lifecycle**
* Contributors earn visibility, leaderboard rank, and reputation
* Maintainers review PRs transparently
* Everything auto-syncs with GitHub (no fake points)

**Core Goal:**
Turn open-source contribution into a **measurable, competitive, and visible system**.

---

## 2. 👥 User Roles

### 2.1 Visitor (Unauthenticated)

* View projects
* View leaderboards (read-only)
* View contributor profiles (public stats)
* Cannot contribute

### 2.2 Contributor (GitHub Login)

* Link GitHub account
* View assigned / self-picked projects
* Raise PRs on GitHub
* Track PR status in dashboard
* Earn points, badges, ranks

### 2.3 Maintainer

* Register project & repos
* Define contribution rules
* Review PRs
* Mark internal review status
* Moderate leaderboard abuse

### 2.4 Admin

* Platform moderation
* Ban users/projects
* Resolve disputes
* Override scores if needed

---

## 3. 🧱 Core Features

---

## 3.1 Authentication & Identity

### Auth Method

* **GitHub OAuth (mandatory)**
* No email/password system

### Stored Identity

* GitHub ID (primary key)
* Username
* Avatar
* Public repos
* Contribution history (platform-only)

### Edge Cases

* User changes GitHub username → map via GitHub ID
* User deletes GitHub account → soft-delete platform account
* Multiple GitHub accounts → NOT allowed

---

## 3.2 Project & Repo Listing

### Project

* Name
* Description
* Tags (frontend, backend, ML, DevOps, etc.)
* Difficulty level
* Maintainers
* Contribution rules

### Repository

* GitHub repo URL
* Default branch
* Allowed contribution types
* Issue labels to track

### Edge Cases

* Repo becomes private → auto-disable contributions
* Repo deleted → archive project
* Maintainer removed from GitHub repo → revoke maintainer rights

---

## 3.3 Contribution Flow (PR Lifecycle)

### Step-by-Step

1. User selects project
2. Clicks **“Contribute”**
3. Gets redirected to GitHub repo
4. Creates PR (normal GitHub flow)
5. Platform listens via **GitHub Webhooks**
6. PR auto-appears in dashboard

### PR States (Platform)

* `OPEN`
* `UNDER_REVIEW`
* `CHANGES_REQUESTED`
* `APPROVED`
* `MERGED`
* `CLOSED`

### Edge Cases

* PR closed without merge → no points
* PR reopened → status restored
* Force-push → PR remains same
* PR merged by non-maintainer → still valid
* PR squashed/rebased → detect via commit hash

---

## 3.4 Dashboard (Contributor)

### Sections

* Active PRs
* Under Review
* Merged PRs
* Rejected PRs
* Points history
* Badges

### Edge Cases

* Same PR referenced twice → dedupe via PR ID
* PR raised outside platform → still counted if repo registered
* User contributes to own repo → optional exclusion

---

## 3.5 Review System

### Maintainer Actions

* Mark PR as:

  * Needs changes
  * Approved internally
* Add internal comments (platform-only)
* Rate PR quality (1–5)

### Edge Cases

* Maintainer approves but PR not merged → no final score
* Maintainer inactive → auto-timeout review
* Conflicting maintainer reviews → admin arbitration

---

## 3.6 Leaderboard & Scoring

### Scoring Rules (Example)

* PR opened → +5
* PR merged → +20
* PR review approved → +10
* High-quality PR bonus → +5–15
* Spam / low-quality → negative score

### Leaderboards

* Global
* Monthly
* Project-wise
* Skill-tag based

### Anti-Gaming Edge Cases

* PR spam → auto-detect low diff size
* Docs typo abuse → diminishing returns
* Same repo farming → cap points per repo
* Bot accounts → rate limit + CAPTCHA

---

## 4. 🧠 System Architecture

---

## 4.1 Frontend (JS Allowed)

**Tech Stack**

* React + TypeScript
* Tailwind CSS
* React Query
* OAuth redirect handling

---

## 4.2 Backend (🚫 No JavaScript)

### Recommended Stack

**Option A (Best for speed + OSS):**

* **Python**
* FastAPI
* SQLAlchemy
* PostgreSQL
* Celery + Redis (background jobs)

---

## 4.3 Integrations

* GitHub OAuth
* GitHub Webhooks
* GitHub REST + GraphQL API

### Webhooks Used

* `pull_request`
* `push`
* `issues`
* `member`
* `repository`

---

## 5. 🗄️ Data Models (High-Level)

### User

* id
* github_id
* username
* avatar
* total_points
* rank

### Project

* id
* name
* description
* owner_id
* rules

### Repository

* id
* github_repo_id
* project_id
* is_active

### PullRequest

* id
* github_pr_id
* repo_id
* author_id
* status
* score

### Review

* id
* pr_id
* reviewer_id
* rating
* comment

---

## 6. 🔐 Security & Abuse Handling

* Webhook signature verification
* OAuth token rotation
* Rate limiting
* IP throttling
* Audit logs
* Manual admin override

---

## 7. ⚠️ Edge Cases You’ll 100% Face

* GitHub API rate limits → queue + retry
* Repo transferred to new org
* Maintainer leaves mid-review
* PR merged without webhook firing (rare but real)
* Contributors gaming leaderboard
* GitHub outage

All handled via **background sync jobs**.

---

## 8. 🚀 MVP Scope (Don’t Overbuild)

**MVP Includes**

* GitHub login
* Project + repo listing
* PR tracking
* Contributor dashboard
* Global leaderboard

---
