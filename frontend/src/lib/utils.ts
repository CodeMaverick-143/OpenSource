/**
 * Utility functions for formatting and data manipulation.
 */

import type { PRStatus, TransactionType } from './types';

/**
 * Format ISO date string to readable format.
 */
export function formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    // Relative time for recent dates
    if (diffDays === 0) {
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        if (diffHours === 0) {
            const diffMinutes = Math.floor(diffMs / (1000 * 60));
            return diffMinutes <= 1 ? 'Just now' : `${diffMinutes} minutes ago`;
        }
        return diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`;
    }
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;

    // Absolute date for older dates
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

/**
 * Format points with +/- prefix and color class.
 */
export function formatPoints(points: number): { text: string; colorClass: string } {
    const prefix = points > 0 ? '+' : '';
    const colorClass = points > 0 ? 'text-green-600' : points < 0 ? 'text-red-600' : 'text-gray-600';
    return {
        text: `${prefix}${points}`,
        colorClass,
    };
}

/**
 * Calculate rank delta and return symbol with color.
 */
export function getRankDelta(currentRank: number, previousRank: number | null): {
    symbol: string;
    colorClass: string;
    text: string;
} {
    if (previousRank === null) {
        return { symbol: '→', colorClass: 'text-gray-500', text: 'New' };
    }

    const delta = previousRank - currentRank; // Lower rank number is better
    if (delta > 0) {
        return { symbol: '↑', colorClass: 'text-green-600', text: `+${delta}` };
    } else if (delta < 0) {
        return { symbol: '↓', colorClass: 'text-red-600', text: `${delta}` };
    } else {
        return { symbol: '→', colorClass: 'text-gray-500', text: 'No change' };
    }
}

/**
 * Map PR status to Tailwind color classes.
 */
export function getStatusColor(status: string): string {
    const statusMap: Record<string, string> = {
        OPEN: 'bg-blue-100 text-blue-800',
        UNDER_REVIEW: 'bg-yellow-100 text-yellow-800',
        CHANGES_REQUESTED: 'bg-orange-100 text-orange-800',
        APPROVED: 'bg-green-100 text-green-800',
        MERGED: 'bg-purple-100 text-purple-800',
        CLOSED: 'bg-gray-100 text-gray-800',
    };
    return statusMap[status] || 'bg-gray-100 text-gray-800';
}

/**
 * Map transaction type to color classes.
 */
export function getTransactionTypeColor(type: TransactionType): string {
    const typeMap: Record<TransactionType, string> = {
        AWARD: 'bg-green-100 text-green-800',
        BONUS: 'bg-blue-100 text-blue-800',
        PENALTY: 'bg-red-100 text-red-800',
        REVERSAL: 'bg-orange-100 text-orange-800',
    };
    return typeMap[type] || 'bg-gray-100 text-gray-800';
}

/**
 * Format status string to readable text.
 */
export function formatStatus(status: string): string {
    return status
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

/**
 * Truncate text to specified length with ellipsis.
 */
export function truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength - 3) + '...';
}

/**
 * Class name merger utility (simple version).
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
    return classes.filter(Boolean).join(' ');
}

/**
 * Calculate contribution intensity color based on count.
 */
export function getContributionColor(count: number): string {
    if (count === 0) return 'bg-gray-100';
    if (count === 1) return 'bg-green-200';
    if (count <= 3) return 'bg-green-400';
    if (count <= 5) return 'bg-green-600';
    return 'bg-green-800';
}

/**
 * Format number with commas.
 */
export function formatNumber(num: number): string {
    return num.toLocaleString('en-US');
}

/**
 * Calculate percentage.
 */
export function calculatePercentage(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100);
}
