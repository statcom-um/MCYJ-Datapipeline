import React, { useState, useMemo } from 'react';
import { KeywordBadge, KeywordBadgeList } from './KeywordBadge.jsx';
import { AutocompleteInput } from './AutocompleteInput.jsx';
import { getBaseUrl, ALL_SEVERITY_LEVELS } from '../utils/helpers.js';

/**
 * Collapsible section within the filter panel
 */
function FilterSection({ id, icon, label, openSections, onToggle, children }) {
    const isOpen = openSections.includes(id);
    return (
        <div className="filter-section">
            <button
                type="button"
                className="filter-section-toggle"
                onClick={() => onToggle(id)}
                aria-expanded={isOpen}
                aria-controls={`filter-section-${id}`}
            >
                <span className="filter-section-label">
                    <span>{icon}</span>
                    <span>{label}</span>
                </span>
                <span className={`filter-section-arrow ${isOpen ? 'open' : ''}`} aria-hidden="true">▶</span>
            </button>
            {isOpen && (
                <div className="filter-section-body" id={`filter-section-${id}`}>
                    {children}
                </div>
            )}
        </div>
    );
}

const STAFFING_LABELS = {
    yes_high: 'Staffing: Yes — High',
    yes_medium: 'Staffing: Yes — Medium',
    yes_low: 'Staffing: Yes — Low',
    no_low: 'Staffing: No — Low',
    no_medium: 'Staffing: No — Medium',
    no_high: 'Staffing: No — High'
};

const TIME_LABELS = {
    '1': '1 month',
    '3': '3 months',
    '6': '6 months',
    '12': '1 year',
    '24': '2 years',
    '36': '3 years'
};

const SEVERITY_COLORS = { low: '#f39c12', moderate: '#e67e22', severe: '#e74c3c', none: '#95a5a6' };
const SEVERITY_LABELS = { low: 'Low', moderate: 'Moderate', severe: 'Severe', none: 'None identified' };

/**
 * FilterPanel component for filtering agencies and documents
 * Designed for advocates at the Michigan Youth Justice Center
 * who need to quickly identify patterns and problems across facilities.
 *
 * @param {Object} props
 * @param {Object} props.filters - Current filter state
 * @param {Function} props.onFilterChange - Callback when filters change
 * @param {Function} props.onKeywordSearch - Function to search keywords
 * @param {Function} props.onKeywordSelect - Callback when keyword is selected
 * @param {Function} props.onKeywordRemove - Callback when keyword is removed
 * @param {Function} props.onClearAllKeywords - Callback to clear all keywords
 * @param {Function} props.onAgencySearch - Function to search agencies
 * @param {Function} props.onAgencySelect - Callback when agency is selected
 * @param {Function} props.onAgencyRemove - Callback when agency is removed
 * @param {Array} props.uniqueLicenseStatuses - Available license status options
 * @param {Array} props.uniqueAgencyTypes - Available agency type options
 * @param {Array} props.uniqueCounties - Available county options
 * @param {string} [props.selectedAgencyText] - Display text for selected agency
 * @param {number} props.totalAgencies - Total agencies count
 * @param {number} props.totalReports - Total reports count
 */
