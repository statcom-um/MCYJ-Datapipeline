import React, { useState, useEffect, useMemo } from 'react';
import { Header, Loading, Error } from '../components/index.js';
import { AiCaution } from '../components/AiCaution.jsx';
import { AboutSection } from '../components/AboutSection.jsx';
import { getBaseUrl, ACTIVE_LICENSE_STATUSES, ALL_SEVERITY_LEVELS } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

const REGION_NAMES = {
    1: 'Upper Peninsula',
    2: 'Northwest',
    3: 'Northeast',
    4: 'West Michigan',
    5: 'East Central',
    6: 'East Michigan',
    7: 'South Central',
    8: 'Southwest',
    9: 'Southeast',
    10: 'Detroit Metro',
};

const SEVERITY_LABELS = { low: 'Low', moderate: 'Moderate', severe: 'Severe', none: 'None identified' };
const SEVERITY_COLORS = { low: '#f39c12', moderate: '#e67e22', severe: '#e74c3c', none: '#95a5a6' };

const TAB_IDS = ['region-keyword', 'keyword-keyword', 'agencytype-keyword'];
const TAB_LABELS = {
    'region-keyword': 'Region × Keyword',
    'keyword-keyword': 'Keyword × Keyword',
    'agencytype-keyword': 'Agency Type × Keyword',
};

/**
 * Format a proportion as a percentage string.
 */
function pct(numerator, denominator) {
    if (!denominator) return '—';
    return `${((numerator / denominator) * 100).toFixed(1)}%`;
}

/**
 * Render a heatmap-style background for a table cell based on value.
 */
function heatStyle(numerator, denominator) {
    if (!denominator || !numerator) return {};
    const ratio = numerator / denominator;
    // Blue heatmap: intensity 0..0.6 opacity
    const alpha = Math.min(ratio * 0.8, 0.6);
    return { backgroundColor: `rgba(52, 152, 219, ${alpha})` };
}

/**
 * Build county → region mapping from CSV text.
 */
function parseRegionsCsv(csvText) {
    const lines = csvText.trim().split('\n');
    const map = {};
    // skip header
    for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',');
        if (parts.length >= 2) {
            const county = parts[0].trim();
            const regionNum = parseInt(parts[1].trim(), 10);
            if (county && !isNaN(regionNum)) {
                map[county.toUpperCase()] = regionNum;
            }
        }
    }
    return map;
}

/**
 * Determine whether a document represents a substantiated violation.
 * A document is considered substantiated if its SIR summary says violation == 'y'.
 */
function isSubstantiated(doc) {
    return doc.sir_summary?.violation === 'y';
}

/**
 * CrosstabPage — crosstab analysis of keywords against regions, other keywords, and agency types
 */
