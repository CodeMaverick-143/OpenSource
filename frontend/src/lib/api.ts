/**
 * API client for consuming backend dashboard endpoints.
 * All methods are type-safe and handle errors gracefully.
 */

import type {
    PRListResponse as DashboardPRListResponse,
    PointsHistoryResponse,
    BadgesResponse,
    RankInfo,
    ContributionGraphResponse,
    SkillsResponse,
    DashboardStats,
    PRFilters,
    TimeRange,
    APIError,
    MaintainerProject,
    PRListResponse,
    ProjectPR,
    Contributor,
    ContributorStats,
    ProjectAnalytics,
    MaintainerFilters,
    Badge,
    UserBadge,
    BadgeProgress,
    BadgeDistribution,
} from './types';

const API_BASE_URL = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * Base fetch wrapper with error handling and cookie support.
 */
async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    try {
        const response = await fetch(url, {
            ...options,
            credentials: 'include', // Send cookies (JWT tokens)
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            // Handle HTTP errors
            if (response.status === 401) {
                // Unauthorized - redirect to login
                if (typeof window !== 'undefined') {
                    window.location.href = '/auth/login';
                }
                throw new Error('Unauthorized');
            }

            let errorMessage = 'An error occurred';
            try {
                const errorData: APIError = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch {
                // If JSON parsing fails, use status text
                errorMessage = response.statusText || errorMessage;
            }

            throw new Error(errorMessage);
        }

        // Handle null responses (e.g., rank not assigned)
        if (response.status === 204 || response.headers.get('content-length') === '0') {
            return null as T;
        }

        return await response.json();
    } catch (error) {
        if (error instanceof Error) {
            throw error;
        }
        throw new Error('Network error occurred');
    }
}

/**
 * Build query string from object.
 */
function buildQueryString(params: Record<string, any>): string {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
            searchParams.append(key, String(value));
        }
    });
    const query = searchParams.toString();
    return query ? `?${query}` : '';
}

// ============================================================================
// API Methods
// ============================================================================

/**
 * Get user's PRs with filtering, sorting, and pagination.
 */
export async function getPRs(filters: PRFilters = {}): Promise<DashboardPRListResponse> {
    const query = buildQueryString(filters);
    return fetchAPI<DashboardPRListResponse>(`/dashboard/prs${query}`);
}

/**
 * Get user's points transaction history.
 */
export async function getPointsHistory(page: number = 1, limit: number = 20): Promise<PointsHistoryResponse> {
    const query = buildQueryString({ page, limit });
    return fetchAPI<PointsHistoryResponse>(`/dashboard/points${query}`);
}

/**
 * Get user's earned and available badges.
 */
export async function getBadges(): Promise<BadgesResponse> {
    return fetchAPI<BadgesResponse>('/dashboard/badges');
}

/**
 * Get user's rank information.
 * Returns null if rank not yet assigned.
 */
export async function getRank(): Promise<RankInfo | null> {
    return fetchAPI<RankInfo | null>('/dashboard/rank');
}

/**
 * Get user's contribution graph data.
 */
export async function getContributionGraph(range: TimeRange = '30d'): Promise<ContributionGraphResponse> {
    const query = buildQueryString({ range });
    return fetchAPI<ContributionGraphResponse>(`/dashboard/contributions${query}`);
}

/**
 * Get user's top skill tags.
 */
export async function getSkills(): Promise<SkillsResponse> {
    return fetchAPI<SkillsResponse>('/dashboard/skills');
}

/**
 * Get dashboard summary statistics.
 */
export async function getDashboardStats(): Promise<DashboardStats> {
    return fetchAPI<DashboardStats>('/dashboard/stats');
}

// ============================================================================
// Maintainer Dashboard API Methods
// ============================================================================

/**
 * Get projects where user is maintainer or owner.
 */
export async function getMaintainerProjects(): Promise<{ projects: MaintainerProject[] }> {
    return fetchAPI<{ projects: MaintainerProject[] }>('/maintainer/projects');
}

/**
 * Get PRs for a project with filtering and sorting.
 */
export async function getProjectPRs(projectId: string, filters: MaintainerFilters = {}): Promise<PRListResponse> {
    const query = buildQueryString(filters);
    return fetchAPI<PRListResponse>(`/maintainer/projects/${projectId}/prs${query}`);
}

/**
 * Get detailed PR information.
 */
export async function getPRDetails(prId: string): Promise<{ pr: ProjectPR }> {
    return fetchAPI<{ pr: ProjectPR }>(`/maintainer/prs/${prId}`);
}

/**
 * Add internal comment to PR.
 */
export async function addInternalComment(prId: string, comment: string): Promise<{ message: string }> {
    return fetchAPI<{ message: string }>(`/maintainer/prs/${prId}/comments`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
    });
}

/**
 * Get all contributors for a project.
 */
export async function getProjectContributors(projectId: string): Promise<{ contributors: Contributor[] }> {
    return fetchAPI<{ contributors: Contributor[] }>(`/maintainer/projects/${projectId}/contributors`);
}

/**
 * Get detailed stats for a contributor in a project.
 */
export async function getContributorStats(projectId: string, contributorId: string): Promise<{ stats: ContributorStats }> {
    return fetchAPI<{ stats: ContributorStats }>(`/maintainer/projects/${projectId}/contributors/${contributorId}/stats`);
}

/**
 * Get project analytics for specified time range.
 */
export async function getProjectAnalytics(projectId: string, days: number = 30): Promise<{ analytics: ProjectAnalytics }> {
    const query = buildQueryString({ days });
    return fetchAPI<{ analytics: ProjectAnalytics }>(`/maintainer/projects/${projectId}/analytics${query}`);
}

// ============================================================================
// Badges API Methods
// ============================================================================

/**
 * Get all badges with optional filtering.
 */
export async function getAllBadges(filters?: { category?: string; rarity?: string }): Promise<{ badges: Badge[] }> {
    const query = filters ? buildQueryString(filters) : '';
    return fetchAPI<{ badges: Badge[] }>(`/badges${query}`);
}

/**
 * Get badge details including award count.
 */
export async function getBadge(badgeId: string): Promise<{ badge: Badge; award_count: number }> {
    return fetchAPI<{ badge: Badge; award_count: number }>(`/badges/${badgeId}`);
}

/**
 * Get badges earned by a specific user.
 */
export async function getUserBadges(userId: string): Promise<{ badges: UserBadge[] }> {
    return fetchAPI<{ badges: UserBadge[] }>(`/badges/users/${userId}`);
}

/**
 * Get user's progress towards a badge.
 */
export async function getBadgeProgress(badgeId: string): Promise<BadgeProgress> {
    return fetchAPI<BadgeProgress>(`/badges/${badgeId}/progress`);
}

/**
 * Get badge distribution statistics (admin only).
 */
export async function getBadgeDistribution(): Promise<{ distribution: BadgeDistribution }> {
    return fetchAPI<{ distribution: BadgeDistribution }>('/badges/admin/distribution');
}

