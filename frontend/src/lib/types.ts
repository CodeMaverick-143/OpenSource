/**
 * TypeScript types matching backend Pydantic schemas.
 * These types ensure type safety when consuming dashboard APIs.
 */

// ============================================================================
// PR Management Types
// ============================================================================

export interface PRItem {
    id: string;
    title: string;
    pr_number: number;
    github_url: string;
    status: string;
    score: number;
    project_name: string | null;
    project_slug: string | null;
    project_is_active: boolean | null;
    repository_name: string | null;
    repository_is_active: boolean | null;
    opened_at: string;
    merged_at: string | null;
    closed_at: string | null;
    last_activity: string;
}

export interface PRListResponse {
    items: PRItem[];
    total: number;
    page: number;
    limit: number;
    total_pages: number;
}

// ============================================================================
// Points History Types
// ============================================================================

export interface PRReference {
    id: string;
    title: string;
    pr_number: number;
    github_url: string;
}

export interface PointTransaction {
    id: string;
    points: number;
    reason: string;
    transaction_type: string;
    pr_reference: PRReference | null;
    metadata: Record<string, any> | null;
    created_at: string;
}

export interface PointsHistoryResponse {
    items: PointTransaction[];
    total: number;
    page: number;
    limit: number;
    total_pages: number;
}

// ============================================================================
// Badges Types
// ============================================================================

export type BadgeRarity = 'COMMON' | 'RARE' | 'EPIC' | 'LEGENDARY';
export type BadgeCategory = 'MILESTONE' | 'QUALITY' | 'STREAK' | 'SPECIAL';

export interface BadgeCriteria {
    type: string;
    threshold: number;
    description: string;
    period_days?: number;
    min_rating?: number;
    repos?: string[];
}

export interface Badge {
    id: string;
    name: string;
    description: string;
    iconUrl: string | null;
    rarity: BadgeRarity;
    category: BadgeCategory;
    criteria: Record<string, any>;
    version: number;
    isActive: boolean;
    createdAt: string;
    updatedAt: string;
}

export interface UserBadge {
    id: string;
    badge: Badge;
    earnedAt: string;
    awardedBy: string | null;
    isManual: boolean;
    metadata: Record<string, any> | null;
}

export interface BadgeProgress {
    earned: boolean;
    progress: {
        current: number;
        required: number;
        percentage: number;
        current_prs?: number;
        required_prs?: number;
        current_rating?: number;
        required_rating?: number;
        current_months?: number;
        required_months?: number;
    } | null;
}

/**
 * Badge response from dashboard API.
 * This matches the BadgeResponse schema from the backend.
 */
export interface BadgeResponse {
    id: string;
    name: string;
    description: string;
    icon_url: string | null;
    earned_at?: string | null;  // Only for earned badges
    criteria?: Record<string, any> | null;  // Only for available badges
}

export interface BadgesResponse {
    earned: BadgeResponse[];
    available: BadgeResponse[];
}

export interface BadgeDistribution {
    total_badges: number;
    badges_by_rarity: Record<BadgeRarity, number>;
    total_awards: number;
    manual_awards: number;
    auto_awards: number;
    most_awarded: Array<{ badge_name: string; count: number }>;
}

// ============================================================================
// Maintainer Dashboard Types
// ============================================================================

export interface User {
    id: string;
    githubUsername: string;
    avatarUrl: string | null;
    profileUrl: string | null;
}

export interface Repository {
    id: string;
    name: string;
    fullName: string;
    isActive: boolean;
}

export interface ProjectMaintainer {
    id: string;
    userId: string;
    role: string;
    user?: User;
}

export interface MaintainerProject {
    id: string;
    name: string;
    slug: string;
    description: string | null;
    tags: string[];
    difficulty: string;
    isActive: boolean;
    repositories: Repository[];
    maintainers: ProjectMaintainer[];
}

export interface ProjectPR {
    id: string;
    title: string;
    status: PRStatus;
    prNumber: number;
    githubUrl: string;
    diffSize: number | null;
    score: number;
    author: User;
    repository: Repository;
    reviews?: PRReview[];
    reviewComments?: ReviewComment[];
    openedAt: string;
    reviewedAt: string | null;
    approvedAt: string | null;
    mergedAt: string | null;
    closedAt: string | null;
}

export interface PRReview {
    id: string;
    action: string;
    status: string;
    rating: number | null;
    comment: string | null;
    reviewer: User;
    createdAt: string;
}

export interface ReviewComment {
    id: string;
    comment: string;
    isInternal: boolean;
    reviewer: User;
    createdAt: string;
}

export interface PRListResponse {
    prs: ProjectPR[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface Contributor {
    user_id: string;
    username: string;
    avatar_url: string | null;
    total_prs: number;
    merged_prs: number;
}

export interface ContributorStats {
    user_id: string;
    project_id: string;
    total_prs: number;
    merged_prs: number;
    open_prs: number;
    avg_rating: number | null;
    avg_review_time_hours: number | null;
    total_points: number;
}

export interface ProjectAnalytics {
    contribution_volume: Array<{ week: string; count: number }>;
    top_contributors: Array<{ user_id: string; username: string; count: number }>;
    pr_merge_rate: number;
    avg_review_time_hours: number | null;
    quality_trends: Record<number, number>;
    total_prs: number;
    merged_prs: number;
}

export interface MaintainerFilters {
    status?: PRStatus;
    author_id?: string;
    sort_by?: 'newest' | 'oldest' | 'review_age';
    page?: number;
    page_size?: number;
}

// ============================================================================
// Rank Types
// ============================================================================

export interface RankInfo {
    rank: number;
    previous_rank: number | null;
    rank_change: number;
    total_points: number;
    percentile: number;
    next_rank_points: number;
    progress_percentage: number;
    leaderboard_type: string;
    last_updated: string;
}

// ============================================================================
// Contribution Graph Types
// ============================================================================

export interface ContributionDay {
    date: string;
    count: number;
}

export interface ContributionStats {
    total_contributions: number;
    current_streak: number;
    longest_streak: number;
    best_day: Record<string, any> | null;
}

export interface ContributionGraphResponse {
    range: string;
    data: ContributionDay[];
    stats: ContributionStats;
}

// ============================================================================
// Skills Types
// ============================================================================

export interface SkillTag {
    name: string;
    weight: number;
    contribution_count: number;
}

export interface SkillsResponse {
    skills: SkillTag[];
}

// ============================================================================
// Dashboard Stats Types
// ============================================================================

export interface DashboardStats {
    total_prs: number;
    merged_prs: number;
    open_prs: number;
    under_review_prs: number;
    total_points: number;
    active_projects: number;
    badges_earned: number;
    current_rank: number | null;
}

// ============================================================================
// API Error Types
// ============================================================================

export interface APIError {
    detail: string;
    status?: number;
}

// ============================================================================
// Filter & Query Types
// ============================================================================

export interface PRFilters {
    status?: string;
    project_id?: string;
    repository_id?: string;
    sort_by?: 'recent' | 'score' | 'oldest';
    page?: number;
    limit?: number;
}

export type TimeRange = '30d' | '90d' | 'all';

export type PRStatus = 'OPEN' | 'UNDER_REVIEW' | 'CHANGES_REQUESTED' | 'APPROVED' | 'MERGED' | 'CLOSED';

export type TransactionType = 'AWARD' | 'BONUS' | 'PENALTY' | 'REVERSAL';