export function CrosstabPage() {
    const [allAgencies, setAllAgencies] = useState([]);
    const [countyToRegion, setCountyToRegion] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('region-keyword');

    // Filters
    const [severityLevels, setSeverityLevels] = useState([...ALL_SEVERITY_LEVELS]);
    const [activeLicenseOnly, setActiveLicenseOnly] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [agenciesRes, regionsRes] = await Promise.all([
                fetch(`${BASE_URL}data/agencies_data.json`),
                fetch(`${BASE_URL}geo/michigan_prosperity_regions.csv`),
            ]);

            if (!agenciesRes.ok) throw new window.Error(`Failed to load agencies data: ${agenciesRes.statusText}`);

            const agencies = await agenciesRes.json();
            setAllAgencies(agencies);

            if (regionsRes.ok) {
                const csvText = await regionsRes.text();
                setCountyToRegion(parseRegionsCsv(csvText));
            }

            setLoading(false);
        } catch (err) {
            console.error('Error loading data:', err);
            setError(`Failed to load data: ${err.message}`);
            setLoading(false);
        }
    };

    /**
     * Filter agencies and flatten to substantiated-violation SIR documents
     * with region and agency type attached.
     */
    const filteredDocs = useMemo(() => {
        const docs = [];

        for (const agency of allAgencies) {
            const facility = agency.facility;

            // Active license filter
            if (activeLicenseOnly) {
                if (!facility || !ACTIVE_LICENSE_STATUSES.includes(facility.LicenseStatus)) {
                    continue;
                }
            }

            const county = (facility?.County || '').toUpperCase();
            const regionNum = countyToRegion[county] || null;
            const agencyType = facility?.AgencyType || 'Unknown';

            if (!agency.documents || !Array.isArray(agency.documents)) continue;

            for (const doc of agency.documents) {
                // Only SIRs
                if (!doc.is_special_investigation) continue;

                // Only substantiated violations
                if (!isSubstantiated(doc)) continue;

                // Severity filter
                const docLevel = (doc.sir_violation_level?.level || '').toLowerCase() || 'none';
                if (severityLevels.length < ALL_SEVERITY_LEVELS.length) {
                    if (!severityLevels.includes(docLevel)) continue;
                }

                const keywords = doc.sir_violation_level?.keywords || [];

                docs.push({
                    sha256: doc.sha256,
                    regionNum,
                    agencyType,
                    keywords,
                });
            }
        }

        return docs;
    }, [allAgencies, countyToRegion, severityLevels, activeLicenseOnly]);

    /** Collect all unique keywords from filtered docs. */
    const allKeywords = useMemo(() => {
        const set = new Set();
        for (const doc of filteredDocs) {
            for (const kw of doc.keywords) {
                set.add(kw);
            }
        }
        return Array.from(set).sort();
    }, [filteredDocs]);

    /** Collect all unique agency types from filtered docs. */
    const allAgencyTypes = useMemo(() => {
        const set = new Set();
        for (const doc of filteredDocs) {
            set.add(doc.agencyType);
        }
        return Array.from(set).sort();
    }, [filteredDocs]);

    // ── Crosstab computations ──────────────────────────────────────────

    /**
     * Tab 1: Region × Keyword
     * For every prosperity region, what proportion of substantiated-violation reports have each keyword.
     */
    const regionKeywordData = useMemo(() => {
        const regionTotals = {};  // regionNum -> count
        const regionKeywordCounts = {};  // regionNum -> keyword -> count

        for (const doc of filteredDocs) {
            if (doc.regionNum == null) continue;
            const r = doc.regionNum;
            regionTotals[r] = (regionTotals[r] || 0) + 1;
            if (!regionKeywordCounts[r]) regionKeywordCounts[r] = {};
            for (const kw of doc.keywords) {
                regionKeywordCounts[r][kw] = (regionKeywordCounts[r][kw] || 0) + 1;
            }
        }

        return { regionTotals, regionKeywordCounts };
    }, [filteredDocs]);

    /**
     * Tab 2: Keyword × Keyword
     * For every keyword, what proportion of substantiated-violation reports that have that keyword
     * also have each other keyword.
     */
    const keywordKeywordData = useMemo(() => {
        const kwTotals = {};  // keyword -> count of docs with that keyword
        const kwPairCounts = {};  // keyword -> other keyword -> count

        for (const doc of filteredDocs) {
            const kwSet = new Set(doc.keywords);
            for (const kw of kwSet) {
                kwTotals[kw] = (kwTotals[kw] || 0) + 1;
                if (!kwPairCounts[kw]) kwPairCounts[kw] = {};
                for (const other of kwSet) {
                    kwPairCounts[kw][other] = (kwPairCounts[kw][other] || 0) + 1;
                }
            }
        }

        return { kwTotals, kwPairCounts };
    }, [filteredDocs]);

    /**
     * Tab 3: Agency Type × Keyword
     * For each type of agency, what proportion of substantiated-violation reports have each keyword.
     */
    const agencyTypeKeywordData = useMemo(() => {
        const typeTotals = {};  // agencyType -> count
        const typeKeywordCounts = {};  // agencyType -> keyword -> count

        for (const doc of filteredDocs) {
            const t = doc.agencyType;
            typeTotals[t] = (typeTotals[t] || 0) + 1;
            if (!typeKeywordCounts[t]) typeKeywordCounts[t] = {};
            for (const kw of doc.keywords) {
                typeKeywordCounts[t][kw] = (typeKeywordCounts[t][kw] || 0) + 1;
            }
        }

        return { typeTotals, typeKeywordCounts };
    }, [filteredDocs]);

    // ── Severity toggle ────────────────────────────────────────────────

    const handleSeverityToggle = (level) => {
        setSeverityLevels(prev => {
            if (prev.includes(level)) {
                return prev.filter(l => l !== level);
            }
            return [...prev, level];
        });
    };

    // ── Render helpers ─────────────────────────────────────────────────

    if (loading) {
        return (
            <>
                <Header title="Crosstab Analysis" subtitle="Keyword co-occurrence across regions, agency types, and keywords" />
                <div className="container"><Loading message="Loading data..." /></div>
            </>
        );
    }

    if (error) {
        return (
            <>
                <Header title="Crosstab Analysis" subtitle="Keyword co-occurrence across regions, agency types, and keywords" />
                <div className="container"><Error message={error} /></div>
            </>
        );
    }

    const regions = Object.keys(REGION_NAMES).map(Number).sort((a, b) => a - b);

    return (
        <>
            <Header title="Crosstab Analysis" subtitle="Keyword co-occurrence across regions, agency types, and keywords" />
            <div className="container">
                <AboutSection />

                {/* Filters */}
                <div className="crosstab-filters">
                    <div className="crosstab-filter-group">
                        <span className="crosstab-filter-label">Severity: <AiCaution /></span>
                        <div className="crosstab-severity-checks">
                            {ALL_SEVERITY_LEVELS.map(level => (
                                <label key={level} className="crosstab-severity-check">
                                    <input
                                        type="checkbox"
                                        checked={severityLevels.includes(level)}
                                        onChange={() => handleSeverityToggle(level)}
                                    />
                                    <span className="crosstab-severity-dot" style={{ background: SEVERITY_COLORS[level] }} />
                                    {SEVERITY_LABELS[level]}
                                </label>
                            ))}
                        </div>
                    </div>
                    <div className="crosstab-filter-group">
                        <label className="crosstab-license-check">
                            <input
                                type="checkbox"
                                checked={activeLicenseOnly}
                                onChange={e => setActiveLicenseOnly(e.target.checked)}
                            />
                            Only agencies currently licensed
                        </label>
                    </div>
                    <div className="crosstab-summary">
                        {filteredDocs.length} substantiated-violation report{filteredDocs.length !== 1 ? 's' : ''} · {allKeywords.length} keyword{allKeywords.length !== 1 ? 's' : ''}
                    </div>
                </div>

                {/* Tabs */}
                <div className="crosstab-tabs">
                    {TAB_IDS.map(id => (
                        <button
                            key={id}
                            className={`crosstab-tab ${activeTab === id ? 'active' : ''}`}
                            onClick={() => setActiveTab(id)}
                            type="button"
                        >
                            {TAB_LABELS[id]}
                        </button>
                    ))}
                </div>

                {/* Tab content */}
                <div className="crosstab-content">
                    {activeTab === 'region-keyword' && (
                        <RegionKeywordTable
                            regions={regions}
                            keywords={allKeywords}
                            data={regionKeywordData}
                        />
                    )}
                    {activeTab === 'keyword-keyword' && (
                        <KeywordKeywordTable
                            keywords={allKeywords}
                            data={keywordKeywordData}
                        />
                    )}
                    {activeTab === 'agencytype-keyword' && (
                        <AgencyTypeKeywordTable
                            agencyTypes={allAgencyTypes}
                            keywords={allKeywords}
                            data={agencyTypeKeywordData}
                        />
                    )}
                </div>

                {allKeywords.length === 0 && (
                    <div className="crosstab-empty">
                        No substantiated-violation reports match the current filters.
                    </div>
                )}
            </div>

            <div id="commitHash" style={{ textAlign: 'center', padding: '20px', color: '#999', fontSize: '0.8em', fontFamily: 'monospace' }}>
                Version: {__COMMIT_HASH__}
            </div>
        </>
    );
}

