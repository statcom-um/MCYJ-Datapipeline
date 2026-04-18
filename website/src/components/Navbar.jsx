import React, { useState } from 'react';
import { getBaseUrl } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

const NAV_LINKS = [
    { label: 'Home', href: `${BASE_URL}` },
    { label: 'Agency View', href: `${BASE_URL}agencies.html` },
    { label: 'Documents', href: `${BASE_URL}documents.html` },
    { label: 'Map', href: `${BASE_URL}map.html` },
    { label: 'Crosstab', href: `${BASE_URL}crosstab.html` },
    { label: 'AI Methodology', href: `${BASE_URL}ai-methodology.html` },
];

function isActive(href) {
    const path = window.location.pathname;
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
                <a href={BASE_URL} className="navbar-brand">MI Child Welfare Agency Report Dashboard</a>

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