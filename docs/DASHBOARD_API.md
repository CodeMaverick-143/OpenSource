# Contributor Dashboard API Reference

## Base URL
All dashboard endpoints are under: `/api/v1/dashboard`

## Authentication
All endpoints require authentication via Bearer token in the `Authorization` header.

```
Authorization: Bearer <access_token>
```

---

## Endpoints

### 1. GET /dashboard/prs
Get user's pull requests with filtering, sorting, and pagination.

**Query Parameters:**
- `status` (optional): Filter by PR status (OPEN, MERGED, CLOSED, UNDER_REVIEW, etc.)
- `project_id` (optional): Filter by project ID
- `repository_id` (optional): Filter by repository ID
- `sort_by` (optional): Sort order - `recent` (default), `score`, `oldest`
- `page` (optional): Page number, default: 1
- `limit` (optional): Items per page (1-100), default: 20

**Example Request:**
```bash
GET /api/v1/dashboard/prs?status=MERGED&sort_by=score&page=1&limit=10
```

**Response:** `PRListResponse`
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Add user authentication",
      "pr_number": 123,
      "github_url": "https://github.com/owner/repo/pull/123",
      "status": "MERGED",
      "score": 150,
      "project_name": "ContriVerse",
      "project_slug": "contriverse",
      "project_is_active": true,
      "repository_name": "owner/repo",
      "repository_is_active": true,
      "opened_at": "2025-01-15T10:00:00Z",
      "merged_at": "2025-01-20T14:30:00Z",
      "closed_at": null,
      "last_activity": "2025-01-20T14:30:00Z"
    }
  ],
  "total": 38,
  "page": 1,
  "limit": 10,
  "total_pages": 4
}
```

---

### 2. GET /dashboard/points
Get user's points transaction history.

**Query Parameters:**
- `page` (optional): Page number, default: 1
- `limit` (optional): Items per page (1-100), default: 20

**Example Request:**
```bash
GET /api/v1/dashboard/points?page=1&limit=20
```

**Response:** `PointsHistoryResponse`
```json
{
  "items": [
    {
      "id": "uuid",
      "points": 150,
      "reason": "PR_MERGED",
      "transaction_type": "AWARD",
      "pr_reference": {
        "id": "pr-uuid",
        "title": "Add user authentication",
        "pr_number": 123,
        "github_url": "https://github.com/owner/repo/pull/123"
      },
      "metadata": {"quality_bonus": 50},
      "created_at": "2025-01-20T14:30:00Z"
    }
  ],
  "total": 120,
  "page": 1,
  "limit": 20,
  "total_pages": 6
}
```

---

### 3. GET /dashboard/badges
Get user's earned and available badges.

**Example Request:**
```bash
GET /api/v1/dashboard/badges
```

**Response:** `BadgesResponse`
```json
{
  "earned": [
    {
      "id": "uuid",
      "name": "First PR Merged",
      "description": "Merged your first pull request",
      "icon_url": "/badges/first-pr.svg",
      "earned_at": "2025-01-15T10:00:00Z"
    }
  ],
  "available": [
    {
      "id": "uuid",
      "name": "10 PRs Merged",
      "description": "Merge 10 pull requests",
      "icon_url": "/badges/10-prs.svg",
      "criteria": {"merged_prs": 10}
    }
  ]
}
```

---

### 4. GET /dashboard/rank
Get user's current rank and progress.

**Example Request:**
```bash
GET /api/v1/dashboard/rank
```

**Response:** `RankInfoResponse` or `null` if rank unavailable
```json
{
  "rank": 42,
  "previous_rank": 45,
  "rank_change": 3,
  "total_points": 3450,
  "percentile": 85.5,
  "next_rank_points": 3600,
  "progress_percentage": 75.0,
  "leaderboard_type": "GLOBAL",
  "last_updated": "2025-01-20T00:00:00Z"
}
```

---

### 5. GET /dashboard/contributions
Get contribution graph data with statistics.

**Query Parameters:**
- `range` (optional): Time range - `30d` (default), `90d`, `all`

**Example Request:**
```bash
GET /api/v1/dashboard/contributions?range=30d
```

**Response:** `ContributionGraphResponse`
```json
{
  "range": "30d",
  "data": [
    {"date": "2025-01-20", "count": 3},
    {"date": "2025-01-19", "count": 1},
    {"date": "2025-01-18", "count": 0}
  ],
  "stats": {
    "total_contributions": 45,
    "current_streak": 5,
    "longest_streak": 12,
    "best_day": {
      "date": "2025-01-10",
      "count": 5
    }
  }
}
```

---

### 6. GET /dashboard/skills
Get user's top skill tags.

**Example Request:**
```bash
GET /api/v1/dashboard/skills
```

**Response:** `SkillsResponse`
```json
{
  "skills": [
    {"name": "Frontend", "weight": 0.85, "contribution_count": 25},
    {"name": "Backend", "weight": 0.65, "contribution_count": 15},
    {"name": "DevOps", "weight": 0.30, "contribution_count": 5}
  ]
}
```

---

### 7. GET /dashboard/stats
Get dashboard summary statistics.

**Example Request:**
```bash
GET /api/v1/dashboard/stats
```

**Response:** `DashboardStatsResponse`
```json
{
  "total_prs": 45,
  "merged_prs": 38,
  "open_prs": 5,
  "under_review_prs": 2,
  "total_points": 3450,
  "active_projects": 3,
  "badges_earned": 5,
  "current_rank": 42
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid authentication credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Your account has been banned. Please contact support."
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "ensure this value is less than or equal to 100",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to fetch dashboard data"
}
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Pagination is 1-indexed (first page is page=1)
- Empty results return empty arrays, not null
- GitHub URLs are always valid and point to actual PRs
- Points in ledger always match user's total_points
- Rank data comes from snapshots, not live calculation
