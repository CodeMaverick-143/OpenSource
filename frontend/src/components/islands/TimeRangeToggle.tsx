import { useState } from 'react';

interface TimeRangeToggleProps {
    initialRange?: string;
}

export default function TimeRangeToggle({ initialRange = '30d' }: TimeRangeToggleProps) {
    const [range, setRange] = useState(initialRange);

    const handleRangeChange = (newRange: string) => {
        setRange(newRange);

        const url = new URL(window.location.href);
        url.searchParams.set('range', newRange);
        window.location.href = url.toString();
    };

    const ranges = [
        { value: '30d', label: '30 Days' },
        { value: '90d', label: '90 Days' },
        { value: 'all', label: 'All Time' },
    ];

    return (
        <div className="flex items-center gap-2 mb-6">
            <span className="text-sm font-medium text-gray-700">Time Range:</span>
            <div className="inline-flex rounded-lg border border-gray-300 bg-white p-1">
                {ranges.map((r) => (
                    <button
                        key={r.value}
                        onClick={() => handleRangeChange(r.value)}
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${range === r.value
                                ? 'bg-blue-600 text-white'
                                : 'text-gray-700 hover:bg-gray-100'
                            }`}
                    >
                        {r.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
