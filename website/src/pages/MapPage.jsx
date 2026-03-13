import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import { Header, Loading, Error } from '../components/index.js';
import { getBaseUrl } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

const AGENCY_TYPE_COLORS = {
    'CPA - Private': '#3498db',
    'CPA - Government': '#27ae60',
    'CCI': '#e67e22',
    'Court': '#e74c3c',
    'Child Placing Agency': '#3498db',
    'Child Caring Institution': '#e67e22',
};
const DEFAULT_COLOR = '#9b59b6';

function getColor(agencyType) {
    if (!agencyType) return DEFAULT_COLOR;
    for (const [key, color] of Object.entries(AGENCY_TYPE_COLORS)) {
        if (agencyType.toLowerCase().includes(key.toLowerCase())) return color;
    }
    return DEFAULT_COLOR;
}

export function MapPage() {
    const [facilities, setFacilities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [visibleTypes, setVisibleTypes] = useState(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const response = await fetch(`${BASE_URL}data/facilities_data.json`);
            if (!response.ok) throw new Error(`Failed to load data: ${response.statusText}`);

            const data = await response.json();
            const withCoords = data.filter(f => f.lat != null && f.lon != null);
            setFacilities(withCoords);

            // Initialize all types as visible
            const types = new Set(withCoords.map(f => f.AgencyType || 'Unknown'));
            const initial = {};
            types.forEach(t => { initial[t] = true; });
            setVisibleTypes(initial);

            setLoading(false);
        } catch (err) {
            console.error('Error loading data:', err);
            setError(`Failed to load data: ${err.message}`);
            setLoading(false);
        }
    };

    const filteredFacilities = useMemo(() => {
        if (!visibleTypes) return facilities;
        return facilities.filter(f => visibleTypes[f.AgencyType || 'Unknown']);
    }, [facilities, visibleTypes]);

    const toggleType = (type) => {
        setVisibleTypes(prev => ({ ...prev, [type]: !prev[type] }));
    };

    if (loading) {
        return (
            <>
                <Header title="Agency Map" subtitle="Geographic distribution of licensed agencies" />
                <div className="container"><Loading message="Loading map data..." /></div>
            </>
        );
    }

    if (error) {
        return (
            <>
                <Header title="Agency Map" subtitle="Geographic distribution of licensed agencies" />
                <div className="container"><Error message={error} /></div>
            </>
        );
    }

    if (facilities.length === 0) {
        return (
            <>
                <Header title="Agency Map" subtitle="Geographic distribution of licensed agencies" />
                <div className="container">
                    <div className="map-no-data">
                        No agencies with geographic coordinates found. Run the data generation script with --gazetteer-zip to populate coordinates.
                    </div>
                </div>
            </>
        );
    }

    const typeEntries = visibleTypes ? Object.keys(visibleTypes).sort() : [];

    return (
        <>
            <Header title="Facility Map" subtitle="Geographic distribution of licensed facilities" />
            <div className="container">
                <div className="map-page-container">
                    <div className="map-legend">
                        <strong>Agency Types:</strong>
                        <div className="map-legend-items">
                            {typeEntries.map(type => (
                                <label key={type} className="map-legend-item">
                                    <input
                                        type="checkbox"
                                        checked={visibleTypes[type]}
                                        onChange={() => toggleType(type)}
                                    />
                                    <span
                                        className="map-legend-color"
                                        style={{ background: getColor(type) }}
                                    ></span>
                                    <span>{type} ({facilities.filter(f => (f.AgencyType || 'Unknown') === type).length})</span>
                                </label>
                            ))}
                        </div>
                        <div className="map-legend-count">
                            Showing {filteredFacilities.length} of {facilities.length} agencies
                        </div>
                    </div>

                    <div className="map-wrapper">
                        <MapContainer
                            center={[44.3, -84.7]}
                            zoom={7}
                            style={{ height: '600px', width: '100%', borderRadius: '8px' }}
                        >
                            <TileLayer
                                attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                            />
                            <MarkerClusterGroup chunkedLoading>
                                {filteredFacilities.map((f, idx) => (
                                    <CircleMarker
                                        key={`${f.LicenseNumber}-${idx}`}
                                        center={[f.lat, f.lon]}
                                        radius={7}
                                        fillColor={getColor(f.AgencyType)}
                                        color="#fff"
                                        weight={1}
                                        opacity={1}
                                        fillOpacity={0.8}
                                    >
                                        <Popup>
                                            <div className="map-popup">
                                                <strong>
                                                    <a href={`${BASE_URL}agency.html?id=${encodeURIComponent(f.agencyId || f.LicenseNumber)}`}>
                                                        {f.AgencyName || 'Unknown'}
                                                    </a>
                                                </strong>
                                                <div>{f.AgencyType}</div>
                                                {f.County && <div>County: {f.County}</div>}
                                                {f.City && <div>City: {f.City}</div>}
                                                <div>License: {f.LicenseStatus}</div>
                                            </div>
                                        </Popup>
                                    </CircleMarker>
                                ))}
                            </MarkerClusterGroup>
                        </MapContainer>
                    </div>
                </div>
            </div>

            <div id="commitHash" style={{ textAlign: 'center', padding: '20px', color: '#999', fontSize: '0.8em', fontFamily: 'monospace' }}>
                Version: {__COMMIT_HASH__}
            </div>
        </>
    );
}

export default MapPage;
