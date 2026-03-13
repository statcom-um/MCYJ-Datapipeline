import React, { useState, useEffect, useMemo } from 'react';
import { Header, Loading, Error, Pagination } from '../components/index.js';
import { AiCaution } from '../components/AiCaution.jsx';
import { getBaseUrl, ALL_SEVERITY_LEVELS } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();
const PAGE_SIZE = 50;

export function DocumentsPage() {
    const [allDocuments, setAllDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);

    // Filters
    const [sirOnly, setSirOnly] = useState(true);
    const [severity, setSeverity] = useState('');
    const [county, setCounty] = useState('');
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    // Sort
    const [sortField, setSortField] = useState('date_iso');
    const [sortDir, setSortDir] = useState('desc');

    // Unique values for filters
    const [uniqueCounties, setUniqueCounties] = useState([]);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const response = await fetch(`${BASE_URL}data/agencies_data.json`);
            if (!response.ok) throw new Error(`Failed to load data: ${response.statusText}`);

            const agencies = await response.json();
            const docs = [];
            const counties = new Set();

            agencies.forEach(agency => {
                if (agency.facility?.County) counties.add(agency.facility.County);
                if (agency.documents && Array.isArray(agency.documents)) {
                    agency.documents.forEach(doc => {
                        docs.push({
                            ...doc,
                            agencyId: agency.agencyId,
                            agencyName: agency.AgencyName,
                            county: agency.facility?.County || '',
                            agencyType: agency.facility?.AgencyType || '',
                        });
                    });
                }
            });

            setAllDocuments(docs);
            setUniqueCounties(Array.from(counties).sort());
            setLoading(false);
        } catch (err) {
            console.error('Error loading data:', err);
            setError(`Failed to load data: ${err.message}`);
            setLoading(false);
        }
    };

    const filteredDocuments = useMemo(() => {
        let docs = allDocuments;

        if (sirOnly) {
            docs = docs.filter(d => d.is_special_investigation);
        }

        if (severity) {
            docs = docs.filter(d => {
                const level = d.sir_violation_level?.level?.toLowerCase() || 'none';
                return level === severity;
            });
        }

        if (county) {
            docs = docs.filter(d => d.county === county);
        }

        if (dateFrom) {
            docs = docs.filter(d => d.date_iso && d.date_iso >= dateFrom);
        }

        if (dateTo) {
            docs = docs.filter(d => d.date_iso && d.date_iso <= dateTo);
        }

        if (searchQuery.trim()) {
            const q = searchQuery.trim().toLowerCase();
            docs = docs.filter(d =>
                (d.document_title || '').toLowerCase().includes(q) ||
                (d.agencyName || '').toLowerCase().includes(q) ||
                (d.sir_violation_level?.keywords || []).some(k => k.toLowerCase().includes(q))
            );
        }

        // Sort
        docs = [...docs].sort((a, b) => {
            let aVal = a[sortField] || '';
            let bVal = b[sortField] || '';
            if (sortField === 'agencyName') {
                aVal = a.agencyName || '';
                bVal = b.agencyName || '';
            }
            if (sortField === 'county') {
                aVal = a.county || '';
                bVal = b.county || '';
            }
            const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            return sortDir === 'asc' ? cmp : -cmp;
        });

        return docs;
    }, [allDocuments, sirOnly, severity, county, dateFrom, dateTo, searchQuery, sortField, sortDir]);

    // Reset page when filters change
    useEffect(() => {
        setCurrentPage(1);
    }, [sirOnly, severity, county, dateFrom, dateTo, searchQuery, sortField, sortDir]);

    const handleSort = (field) => {
        if (sortField === field) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDir(field === 'date_iso' ? 'desc' : 'asc');
        }
    };

    const sortIndicator = (field) => {
        if (sortField !== field) return '';
        return sortDir === 'asc' ? ' \u25B2' : ' \u25BC';
    };

    const getSeverityStyle = (level) => {
        if (!level) return {};
        switch (level.toLowerCase()) {
            case 'severe': return { color: '#e74c3c' };
            case 'moderate': return { color: '#e67e22' };
            case 'low': return { color: '#f39c12' };
            default: return { color: '#95a5a6' };
        }
    };

    if (loading) {
        return (
            <>
                <Header title="All Documents" subtitle="Browse all documents across agencies" />
                <div className="container"><Loading message="Loading documents..." /></div>
            </>
        );
    }

    if (error) {
        return (
            <>
                <Header title="All Documents" subtitle="Browse all documents across agencies" />
                <div className="container"><Error message={error} /></div>
            </>
        );
    }

    const pagedDocs = filteredDocuments.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

    return (
        <>
            <Header title="All Documents" subtitle="Browse all documents across agencies" />
            <div className="container">
                <div className="documents-page-container">
                    <div className="documents-filters">
                        <div className="documents-filter-row">
                            <label className="documents-filter-item">
                                <input
                                    type="checkbox"
                                    checked={sirOnly}
                                    onChange={e => setSirOnly(e.target.checked)}
                                />
                                SIR only
                            </label>
                            <select
                                className="filter-select documents-filter-select"
                                value={severity}
                                onChange={e => setSeverity(e.target.value)}
                            >
                                <option value="">All severities</option>
                                {ALL_SEVERITY_LEVELS.map(s => (
                                    <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                                ))}
                            </select>
                            <select
                                className="filter-select documents-filter-select"
                                value={county}
                                onChange={e => setCounty(e.target.value)}
                            >
                                <option value="">All counties</option>
                                {uniqueCounties.map(c => (
                                    <option key={c} value={c}>{c}</option>
                                ))}
                            </select>
                            <input
                                type="date"
                                className="documents-filter-date"
                                value={dateFrom}
                                onChange={e => setDateFrom(e.target.value)}
                                placeholder="From"
                                title="From date"
                            />
                            <input
                                type="date"
                                className="documents-filter-date"
                                value={dateTo}
                                onChange={e => setDateTo(e.target.value)}
                                placeholder="To"
                                title="To date"
                            />
                            <input
                                type="text"
                                className="documents-filter-search"
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                placeholder="Search title, agency, keywords..."
                            />
                        </div>
                        <div className="documents-results-count">
                            {filteredDocuments.length} document{filteredDocuments.length !== 1 ? 's' : ''} found
                        </div>
                    </div>

                    <div className="documents-table-wrapper">
                        <table className="documents-table">
                            <thead>
                                <tr>
                                    <th onClick={() => handleSort('date_iso')} className="sortable">
                                        Date{sortIndicator('date_iso')}
                                    </th>
                                    <th onClick={() => handleSort('agencyName')} className="sortable">
                                        Agency{sortIndicator('agencyName')}
                                    </th>
                                    <th>Title</th>
                                    <th>Type</th>
                                    <th onClick={() => handleSort('county')} className="sortable">
                                        County{sortIndicator('county')}
                                    </th>
                                    <th>Severity</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pagedDocs.map((doc, idx) => {
                                    const level = doc.sir_violation_level?.level;
                                    return (
                                        <tr key={`${doc.sha256}-${idx}`}>
                                            <td className="documents-td-date">{doc.date || '—'}</td>
                                            <td>
                                                <a href={`${BASE_URL}agency.html?id=${encodeURIComponent(doc.agencyId)}`}>
                                                    {doc.agencyName}
                                                </a>
                                            </td>
                                            <td>
                                                <a href={`${BASE_URL}document.html?sha=${doc.sha256}`}>
                                                    {doc.document_title || 'Untitled'}
                                                </a>
                                            </td>
                                            <td>{doc.is_special_investigation ? 'SIR' : 'Report'}</td>
                                            <td>{doc.county || '—'}</td>
                                            <td style={getSeverityStyle(level)}>
                                                {level ? (
                                                    <><span>{level.charAt(0).toUpperCase() + level.slice(1)}</span> <AiCaution /></>
                                                ) : '—'}
                                            </td>
                                        </tr>
                                    );
                                })}
                                {pagedDocs.length === 0 && (
                                    <tr>
                                        <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                                            No documents match your filters.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    <Pagination
                        totalItems={filteredDocuments.length}
                        itemsPerPage={PAGE_SIZE}
                        currentPage={currentPage}
                        onPageChange={setCurrentPage}
                    />
                </div>
            </div>

            <div id="commitHash" style={{ textAlign: 'center', padding: '20px', color: '#999', fontSize: '0.8em', fontFamily: 'monospace' }}>
                Version: {__COMMIT_HASH__}
            </div>
        </>
    );
}

export default DocumentsPage;
