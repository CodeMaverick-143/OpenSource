/**
 * Utility functions for badge rarity styling and display.
 */

import type { BadgeRarity, BadgeCategory } from './types';

/**
 * Get Tailwind CSS classes for badge rarity.
 */
export function getBadgeRarityStyles(rarity: BadgeRarity) {
    const styles = {
        COMMON: {
            border: 'border-gray-400',
            bg: 'bg-gray-50',
            text: 'text-gray-700',
            glow: 'shadow-md shadow-gray-200',
            ring: 'ring-gray-300',
            icon: 'text-gray-500',
        },
        RARE: {
            border: 'border-blue-500',
            bg: 'bg-blue-50',
            text: 'text-blue-700',
            glow: 'shadow-lg shadow-blue-300',
            ring: 'ring-blue-400',
            icon: 'text-blue-600',
        },
        EPIC: {
            border: 'border-purple-500',
            bg: 'bg-purple-50',
            text: 'text-purple-700',
            glow: 'shadow-xl shadow-purple-300',
            ring: 'ring-purple-400',
            icon: 'text-purple-600',
        },
        LEGENDARY: {
            border: 'border-amber-500',
            bg: 'bg-gradient-to-br from-amber-50 to-yellow-50',
            text: 'text-amber-700',
            glow: 'shadow-2xl shadow-amber-400',
            ring: 'ring-amber-500',
            icon: 'text-amber-600',
        },
    };

    return styles[rarity];
}

/**
 * Get display name for badge category.
 */
export function getBadgeCategoryName(category: BadgeCategory): string {
    const names: Record<BadgeCategory, string> = {
        MILESTONE: 'Milestone',
        QUALITY: 'Quality',
        STREAK: 'Streak',
        SPECIAL: 'Special',
    };

    return names[category];
}

/**
 * Get icon for badge category.
 */
export function getBadgeCategoryIcon(category: BadgeCategory): string {
    const icons: Record<BadgeCategory, string> = {
        MILESTONE: '🎯',
        QUALITY: '⭐',
        STREAK: '🔥',
        SPECIAL: '🏆',
    };

    return icons[category];
}

/**
 * Format badge rarity for display.
 */
export function formatBadgeRarity(rarity: BadgeRarity): string {
    return rarity.charAt(0) + rarity.slice(1).toLowerCase();
}

/**
 * Get rarity order for sorting (higher is rarer).
 */
export function getRarityOrder(rarity: BadgeRarity): number {
    const order: Record<BadgeRarity, number> = {
        COMMON: 1,
        RARE: 2,
        EPIC: 3,
        LEGENDARY: 4,
    };

    return order[rarity];
}

/**
 * Sort badges by rarity (rarest first).
 */
export function sortBadgesByRarity<T extends { rarity: BadgeRarity }>(badges: T[]): T[] {
    return [...badges].sort((a, b) => getRarityOrder(b.rarity) - getRarityOrder(a.rarity));
}

/**
 * Get badge icon or default emoji.
 */
export function getBadgeIcon(badge: { icon_url: string | null; name: string }): string {
    if (badge.icon_url) {
        return badge.icon_url;
    }

    // Default emojis based on badge name patterns
    const name = badge.name.toLowerCase();

    if (name.includes('first')) return '🎯';
    if (name.includes('streak')) return '🔥';
    if (name.includes('quality')) return '⭐';
    if (name.includes('champion')) return '🏆';
    if (name.includes('10')) return '🥉';
    if (name.includes('50')) return '🥈';
    if (name.includes('100')) return '🥇';
    if (name.includes('500')) return '💎';

    return '🏅';
}

/**
 * Format badge criteria for human-readable display.
 */
export function formatBadgeCriteria(criteria: Record<string, any> | null): string {
    if (!criteria || Object.keys(criteria).length === 0) {
        return 'No criteria specified';
    }

    const parts: string[] = [];

    if (criteria.min_prs) {
        parts.push(`${criteria.min_prs} PRs merged`);
    }

    if (criteria.min_rating) {
        parts.push(`${criteria.min_rating}+ average rating`);
    }

    if (criteria.min_months) {
        parts.push(`${criteria.min_months} months active`);
    }

    if (criteria.project_id) {
        parts.push('in specific project');
    }

    if (criteria.min_project_prs) {
        parts.push(`${criteria.min_project_prs} PRs in one project`);
    }

    return parts.join(', ') || 'Custom criteria';
}

/**
 * Format earned date to relative time.
 */
export function formatEarnedDate(earnedAt: string): string {
    const date = new Date(earnedAt);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
}
