import React, { useState } from 'react';
import { getBaseUrl } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

const NAV_LINKS = [
    { label: 'Home', href: `${BASE_URL}` },
    { label: 'Agency View', href: `${BASE_URL}dashboard.html` },
    { label: 'Documents', href: `${BASE_URL}documents.html` },
    { label: 'Agency Counts', href: `${BASE_URL}facilities.html` },
    { label: 'Keywords', href: `${BASE_URL}keywords.html` },
    { label: 'Map', href: `${BASE_URL}map.html` },
    { label: 'AI Methodology', href: `${BASE_URL}ai-methodology.html` },
];

function isActive(href) {
    const path = window.location.pathname;
    const page = path.split('/').pop();

    if (href === BASE_URL)                    return page === 'index.html' || page === '';
    if (href.endsWith('dashboard.html'))      return page === 'dashboard.html';
    if (href.endsWith('documents.html'))      return page === 'documents.html';
    if (href.endsWith('facilities.html'))     return page === 'facilities.html';
    if (href.endsWith('keywords.html'))       return page === 'keywords.html';
    if (href.endsWith('map.html'))            return page === 'map.html';
    if (href.endsWith('ai-methodology.html')) return page === 'ai-methodology.html';
    return false;
}

export function Navbar() {
    const [menuOpen, setMenuOpen] = useState(false);

    return (
        <nav className="navbar">
            <div className="navbar-inner">
                {/* MCYJ Brand — left side */}
                <a href={`${BASE_URL}home.html`} className="navbar-brand">
                    <span className="navbar-brand-m">M</span>
                    <span className="navbar-brand-c">C</span>
                    <span className="navbar-brand-y">Y</span>
                    <span className="navbar-brand-j">J</span>
                    <span className="navbar-brand-text">Dashboard</span>
                </a>

                {/* Hamburger — mobile only */}
                <button
                    className="navbar-hamburger"
                    onClick={() => setMenuOpen(!menuOpen)}
                    aria-label="Toggle navigation"
                >
                    <span className={`hamburger-icon ${menuOpen ? 'open' : ''}`}>
                        <span></span>
                        <span></span>
                        <span></span>
                    </span>
                </button>

                {/* Nav links — right side */}
                <div className={`navbar-links ${menuOpen ? 'open' : ''}`}>
                    {NAV_LINKS.map(link => (
                        <a
                            key={link.label}
                            href={link.href}
                            className={`navbar-link ${isActive(link.href) ? 'active' : ''}`}
                            onClick={() => setMenuOpen(false)}
                        >
                            {link.label}
                        </a>
                    ))}
                </div>
            </div>
        </nav>
    );
}

export default Navbar;