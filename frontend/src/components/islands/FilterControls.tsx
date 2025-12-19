import { useState } from 'react';

interface FilterControlsProps {
    initialStatus?: string;
    initialProjectId?: string;
    initialRepositoryId?: string;
    initialSortBy?: string;
}

export default function FilterControls({
    initialStatus = '',
    initialProjectId = '',
    initialRepositoryId = '',
    initialSortBy = 'recent',
}: FilterControlsProps) {
    const [status, setStatus] = useState(initialStatus);
    const [sortBy, setSortBy] = useState(initialSortBy);

    const handleFilterChange = (key: string, value: string) => {
        const url = new URL(window.location.href);

        if (value) {
            url.searchParams.set(key, value);
        } else {
            url.searchParams.delete(key);
        }

        // Reset to page 1 when filters change
        url.searchParams.set('page', '1');

        window.location.href = url.toString();
    };

    return (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Status Filter */}
                <div>
                    <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
                        Status
                    </label>
                    <select
                        id="status"
                        value={status}
                        onChange={(e) => {
                            setStatus(e.target.value);
                            handleFilterChange('status', e.target.value);
                        }}
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                    >
                        <option value="">All Statuses</option>
                        <option value="OPEN">Open</option>
                        <option value="UNDER_REVIEW">Under Review</option>
                        <option value="CHANGES_REQUESTED">Changes Requested</option>
                        <option value="APPROVED">Approved</option>
                        <option value="MERGED">Merged</option>
                        <option value="CLOSED">Closed</option>
                    </select>
                </div>

                {/* Sort By */}
                <div>
                    <label htmlFor="sortBy" className="block text-sm font-medium text-gray-700 mb-1">
                        Sort By
                    </label>
                    <select
                        id="sortBy"
                        value={sortBy}
                        onChange={(e) => {
                            setSortBy(e.target.value);
                            handleFilterChange('sort_by', e.target.value);
                        }}
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                    >
                        <option value="recent">Most Recent</option>
                        <option value="score">Highest Score</option>
                        <option value="oldest">Oldest Pending</option>
                    </select>
                </div>

                {/* Reset Filters */}
                <div className="flex items-end">
                    <button
                        onClick={() => {
                            const url = new URL(window.location.href);
                            url.search = '';
                            window.location.href = url.toString();
                        }}
                        className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                    >
                        Reset Filters
                    </button>
                </div>
            </div>
        </div>
    );
}