// ── Sub-components ─────────────────────────────────────────────────────

function RegionKeywordTable({ regions, keywords, data }) {
    const { regionTotals, regionKeywordCounts } = data;

    if (keywords.length === 0) return null;

    return (
        <div className="crosstab-table-wrapper">
            <p className="crosstab-table-description">
                For each prosperity region, the percentage of substantiated-violation reports that mention each keyword.
                The <strong>N</strong> column shows the total number of substantiated-violation reports in that region.
            </p>
            <table className="crosstab-table">
                <thead>
                    <tr>
                        <th className="crosstab-row-header">Prosperity Region</th>
                        <th className="crosstab-n-col">N</th>
                        {keywords.map(kw => (
                            <th key={kw} className="crosstab-col-header">
                                <span className="crosstab-col-header-text">{kw}</span>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {regions.map(r => {
                        const total = regionTotals[r] || 0;
                        return (
                            <tr key={r}>
                                <td className="crosstab-row-label">{r}. {REGION_NAMES[r]}</td>
                                <td className="crosstab-n-cell">{total}</td>
                                {keywords.map(kw => {
                                    const count = regionKeywordCounts[r]?.[kw] || 0;
                                    return (
                                        <td
                                            key={kw}
                                            className="crosstab-cell"
                                            style={heatStyle(count, total)}
                                            title={`${count} of ${total} reports`}
                                        >
                                            {pct(count, total)}
                                        </td>
                                    );
                                })}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

function KeywordKeywordTable({ keywords, data }) {
    const { kwTotals, kwPairCounts } = data;

    if (keywords.length === 0) return null;

    return (
        <div className="crosstab-table-wrapper">
            <p className="crosstab-table-description">
                For each keyword (row), the percentage of substantiated-violation reports with that keyword
                that also mention each other keyword (column). Diagonal cells show 100% (self-co-occurrence).
                The <strong>N</strong> column shows the total number of reports with the row keyword.
            </p>
            <table className="crosstab-table">
                <thead>
                    <tr>
                        <th className="crosstab-row-header">Keyword</th>
                        <th className="crosstab-n-col">N</th>
                        {keywords.map(kw => (
                            <th key={kw} className="crosstab-col-header">
                                <span className="crosstab-col-header-text">{kw}</span>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {keywords.map(rowKw => {
                        const total = kwTotals[rowKw] || 0;
                        return (
                            <tr key={rowKw}>
                                <td className="crosstab-row-label">{rowKw}</td>
                                <td className="crosstab-n-cell">{total}</td>
                                {keywords.map(colKw => {
                                    const count = kwPairCounts[rowKw]?.[colKw] || 0;
                                    const isDiagonal = rowKw === colKw;
                                    return (
                                        <td
                                            key={colKw}
                                            className={`crosstab-cell ${isDiagonal ? 'crosstab-diagonal' : ''}`}
                                            style={isDiagonal ? {} : heatStyle(count, total)}
                                            title={`${count} of ${total} reports`}
                                        >
                                            {pct(count, total)}
                                        </td>
                                    );
                                })}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

function AgencyTypeKeywordTable({ agencyTypes, keywords, data }) {
    const { typeTotals, typeKeywordCounts } = data;

    if (keywords.length === 0) return null;

    return (
        <div className="crosstab-table-wrapper">
            <p className="crosstab-table-description">
                For each agency type, the percentage of substantiated-violation reports that mention each keyword.
                The <strong>N</strong> column shows the total number of substantiated-violation reports for that agency type.
            </p>
            <table className="crosstab-table">
                <thead>
                    <tr>
                        <th className="crosstab-row-header">Agency Type</th>
                        <th className="crosstab-n-col">N</th>
                        {keywords.map(kw => (
                            <th key={kw} className="crosstab-col-header">
                                <span className="crosstab-col-header-text">{kw}</span>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {agencyTypes.map(type => {
                        const total = typeTotals[type] || 0;
                        return (
                            <tr key={type}>
                                <td className="crosstab-row-label">{type}</td>
                                <td className="crosstab-n-cell">{total}</td>
                                {keywords.map(kw => {
                                    const count = typeKeywordCounts[type]?.[kw] || 0;
                                    return (
                                        <td
                                            key={kw}
                                            className="crosstab-cell"
                                            style={heatStyle(count, total)}
                                            title={`${count} of ${total} reports`}
                                        >
                                            {pct(count, total)}
                                        </td>
                                    );
                                })}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

export default CrosstabPage;
