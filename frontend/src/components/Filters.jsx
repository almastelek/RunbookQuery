export function Filters({ filters, onFilterChange }) {
    const sourceTypes = ['all', 'docs', 'issues'];

    const handleSourceTypeClick = (type) => {
        onFilterChange({
            ...filters,
            sourceTypes: type === 'all' ? null : [type],
        });
    };

    const currentType = filters.sourceTypes?.[0] || 'all';

    return (
        <div className="filters">
            <div className="filter-group">
                {sourceTypes.map((type) => (
                    <button
                        key={type}
                        className={`filter-button ${currentType === type ? 'active' : ''}`}
                        onClick={() => handleSourceTypeClick(type)}
                    >
                        {type === 'all' ? 'All' : type === 'docs' ? 'Docs' : 'Issues'}
                    </button>
                ))}
            </div>
        </div>
    );
}
