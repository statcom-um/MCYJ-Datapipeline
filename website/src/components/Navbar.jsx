import React, { useState } from 'react';
import { getBaseUrl } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

const NAV_LINKS = [
    { label: 'Agency View', href: `${BASE_URL}` },
    { label: 'Documents', href: `${BASE_URL}documents.html` },
    { label: 'Agency Counts', href: `${BASE_URL}facilities.html` },
    { label: 'Keywords', href: `${BASE_URL}keywords.html` },
    { label: 'Map', href: `${BASE_URL}map.html` },
    { label: 'AI Methodology', href: `${BASE_URL}ai-methodology.html` },
];

function isActive(href) {
    const path = window.location.pathname;
    // Dashboard: active on index.html or root path
    if (href === BASE_URL || href === `${BASE_URL}index.html`) {
        return path === BASE_URL || path === `${BASE_URL}index.html` || path.endsWith('/');
    }
    return path.endsWith(href.replace(BASE_URL, '/'));
}

export function Navbar() {
    const [menuOpen, setMenuOpen] = useState(false);

    return (
        <nav className="navbar">
            <div className="navbar-inner">
                <a href={BASE_URL} className="navbar-brand">MCYJ Dashboard</a>
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
