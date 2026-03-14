import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import { Header, Loading, Error } from '../components/index.js';
import { getBaseUrl } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

const FLY_ANIMATION_MS = 900;

function getSearchPlaceholder(field) {
    if (field === 'zip') return 'Enter zip code…';
    if (field === 'all') return 'Search by name, city, county, or zip…';
    return `Search by ${field}…`;
}

function formatLocation(city, county, zip) {
    return [city, county ? `${county} County` : null, zip].filter(Boolean).join(' · ');
}

/** Single-agency marker — translucent dot with dashed ring */
const defaultIcon = L.divIcon({
    html: `<span class="map-marker-dot"><span class="map-marker-ring"></span></span>`,
    className: 'map-marker-icon',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
});

const highlightIcon = L.divIcon({
    html: `<span class="map-marker-dot map-marker-highlight"><span class="map-marker-ring"></span></span>`,
    className: 'map-marker-icon',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
});

/** Multi-agency zip group marker — shows count badge */
function createZipGroupIcon(count, isHighlighted) {
    const cls = isHighlighted ? 'map-zipgroup map-zipgroup-highlight' : 'map-zipgroup';
    const size = isHighlighted ? 38 : 34;
    return L.divIcon({
        html: `<div class="${cls}"><span>${count}</span></div>`,
        className: 'map-marker-icon',
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
    });
}

function createClusterIcon(cluster) {
    // Sum actual agency counts, not zip-group marker counts
    const markers = cluster.getAllChildMarkers();
    const count = markers.reduce((sum, m) => sum + (m.options.agencyCount || 1), 0);
    let sizeClass = 'map-cluster-small';
    let size = 40;
    if (count >= 100) { sizeClass = 'map-cluster-large'; size = 54; }
    else if (count >= 20) { sizeClass = 'map-cluster-medium'; size = 46; }

    return L.divIcon({
        html: `<div class="map-cluster ${sizeClass}"><span>${count}</span></div>`,
        className: 'map-cluster-icon',
        iconSize: [size, size],
    });
}

/** Fly the map to a location */
function FlyTo({ position, zoom }) {
    const map = useMap();
    useEffect(() => {
        if (position) {
            map.flyTo(position, zoom || 14, { duration: 0.8 });
        }
    }, [position, zoom, map]);
    return null;
}

/**
 * Group facilities by zip code.
 * Returns an array of { zip, lat, lon, facilities: [...] } objects,
 * one per unique zip code.
 */
function groupByZip(facilities) {
    const groups = new Map();
    for (const f of facilities) {
        const zip = (f.ZipCode || '').slice(0, 5);
        if (!groups.has(zip)) {
            groups.set(zip, { zip, lat: f.lat, lon: f.lon, facilities: [] });
        }
        groups.get(zip).facilities.push(f);
    }
    // Sort facilities within each group alphabetically
    for (const g of groups.values()) {
        g.facilities.sort((a, b) => (a.AgencyName || '').localeCompare(b.AgencyName || ''));
    }
    return Array.from(groups.values());
}

