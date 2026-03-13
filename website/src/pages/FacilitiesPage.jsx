import React, { useState, useEffect } from 'react';
import { Header, BarChart, Loading, Error } from '../components/index.js';
import { getBaseUrl, ACTIVE_LICENSE_STATUSES } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

/**
 * FacilitiesPage component for displaying agency count statistics
 */
export function FacilitiesPage() {
    const [allAgencies, setAllAgencies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentGrouping, setCurrentGrouping] = useState('LicenseStatus');

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const response = await fetch(`${BASE_URL}data/facilities_data.json`);
            if (!response.ok) {
                throw new Error(`Failed to load data: ${response.statusText}`);
            }

            let data = await response.json();

            // Filter to only active agencies
            data = data.filter(f => ACTIVE_LICENSE_STATUSES.includes(f.LicenseStatus));

            setAllAgencies(data);
            setLoading(false);
        } catch (err) {
            console.error('Error loading data:', err);
            setError(`Failed to load data: ${err.message}`);
            setLoading(false);
        }
    };

    const groupAgencies = (groupBy) => {
        const groups = {};

        allAgencies.forEach(agency => {
            const key = agency[groupBy] || 'Unknown';
            if (!groups[key]) {
                groups[key] = [];
            }
            groups[key].push(agency);
        });

        return Object.entries(groups)
            .map(([key, agencies]) => ({
                label: key,
                count: agencies.length,
                linkUrl: `${BASE_URL}?${groupBy.toLowerCase()}=${encodeURIComponent(key)}`,
                tooltip: `View agencies with ${groupBy}: ${key}`
            }))
            .sort((a, b) => b.count - a.count);
    };

    const getChartTitle = () => {
        const titles = {
            'LicenseStatus': 'Agencies by License Status',
            'AgencyType': 'Agencies by Agency Type',
            'County': 'Agencies by County'
        };
        return titles[currentGrouping] || `Agencies by ${currentGrouping}`;
    };

    const getStatsSummary = () => {
        const totalAgencies = allAgencies.length;
        const uniqueCounties = new Set(allAgencies.map(a => a.County)).size;
        const uniqueTypes = new Set(allAgencies.map(a => a.AgencyType)).size;

        return (
            <>
                <strong>Summary:</strong>{' '}
                {totalAgencies} active agencies across{' '}
                {uniqueCounties} counties and{' '}
                {uniqueTypes} agency types.
            </>
        );
    };

    if (loading) {
        return (
            <>
                <Header
                    title="Agency Counts"
                    subtitle="Active Licensed Agencies by Grouping"
                />
                <div className="container">
                    <Loading message="Loading data..." />
                </div>
            </>
        );
    }

    if (error) {
        return (
            <>
                <Header
                    title="Agency Counts"
                    subtitle="Active Licensed Agencies by Grouping"
                />
                <div className="container">
                    <Error message={error} />
                </div>
            </>
        );
    }

    const chartData = groupAgencies(currentGrouping);

    return (
        <>
            <Header
                title="Agency Counts"
                subtitle="Active Licensed Agencies by Grouping"
            />
            <div className="container">


                <div className="facilities-container">
                    <div className="facilities-header">
                        <h2>Agency Counts by Grouping</h2>
                        <p className="facilities-description">
                            This page shows counts of agencies with active licenses, grouped by various attributes.
                            Click on any group to view the corresponding agencies in the agency view.
                        </p>
                    </div>

                    <div className="grouping-selector">
                        <label htmlFor="groupingSelect">Group by:</label>
                        <select
                            id="groupingSelect"
                            value={currentGrouping}
                            onChange={(e) => setCurrentGrouping(e.target.value)}
                        >
                            <option value="LicenseStatus">License Status</option>
                            <option value="AgencyType">Agency Type</option>
                            <option value="County">County</option>
                        </select>
                    </div>

                    <div className="stats-summary">
                        {getStatsSummary()}
                    </div>

                    <BarChart
                        title={getChartTitle()}
                        data={chartData}
                    />
                </div>
            </div>
        </>
    );
}

export default FacilitiesPage;