export function FilterPanel({
    filters,
    onFilterChange,
    onKeywordSearch,
    onKeywordSelect,
    onKeywordRemove,
    onClearAllKeywords,
    onAgencySearch,
    onAgencySelect,
    onAgencyRemove,
    uniqueLicenseStatuses = [],
    uniqueAgencyTypes = [],
    uniqueCounties = [],
    selectedAgencyText,
    totalAgencies,
    totalReports
}) {
    const baseUrl = getBaseUrl();
    const [panelOpen, setPanelOpen] = useState(true);
    const [openSections, setOpenSections] = useState(['agency', 'report-type']);

    const toggleSection = (id) => {
        setOpenSections(prev =>
            prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
        );
    };

    // Compute active filter descriptions for the summary strip
    const activeFilters = useMemo(() => {
        const items = [];
        if (filters.agency) {
            items.push({ key: 'agency', label: selectedAgencyText || filters.agency, onRemove: () => onAgencyRemove() });
        }
        if (filters.sirOnly) {
            items.push({ key: 'sirOnly', label: 'Investigations only', onRemove: () => onFilterChange('sirOnly', false) });
        }
        if (filters.activeLicenseOnly) {
            items.push({ key: 'activeLicenseOnly', label: 'Active licenses', onRemove: () => onFilterChange('activeLicenseOnly', false) });
        }
        if (filters.lastNMonths) {
            items.push({ key: 'lastNMonths', label: `Last ${TIME_LABELS[String(filters.lastNMonths)] || filters.lastNMonths + ' months'}`, onRemove: () => onFilterChange('lastNMonths', null) });
        }
        if (filters.licenseStatus) {
            items.push({ key: 'licenseStatus', label: filters.licenseStatus, onRemove: () => onFilterChange('licenseStatus', null) });
        }
        if (filters.agencyType) {
            items.push({ key: 'agencyType', label: filters.agencyType, onRemove: () => onFilterChange('agencyType', null) });
        }
        if (filters.county) {
            items.push({ key: 'county', label: filters.county, onRemove: () => onFilterChange('county', null) });
        }
        if (filters.severityLevels && filters.severityLevels.length > 0 && filters.severityLevels.length < ALL_SEVERITY_LEVELS.length) {
            const excluded = ALL_SEVERITY_LEVELS.filter(l => !filters.severityLevels.includes(l));
            const label = excluded.length === 1
                ? `Excluding ${excluded[0]} severity`
                : `Excluding ${excluded.join(', ')} severity`;
            items.push({ key: 'severity', label, onRemove: () => onFilterChange('severityLevels', [...ALL_SEVERITY_LEVELS]) });
        }
        if (filters.staffingConfidence) {
            items.push({ key: 'staffing', label: STAFFING_LABELS[filters.staffingConfidence] || filters.staffingConfidence, onRemove: () => onFilterChange('staffingConfidence', null) });
        }
        filters.keywords.forEach(kw => {
            items.push({ key: `kw-${kw}`, label: `🏷️ ${kw}`, onRemove: () => onKeywordRemove(kw) });
        });
        return items;
    }, [filters, selectedAgencyText]);

    const activeCount = activeFilters.length;

    const handleResetAll = () => {
        onFilterChange('sirOnly', false);
        onFilterChange('activeLicenseOnly', false);
        onFilterChange('lastNMonths', null);
        onFilterChange('licenseStatus', null);
        onFilterChange('agencyType', null);
        onFilterChange('county', null);
        onFilterChange('severityLevels', [...ALL_SEVERITY_LEVELS]);
        onFilterChange('staffingConfidence', null);
        if (filters.agency) onAgencyRemove();
        if (filters.keywords.length > 0) onClearAllKeywords();
    };

    return (
        <>
            {/* Mobile toggle */}
            <button
                type="button"
                className="filter-toggle-btn"
                onClick={() => setPanelOpen(prev => !prev)}
                aria-expanded={panelOpen}
                aria-controls="filter-panel"
            >
                <span>
                    🔍 Filters
                    {activeCount > 0 && <span className="filter-badge-count">{activeCount}</span>}
                </span>
                <span className={`filter-toggle-icon ${panelOpen ? 'open' : ''}`} aria-hidden="true">▾</span>
            </button>

            <div id="filter-panel" className={`filter-panel ${panelOpen ? '' : 'collapsed'}`}>
                <div className="filter-panel-inner">
                    {/* Header with title and reset */}
                    <div className="filter-panel-header">
                        <h3 className="filter-panel-title">Narrow Your Search</h3>
                        {activeCount > 0 && (
                            <button type="button" className="filter-reset-btn" onClick={handleResetAll}>
                                ✕ Reset All
                            </button>
                        )}
                    </div>

                    {/* Active filters summary strip */}
                    {activeCount > 0 && (
                        <div className="active-filters-strip" role="status" aria-live="polite">
                            <span className="active-filters-label">Active filters:</span>
                            {activeFilters.map(f => (
                                <span key={f.key} className="active-filter-chip">
                                    <span>{f.label}</span>
                                    <button
                                        type="button"
                                        className="active-filter-chip-remove"
                                        onClick={f.onRemove}
                                        aria-label={`Remove filter: ${f.label}`}
                                        title={`Remove: ${f.label}`}
                                    >✕</button>
                                </span>
                            ))}
                        </div>
                    )}

                    {/* === SECTION: Agency === */}
                    <FilterSection
                        id="agency"
                        icon="🏢"
                        label="Agency"
                        openSections={openSections}
                        onToggle={toggleSection}
                    >
                        {!filters.agency ? (
                            <AutocompleteInput
                                id="agencyFilterInput"
                                placeholder="Search by agency name…"
                                onSearch={onAgencySearch}
                                onSelect={onAgencySelect}
                                renderSuggestion={(s) => (
                                    <span>{s.keyword}</span>
                                )}
                            />
                        ) : null}
                        <div style={{ marginTop: '8px', minHeight: '28px' }}>
                            {filters.agency ? (
                                <KeywordBadge
                                    keyword={selectedAgencyText || filters.agency}
                                    onRemove={onAgencyRemove}
                                />
                            ) : (
                                <span className="filter-keywords-empty">All agencies shown</span>
                            )}
                        </div>
                    </FilterSection>

                    {/* === SECTION: Report Type === */}
                    <FilterSection
                        id="report-type"
                        icon="📋"
                        label="Report Type"
                        openSections={openSections}
                        onToggle={toggleSection}
                    >
                        <label className="filter-checkbox-label">
                            <input
                                type="checkbox"
                                checked={filters.sirOnly}
                                onChange={(e) => onFilterChange('sirOnly', e.target.checked)}
                            />
                            <span className="filter-checkbox-text">
                                <span className="filter-checkbox-title">Special Investigation Reports only</span>
                                <span className="filter-checkbox-desc">Focus on reports where allegations were investigated</span>
                            </span>
                        </label>
                        <label className="filter-checkbox-label">
                            <input
                                type="checkbox"
                                checked={filters.activeLicenseOnly}
                                onChange={(e) => onFilterChange('activeLicenseOnly', e.target.checked)}
                            />
                            <span className="filter-checkbox-text">
                                <span className="filter-checkbox-title">Active licenses only</span>
                                <span className="filter-checkbox-desc">Show only agencies currently licensed (Regular, Original, Provisional, or Inspected)</span>
                            </span>
                        </label>
                    </FilterSection>

                    {/* === SECTION: Time Period === */}
                    <FilterSection
                        id="time-period"
                        icon="📅"
                        label="Time Period"
                        openSections={openSections}
                        onToggle={toggleSection}
                    >
                        <label className="filter-field-label" htmlFor="filterLastNMonths">
                            Show reports from the last:
                        </label>
                        <select
                            id="filterLastNMonths"
                            className="filter-select"
                            value={filters.lastNMonths || ''}
                            onChange={(e) => onFilterChange('lastNMonths', e.target.value ? parseInt(e.target.value, 10) : null)}
                        >
                            <option value="">All time</option>
                            <option value="1">1 month</option>
                            <option value="3">3 months</option>
                            <option value="6">6 months</option>
                            <option value="12">1 year</option>
                            <option value="24">2 years</option>
                            <option value="36">3 years</option>
                        </select>
                    </FilterSection>

                    {/* === SECTION: Violation Severity (conditionally shown when SIR only) === */}
                    {filters.sirOnly && (
                        <FilterSection
                            id="severity"
                            icon="⚠️"
                            label="Violation Severity"
                            openSections={openSections}
                            onToggle={toggleSection}
                        >
                            <p className="filter-note" style={{ marginTop: 0, marginBottom: '10px' }}>
                                Uncheck a level to exclude those reports from results.
                            </p>
                            <div className="filter-severity-group">
                                {ALL_SEVERITY_LEVELS.map(level => {
                                    const isActive = filters.severityLevels.includes(level);
                                    return (
                                        <label
                                            key={level}
                                            className={`filter-severity-pill ${isActive ? 'active' : ''}`}
                                            style={{ color: SEVERITY_COLORS[level] }}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={isActive}
                                                onChange={(e) => {
                                                    const newLevels = e.target.checked
                                                        ? [...filters.severityLevels, level]
                                                        : filters.severityLevels.filter(l => l !== level);
                                                    onFilterChange('severityLevels', newLevels);
                                                }}
                                            />
                                            <span>{isActive ? '●' : '○'}</span>
                                            <span>{SEVERITY_LABELS[level]}</span>
                                        </label>
                                    );
                                })}
                            </div>
                            <p className="filter-note">
                                Severity is only available for Special Investigation Reports with substantiated violations.
                            </p>
                        </FilterSection>
                    )}

                    {/* === SECTION: Staffing Confidence (conditionally shown when SIR only) === */}
                    {filters.sirOnly && (
                        <FilterSection
                            id="staffing"
                            icon="👥"
                            label="Staffing Violation Confidence"
                            openSections={openSections}
                            onToggle={toggleSection}
                        >
                            <p className="filter-note" style={{ marginTop: 0, marginBottom: '10px' }}>
                                Filter by how confident the analysis is that staffing was a factor.
                            </p>
                            <select
                                id="filterStaffingConfidence"
                                className="filter-select"
                                value={filters.staffingConfidence || ''}
                                onChange={(e) => onFilterChange('staffingConfidence', e.target.value || null)}
                            >
                                <option value="">All (no staffing filter)</option>
                                <option value="yes_high">Believed Yes — High Confidence</option>
                                <option value="yes_medium">Believed Yes — Medium Confidence</option>
                                <option value="yes_low">Believed Yes — Low Confidence</option>
                                <option value="no_low">Believed No — Low Confidence</option>
                                <option value="no_medium">Believed No — Medium Confidence</option>
                                <option value="no_high">Believed No — High Confidence</option>
                            </select>
                            <p className="filter-note">
                                Staffing analysis is AI-generated and may contain errors.
                            </p>
                        </FilterSection>
                    )}

                    {/* === SECTION: Facility Details === */}
                    <FilterSection
                        id="facility"
                        icon="🏛️"
                        label="Facility Details"
                        openSections={openSections}
                        onToggle={toggleSection}
                    >
                        <div className="filter-facility-grid">
                            <div className="filter-field-group">
                                <label className="filter-field-label" htmlFor="filterLicenseStatus">License Status</label>
                                <select
                                    id="filterLicenseStatus"
                                    className="filter-select"
                                    value={filters.licenseStatus || ''}
                                    onChange={(e) => onFilterChange('licenseStatus', e.target.value || null)}
                                >
                                    <option value="">All Statuses</option>
                                    {uniqueLicenseStatuses.map(status => (
                                        <option key={status} value={status}>{status}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="filter-field-group">
                                <label className="filter-field-label" htmlFor="filterAgencyType">Agency Type</label>
                                <select
                                    id="filterAgencyType"
                                    className="filter-select"
                                    value={filters.agencyType || ''}
                                    onChange={(e) => onFilterChange('agencyType', e.target.value || null)}
                                >
                                    <option value="">All Types</option>
                                    {uniqueAgencyTypes.map(type => (
                                        <option key={type} value={type}>{type}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="filter-field-group">
                                <label className="filter-field-label" htmlFor="filterCounty">County</label>
                                <select
                                    id="filterCounty"
                                    className="filter-select"
                                    value={filters.county || ''}
                                    onChange={(e) => onFilterChange('county', e.target.value || null)}
                                >
                                    <option value="">All Counties</option>
                                    {uniqueCounties.map(county => (
                                        <option key={county} value={county}>{county}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <a href={`${baseUrl}facilities.html`} className="filter-link">
                            📊 View Facility Statistics
                        </a>
                    </FilterSection>

                    {/* === SECTION: Keywords === */}
                    <FilterSection
                        id="keywords"
                        icon="🏷️"
                        label="Keywords"
                        openSections={openSections}
                        onToggle={toggleSection}
                    >
                        <p className="filter-note" style={{ marginTop: 0, marginBottom: '10px' }}>
                            Add keywords to find documents about specific topics. Multiple keywords show documents matching any of them.
                        </p>
                        <AutocompleteInput
                            id="keywordFilterInput"
                            placeholder="Search for a keyword…"
                            onSearch={onKeywordSearch}
                            onSelect={onKeywordSelect}
                            renderSuggestion={(s) => (
                                <>
                                    <span>{s.keyword}</span>
                                    <span style={{ color: '#666', fontSize: '0.85em' }}>({s.count})</span>
                                </>
                            )}
                        />
                        <div style={{ marginTop: '10px', minHeight: '28px' }}>
                            {filters.keywords.length > 0 ? (
                                <>
                                    {filters.keywords.length > 1 && (
                                        <div className="filter-keywords-or-label">
                                            Showing documents matching any of these:
                                        </div>
                                    )}
                                    <div className="filter-keywords-list">
                                        {filters.keywords.map(kw => (
                                            <KeywordBadge
                                                key={kw}
                                                keyword={kw}
                                                onRemove={onKeywordRemove}
                                            />
                                        ))}
                                        {filters.keywords.length > 1 && (
                                            <button
                                                type="button"
                                                className="filter-clear-keywords-btn"
                                                onClick={onClearAllKeywords}
                                            >
                                                Clear All
                                            </button>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <span className="filter-keywords-empty">No keywords selected</span>
                            )}
                        </div>
                        <div className="filter-hint">
                            <strong>Note:</strong> Keywords were generated by AI and may be inconsistent.
                            See the <a href={`${baseUrl}keywords.html`}>keywords page</a> for details.
                        </div>
                        <a href={`${baseUrl}keywords.html`} className="filter-link">
                            📊 View All Keywords
                        </a>
                    </FilterSection>
                </div>

                {/* Results count bar */}
                <div className="filter-results-bar">
                    Showing <span className="filter-results-count">{totalAgencies}</span> {totalAgencies === 1 ? 'agency' : 'agencies'} with <span className="filter-results-count">{totalReports}</span> {totalReports === 1 ? 'document' : 'documents'}
                </div>
            </div>
        </>
    );
}

export default FilterPanel;