export function MapPage() {
    const [facilities, setFacilities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [searchField, setSearchField] = useState('all');
    const [selectedId, setSelectedId] = useState(null);
    const [flyTarget, setFlyTarget] = useState(null);
    const markerRefs = useRef({});

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
            setLoading(false);
        } catch (err) {
            console.error('Error loading data:', err);
            setError(`Failed to load data: ${err.message}`);
            setLoading(false);
        }
    };

    /** Group facilities by zip for map markers */
    const zipGroups = useMemo(() => groupByZip(facilities), [facilities]);

    /** Look up which zip group an agency belongs to */
    const zipForFacility = useMemo(() => {
        const map = new Map();
        for (const g of zipGroups) {
            for (const f of g.facilities) {
                map.set(f.LicenseNumber, g.zip);
            }
        }
        return map;
    }, [zipGroups]);

    const matchesSearch = useCallback((f, term) => {
        if (!term) return true;
        const q = term.toLowerCase();
        if (searchField === 'name') return (f.AgencyName || '').toLowerCase().includes(q);
        if (searchField === 'city') return (f.City || '').toLowerCase().includes(q);
        if (searchField === 'county') return (f.County || '').toLowerCase().includes(q);
        if (searchField === 'zip') return (f.ZipCode || '').startsWith(q);
        return (
            (f.AgencyName || '').toLowerCase().includes(q) ||
            (f.City || '').toLowerCase().includes(q) ||
            (f.County || '').toLowerCase().includes(q) ||
            (f.ZipCode || '').startsWith(q)
        );
    }, [searchField]);

    const searchResults = useMemo(() => {
        if (!searchTerm) return [];
        return facilities
            .filter(f => matchesSearch(f, searchTerm))
            .sort((a, b) => (a.AgencyName || '').localeCompare(b.AgencyName || ''));
    }, [facilities, searchTerm, matchesSearch]);

    const handleSelectAgency = (f) => {
        const id = f.LicenseNumber;
        const zip = zipForFacility.get(id) || (f.ZipCode || '').slice(0, 5);
        setSelectedId(id);
        setFlyTarget({ position: [f.lat, f.lon], zoom: 15 });

        // Open the zip group marker's popup
        setTimeout(() => {
            const marker = markerRefs.current[zip];
            if (marker) marker.openPopup();
        }, FLY_ANIMATION_MS);
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

    return (
        <>
            <Header title="Agency Map" subtitle="Geographic distribution of licensed agencies" />
            <div className="container">
                <div className="map-zip-notice">
                    <span aria-hidden="true">📍 </span>Agency locations on this map are approximate. Each marker represents a 5-digit zip code area and lists all agencies registered there.
                </div>
                <div className="map-page-layout">
                    {/* Search sidebar */}
                    <div className="map-sidebar">
                        <div className="map-search-header">
                            <h3>Find an Agency</h3>
                            <p>{facilities.length} agencies across {zipGroups.length} 5-digit zip codes</p>
                        </div>

                        <div className="map-search-controls">
                            <select
                                className="map-search-field"
                                value={searchField}
                                onChange={(e) => setSearchField(e.target.value)}
                                aria-label="Search field"
                            >
                                <option value="all">All Fields</option>
                                <option value="name">Name</option>
                                <option value="city">City</option>
                                <option value="county">County</option>
                                <option value="zip">Zip Code</option>
                            </select>
                            <input
                                type="text"
                                className="map-search-input"
                                placeholder={getSearchPlaceholder(searchField)}
                                value={searchTerm}
                                onChange={(e) => { setSearchTerm(e.target.value); setSelectedId(null); }}
                                aria-label="Search agencies"
                            />
                        </div>

                        <div className="map-search-results">
                            {searchTerm && searchResults.length === 0 && (
                                <div className="map-search-empty">No agencies found.</div>
                            )}
                            {!searchTerm && (
                                <div className="map-search-hint">
                                    Type a name, city, county, or zip code to find agencies.
                                </div>
                            )}
                            {searchResults.map((f) => {
                                const id = f.LicenseNumber;
                                return (
                                    <button
                                        key={id}
                                        className={`map-search-result ${selectedId === id ? 'selected' : ''}`}
                                        onClick={() => handleSelectAgency(f)}
                                        type="button"
                                    >
                                        <span className="map-result-name">{f.AgencyName || 'Unknown'}</span>
                                        <span className="map-result-detail">
                                            {formatLocation(f.City, f.County, f.ZipCode)}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Map */}
                    <div className="map-main">
                        <MapContainer
                            center={[44.3148, -85.6024]}
                            zoom={7}
                            style={{ height: '100%', width: '100%' }}
                        >
                            <TileLayer
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &amp; <a href="https://carto.com/">CARTO</a>'
                                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                            />
                            {flyTarget && <FlyTo position={flyTarget.position} zoom={flyTarget.zoom} />}
                            <MarkerClusterGroup
                                chunkedLoading
                                maxClusterRadius={45}
                                spiderfyOnMaxZoom={false}
                                showCoverageOnHover={false}
                                iconCreateFunction={createClusterIcon}
                            >
                                {zipGroups.map((group) => {
                                    const isMulti = group.facilities.length > 1;
                                    const isHighlighted = group.facilities.some(f => f.LicenseNumber === selectedId);

                                    const icon = isMulti
                                        ? createZipGroupIcon(group.facilities.length, isHighlighted)
                                        : (isHighlighted ? highlightIcon : defaultIcon);

                                    return (
                                        <Marker
                                            key={group.zip}
                                            position={[group.lat, group.lon]}
                                            icon={icon}
                                            ref={(ref) => { if (ref) { markerRefs.current[group.zip] = ref; ref.options.agencyCount = group.facilities.length; } }}
                                        >
                                            <Popup maxWidth={320} minWidth={220}>
                                                {isMulti ? (
                                                    <div className="map-popup map-popup-group">
                                                        <div className="map-popup-group-header">
                                                            <strong>{group.facilities.length} agencies in 5-digit zip code {group.zip}</strong>
                                                            {group.facilities[0].City && (
                                                                <div className="map-popup-row">
                                                                    📍 {group.facilities[0].City}
                                                                    {group.facilities[0].County ? `, ${group.facilities[0].County} County` : ''}
                                                                </div>
                                                            )}
                                                        </div>
                                                        <ul className="map-popup-agency-list">
                                                            {group.facilities.map(f => (
                                                                <li key={f.LicenseNumber} className={f.LicenseNumber === selectedId ? 'map-popup-agency-selected' : ''}>
                                                                    <a href={`${BASE_URL}agency.html?id=${encodeURIComponent(f.agencyId || f.LicenseNumber)}`}>
                                                                        {f.AgencyName || 'Unknown'}
                                                                    </a>
                                                                    <span className="map-popup-agency-meta">
                                                                        {f.LicenseNumber && <span className="map-popup-agency-license">#{f.LicenseNumber}</span>}
                                                                        {f.AgencyType && <span className="map-popup-agency-type">{f.AgencyType}</span>}
                                                                    </span>
                                                                </li>
                                                            ))}
                                                        </ul>
                                                        <a className="map-popup-zip-link" href={`${BASE_URL}?zip=${encodeURIComponent(group.zip)}`}>
                                                            View all agencies in zip {group.zip} →
                                                        </a>
                                                        <div className="map-popup-approx"><span aria-hidden="true">📌 </span>Marker is at the center of this 5-digit zip code area.</div>
                                                    </div>
                                                ) : (
                                                    <div className="map-popup">
                                                        <strong>
                                                            <a href={`${BASE_URL}agency.html?id=${encodeURIComponent(group.facilities[0].agencyId || group.facilities[0].LicenseNumber)}`}>
                                                                {group.facilities[0].AgencyName || 'Unknown'}
                                                            </a>
                                                        </strong>
                                                        {group.facilities[0].AgencyType && <div className="map-popup-row">{group.facilities[0].AgencyType}</div>}
                                                        {group.facilities[0].City && <div className="map-popup-row">📍 {group.facilities[0].City}{group.facilities[0].County ? `, ${group.facilities[0].County} County` : ''}</div>}
                                                        {group.facilities[0].ZipCode && <div className="map-popup-row">Zip: {group.facilities[0].ZipCode}</div>}
                                                        <div className="map-popup-row">License: {group.facilities[0].LicenseStatus}</div>
                                                        <div className="map-popup-approx"><span aria-hidden="true">📌 </span>Location shown is the center of 5-digit zip code area, not an exact address.</div>
                                                    </div>
                                                )}
                                            </Popup>
                                        </Marker>
                                    );
                                })}
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
