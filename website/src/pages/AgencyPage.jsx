import React, { useState, useEffect } from 'react';
import { Header, Loading, Error } from '../components/index.js';
import { DocumentList } from '../components/DocumentItem.jsx';
import { AiCaution } from '../components/AiCaution.jsx';
import { getBaseUrl, copyToClipboard } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

/**
 * AgencyPage — dedicated page showing all information for a single agency.
 * Accessed via agency.html?id=<agencyId>
 */
export function AgencyPage() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [agency, setAgency] = useState(null);
    const [copyFeedback, setCopyFeedback] = useState(false);

    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const agencyId = urlParams.get('id');

        if (!agencyId) {
            setError('No agency ID provided. Please navigate from the dashboard.');
            setLoading(false);
            return;
        }

        loadAgency(agencyId);
    }, []);

    const loadAgency = async (agencyId) => {
        try {
            const response = await fetch(`${BASE_URL}data/agencies_data.json`);
            if (!response.ok) {
                throw new Error(`Failed to load data: ${response.statusText}`);
            }

            const allAgencies = await response.json();
            const found = allAgencies.find(a => a.agencyId === agencyId);

            if (!found) {
                setError(`Agency with ID "${agencyId}" not found.`);
                setLoading(false);
                return;
            }

            setAgency(found);
            setLoading(false);
        } catch (err) {
            console.error('Error loading agency data:', err);
            setError(`Failed to load data: ${err.message}`);
            setLoading(false);
        }
    };

    const handleCopyLink = () => {
        copyToClipboard(
            window.location.href,
            () => {
                setCopyFeedback(true);
                setTimeout(() => setCopyFeedback(false), 1500);
            },
            (err) => console.error('Failed to copy link:', err)
        );
    };

    const handleCopyDocumentLink = (sha256, event) => {
        if (event) event.stopPropagation();
        const url = `${window.location.origin}${BASE_URL}document.html?sha=${sha256}`;

        copyToClipboard(
            url,
            () => {
                const btn = event?.target;
                if (btn) {
                    const originalText = btn.textContent;
                    btn.textContent = '✓';
                    setTimeout(() => { btn.textContent = originalText; }, 1500);
                }
            },
            (err) => {
                console.error('Failed to copy link:', err);
            }
        );
    };

    if (loading) {
        return (
            <>
                <Header
                    title="Agency Details"
                    subtitle="Michigan Child Welfare Licensing Dashboard"
                />
                <div className="container">
                    <a href={`${BASE_URL}`} className="back-link">← Back to Dashboard</a>
                    <Loading message="Loading agency data..." />
                </div>
            </>
        );
    }

    if (error) {
        return (
            <>
                <Header
                    title="Agency Details"
                    subtitle="Michigan Child Welfare Licensing Dashboard"
                />
                <div className="container">
                    <a href={`${BASE_URL}`} className="back-link">← Back to Dashboard</a>
                    <Error message={error} />
                </div>
            </>
        );
    }

    const facility = agency.facility;
    const documents = agency.documents || [];

    // Separate SIRs from other documents
    const sirDocuments = documents.filter(d => d.is_special_investigation);
    const otherDocuments = documents.filter(d => !d.is_special_investigation);

    // Count severity levels
    const severityCounts = { severe: 0, moderate: 0, low: 0, none: 0 };
    sirDocuments.forEach(d => {
        const level = d.sir_violation_level?.level?.toLowerCase();
        if (level && severityCounts.hasOwnProperty(level)) {
            severityCounts[level]++;
        } else {
            severityCounts.none++;
        }
    });

    return (
        <>
            <Header
                title={agency.AgencyName || 'Unknown Agency'}
                subtitle="Agency Details"
            />
            <div className="container">
                <a href={`${BASE_URL}`} className="back-link">← Back to Dashboard</a>

                <div className="agency-page-container">
                    {/* Agency Header Info */}
                    <div className="agency-page-header">
                        <div className="agency-page-title-row">
                            <h2>{agency.AgencyName || 'Unknown Agency'}</h2>
                            <button
                                className="copy-link-btn"
                                onClick={handleCopyLink}
                                title="Copy link to this agency"
                                style={{ fontSize: '1.2em' }}
                            >
                                {copyFeedback ? '✓' : '🔗'}
                            </button>
                        </div>
                        <div className="agency-page-id">Agency ID: {agency.agencyId}</div>
                    </div>

                    {/* Facility Information */}
                    {facility && (
                        <div className="agency-page-section">
                            <h3>🏛️ Facility Information</h3>
                            <div className="agency-page-info-grid">
                                {facility.LicenseStatus && (
                                    <div className="agency-page-info-item">
                                        <span className="agency-page-info-label">License Status</span>
                                        <span className={`stat-badge ${facility.LicenseStatus === 'Regular' || facility.LicenseStatus === 'Original' ? 'status-active' : 'status-inactive'}`}>
                                            {facility.LicenseStatus}
                                        </span>
                                    </div>
                                )}
                                {facility.AgencyType && (
                                    <div className="agency-page-info-item">
                                        <span className="agency-page-info-label">Agency Type</span>
                                        <span>{facility.AgencyType}</span>
                                    </div>
                                )}
                                {facility.County && (
                                    <div className="agency-page-info-item">
                                        <span className="agency-page-info-label">County</span>
                                        <span>{facility.County}</span>
                                    </div>
                                )}
                                {facility.Capacity && (
                                    <div className="agency-page-info-item">
                                        <span className="agency-page-info-label">Capacity</span>
                                        <span>{facility.Capacity}</span>
                                    </div>
                                )}
                                {facility.LicenseeName && (
                                    <div className="agency-page-info-item">
                                        <span className="agency-page-info-label">Licensee</span>
                                        <span>{facility.LicenseeName}</span>
                                    </div>
                                )}
                                {facility.Address && (
                                    <div className="agency-page-info-item">
                                        <span className="agency-page-info-label">Address</span>
                                        <span>{facility.Address}{facility.City ? `, ${facility.City}` : ''}{facility.Zip ? ` ${facility.Zip}` : ''}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Summary Stats */}
                    <div className="agency-page-section">
                        <h3>📊 Summary</h3>
                        <div className="agency-page-stats">
                            <div className="stat-card">
                                <div className="stat-number">{documents.length}</div>
                                <div className="stat-label">Total Documents</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-number">{sirDocuments.length}</div>
                                <div className="stat-label">Investigation Reports</div>
                            </div>
                            {sirDocuments.length > 0 && (
                                <>
                                    <div className="stat-card" style={{ borderTop: '3px solid #e74c3c' }}>
                                        <div className="stat-number" style={{ color: '#e74c3c' }}>{severityCounts.severe}</div>
                                        <div className="stat-label">Severe <AiCaution /></div>
                                    </div>
                                    <div className="stat-card" style={{ borderTop: '3px solid #e67e22' }}>
                                        <div className="stat-number" style={{ color: '#e67e22' }}>{severityCounts.moderate}</div>
                                        <div className="stat-label">Moderate <AiCaution /></div>
                                    </div>
                                    <div className="stat-card" style={{ borderTop: '3px solid #f39c12' }}>
                                        <div className="stat-number" style={{ color: '#f39c12' }}>{severityCounts.low}</div>
                                        <div className="stat-label">Low <AiCaution /></div>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Investigation Reports */}
                    {sirDocuments.length > 0 && (
                        <div className="agency-page-section">
                            <h3>🔍 Special Investigation Reports ({sirDocuments.length})</h3>
                            <DocumentList
                                documents={sirDocuments}
                                baseUrl={BASE_URL}
                                onCopyLink={handleCopyDocumentLink}
                            />
                        </div>
                    )}

                    {/* Other Documents */}
                    {otherDocuments.length > 0 && (
                        <div className="agency-page-section">
                            <h3>📄 Other Documents ({otherDocuments.length})</h3>
                            <DocumentList
                                documents={otherDocuments}
                                baseUrl={BASE_URL}
                                onCopyLink={handleCopyDocumentLink}
                            />
                        </div>
                    )}

                    {/* No Documents */}
                    {documents.length === 0 && (
                        <div className="agency-page-section">
                            <p style={{ color: '#666', fontStyle: 'italic' }}>No documents available for this agency.</p>
                        </div>
                    )}
                </div>
            </div>

            <div id="commitHash" style={{ textAlign: 'center', padding: '20px', color: '#999', fontSize: '0.8em', fontFamily: 'monospace' }}>
                Version: {__COMMIT_HASH__}
            </div>
        </>
    );
}

export default AgencyPage;
