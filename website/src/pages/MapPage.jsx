import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import { Header, Loading, Error } from '../components/index.js';
import { getBaseUrl } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

const TYPE_COLORS = {
    'CPA-Private':  '#4fffb0',
    'CPA-Govt':     '#7b6fff',
    'CPA-MDHHS':    '#ffd166',
    'CCI':          '#ff6b6b',
    'Court':        '#48cae4',
};
const DEFAULT_COLOR = '#9b59b6';

function classifyType(agencyType) {
    if (!agencyType) return 'CPA-Private';
    if (agencyType.includes('Private'))                                  return 'CPA-Private';
    if (agencyType.includes('Governmental'))                             return 'CPA-Govt';
    if (agencyType.includes('MDHHS') && agencyType.includes('Placing')) return 'CPA-MDHHS';
    if (agencyType.includes('Caring'))                                   return 'CCI';
    if (agencyType.includes('Court'))                                    return 'Court';
    return 'CPA-Private';
}

function getColor(agencyType) {
    return TYPE_COLORS[classifyType(agencyType)] || DEFAULT_COLOR;
}

function makeDivIcon(color) {
    return L.divIcon({
        html: `<div style="width:11px;height:11px;border-radius:50%;background:${color};border:2px solid rgba(255,255,255,0.8);box-shadow:0 0 5px ${color}80;"></div>`,
        className: '',
        iconSize: [11, 11],
        iconAnchor: [5, 5],
    });
}

// Cache icons per color
const iconCache = {};
function getIcon(agencyType) {
    const color = getColor(agencyType);
    if (!iconCache[color]) {
        iconCache[color] = makeDivIcon(color);
    }
    return iconCache[color];
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
            // Attach classified type
            withCoords.forEach(f => { f._type = classifyType(f.AgencyType); });
            setFacilities(withCoords);

            const types = new Set(withCoords.map(f => f._type));
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
        return facilities.filter(f => visibleTypes[f._type]);
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
    const typeCounts = {};
    facilities.forEach(f => { typeCounts[f._type] = (typeCounts[f._type] || 0) + 1; });

    return (
        <>
            <Header title="Agency Map" subtitle="Geographic distribution of licensed agencies" />
            <div className="container">
                <div className="map-page-container">
                    <div className="map-legend">
                        <strong>Agency Types:</strong>
                        <div className="map-legend-items">
                            {typeEntries.map(type => (
                                <label key={type} className={`map-legend-item ${visibleTypes[type] ? 'active' : ''}`}>
                                    <input
                                        type="checkbox"
                                        checked={visibleTypes[type]}
                                        onChange={() => toggleType(type)}
                                    />
                                    <span
                                        className="map-legend-color"
                                        style={{ background: TYPE_COLORS[type] || DEFAULT_COLOR }}
                                    ></span>
                                    <span>{type.replace('-', ' ')} ({typeCounts[type] || 0})</span>
                                </label>
                            ))}
                        </div>
                        <div className="map-legend-count">
                            Showing {filteredFacilities.length} of {facilities.length} agencies
                        </div>
                    </div>

                    <div className="map-wrapper">
                        <MapContainer
                            center={[44.3148, -85.6024]}
                            zoom={7}
                            style={{ height: '600px', width: '100%', borderRadius: '0 0 8px 8px' }}
                        >
                            <TileLayer
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &amp; <a href="https://carto.com/">CARTO</a>'
                                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                            />
                            <MarkerClusterGroup
                                chunkedLoading
                                maxClusterRadius={50}
                                spiderfyOnMaxZoom={true}
                                showCoverageOnHover={false}
                            >
                                {filteredFacilities.map((f, idx) => (
                                    <Marker
                                        key={`${f.LicenseNumber}-${idx}`}
                                        position={[f.lat, f.lon]}
                                        icon={getIcon(f.AgencyType)}
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
                                    </Marker>
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
