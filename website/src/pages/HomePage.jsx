import React from 'react';
import { Navbar } from '../components/Navbar.jsx';
import { getBaseUrl } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

const FEATURES = [
    {
        icon: '🏢',
        title: 'Agency Directory',
        desc: 'Browse all licensed Michigan child welfare agencies. Filter by type, county, license status, and more.',
        href: `${BASE_URL}agencies.html`,
        label: 'Browse Agencies',
    },
    {
        icon: '📄',
        title: 'Document Tracking',
        desc: 'View licensing documents and Special Investigation Reports (SIRs) with AI-generated summaries.',
        href: `${BASE_URL}documents.html`,
        label: 'View Documents',
    },
    {
        icon: '🗺️',
        title: 'Interactive Map',
        desc: 'Explore the geographic distribution of agencies across Michigan by name, city, county, or zip.',
        href: `${BASE_URL}map.html`,
        label: 'Open Map',
    },
    {
        icon: '🤖',
        title: 'AI Methodology',
        desc: 'Learn how AI is used to generate summaries, severity classifications, and staffing analysis.',
        href: `${BASE_URL}ai-methodology.html`,
        label: 'Learn More',
    },
];

const STEPS = [
    {
        num: '01',
        title: 'Find an Agency',
        desc: 'Search the Agency Directory by name, ID, county, or license status.',
    },
    {
        num: '02',
        title: 'Explore Documents',
        desc: 'Read SIRs and licensing docs. AI summaries highlight key findings — always link back to the full report.',
    },
    {
        num: '03',
        title: 'View on the Map',
        desc: 'Switch to Map view to see geographic patterns and locate agencies across Michigan.',
    },
];

export function HomePage() {
    return (
        <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif", background: '#f5f5f5', minHeight: '100vh' }}>
            <Navbar />

            {/* Hero */}
            <section style={{
                background: 'linear-gradient(135deg, #2c3e50 0%, #34495e 100%)',
                color: 'white',
                padding: '72px 20px 60px',
                textAlign: 'center',
            }}>
                <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                    <h1 style={{ fontSize: 'clamp(1.4rem, 4vw, 2.4rem)', fontWeight: 700, marginBottom: '16px', lineHeight: 1.3 }}>
                        Michigan Licensed Child Welfare Agency<br />Report Dashboard
                    </h1>
                    <p style={{ fontSize: '1.1rem', opacity: 0.85, lineHeight: 1.7, maxWidth: '640px', margin: '0 auto 24px' }}>
                        A public transparency tool for exploring Michigan's child welfare agency
                        licensing documents and special investigation reports.
                    </p>
                    <p style={{ fontSize: '0.92rem', opacity: 0.7, lineHeight: 1.6, maxWidth: '640px', margin: '0 auto 36px' }}>
                        Built by STATCOM at the University of Michigan in partnership with the
                        Michigan Center for Youth Justice (MCYJ).
                    </p>

                    <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
                        <a href={`${BASE_URL}agencies.html`} style={{
                            background: '#3498db', color: 'white',
                            padding: '14px 28px', borderRadius: '8px', textDecoration: 'none',
                            fontWeight: 700, fontSize: '1rem', transition: 'opacity 0.2s',
                        }}
                            onMouseOver={e => e.target.style.opacity = '0.85'}
                            onMouseOut={e => e.target.style.opacity = '1'}
                        >
                            Explore the Dashboard →
                        </a>
                        <a href={`${BASE_URL}map.html`} style={{
                            background: 'transparent', color: 'white',
                            padding: '14px 28px', borderRadius: '8px', textDecoration: 'none',
                            fontWeight: 600, fontSize: '1rem',
                            border: '2px solid rgba(255,255,255,0.4)',
                        }}>
                            View Agency Map
                        </a>
                    </div>
                </div>
            </section>

            {/* Stats bar */}
            <section style={{ background: 'white', borderBottom: '1px solid #eee', padding: '32px 20px' }}>
                <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '24px' }}>
                    {[
                        { num: '281', label: 'Licensed Agencies' },
                        { num: '3,000+', label: 'Documents Tracked' },
                        { num: '83', label: 'Michigan Counties' },
                        { num: '100%', label: 'Public Data' },
                    ].map(s => (
                        <div key={s.label} style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '2.4rem', fontWeight: 800, color: 'var(--accent-dark)' }}>{s.num}</div>
                            <div style={{ fontSize: '0.85rem', color: '#777', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: '4px' }}>{s.label}</div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Mission */}
            <section style={{ padding: '64px 20px', background: '#fafafa' }}>
                <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '48px', alignItems: 'start' }}>
                    <div>
                        <div style={{ display: 'inline-block', background: 'var(--accent-dark)', color: 'white', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', padding: '4px 12px', borderRadius: '20px', marginBottom: '14px' }}>
                            Our Mission
                        </div>
                        <h2 style={{ fontSize: 'clamp(1.4rem, 3vw, 2rem)', fontWeight: 700, color: 'var(--text-dark)', marginBottom: '20px', lineHeight: 1.25 }}>
                            Bringing Transparency to Child Welfare Oversight
                        </h2>
                        <p style={{ color: '#555', lineHeight: 1.8, marginBottom: '16px' }}>
                            Michigan's child welfare system licenses hundreds of agencies providing
                            foster care, adoption, and residential services. When incidents occur,
                            they're documented in Special Investigation Reports (SIRs) — but reading
                            through thousands of individual files is practically impossible.
                        </p>
                        <p style={{ color: '#555', lineHeight: 1.8, marginBottom: '16px' }}>
                            This dashboard makes those documents searchable, with AI-assisted analysis
                            to surface patterns that would be hard to detect otherwise. Our goal is to
                            support advocates, researchers, journalists, and families.
                        </p>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div style={{ background: 'white', border: '1px solid #eee', borderRadius: '16px', padding: '28px', boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                                <span style={{ fontSize: '2rem' }}>🏛️</span>
                                <strong style={{ color: 'var(--text-dark)', fontSize: '1.05rem' }}>Michigan Department of Health and Human Services</strong>
                            </div>
                            <p style={{ color: '#555', lineHeight: 1.7, marginBottom: '12px', fontSize: '0.97rem' }}>
                                MDHHS oversees the licensing of child welfare agencies in Michigan.
                                Licensing documents and special investigation reports are public record.
                            </p>
                            <a href="https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/" target="_blank" rel="noopener noreferrer"
                                style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.92rem', textDecoration: 'none' }}>
                                Public Licensing Search →
                            </a>
                        </div>

                        <div style={{ background: 'white', border: '1px solid #eee', borderRadius: '16px', padding: '28px', boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                                <span style={{ fontSize: '2rem' }}>⚖️</span>
                                <strong style={{ color: 'var(--text-dark)', fontSize: '1.05rem' }}>Michigan Center for Youth Justice</strong>
                            </div>
                            <p style={{ color: '#555', lineHeight: 1.7, marginBottom: '12px', fontSize: '0.97rem' }}>
                                MCYJ works to transform Michigan's youth justice system by advocating for
                                evidence-based policies and supporting system-involved youth and their families.
                            </p>
                            <a href="https://www.miyouthjustice.org/" target="_blank" rel="noopener noreferrer"
                                style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.92rem', textDecoration: 'none' }}>
                                Visit MCYJ Website →
                            </a>
                        </div>

                        <div style={{ background: 'white', border: '1px solid #eee', borderRadius: '16px', padding: '28px', boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                                <span style={{ fontSize: '2rem' }}>🎓</span>
                                <strong style={{ color: 'var(--text-dark)', fontSize: '1.05rem' }}>STATCOM — University of Michigan</strong>
                            </div>
                            <p style={{ color: '#555', lineHeight: 1.7, marginBottom: '12px', fontSize: '0.97rem' }}>
                                Statistics in the Community (STATCOM) is a student-led consulting group
                                providing pro bono statistical analysis to nonprofits and government agencies.
                            </p>
                            <a href="https://sph.umich.edu/biostat/statcom/" target="_blank" rel="noopener noreferrer"
                                style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.92rem', textDecoration: 'none' }}>
                                Visit STATCOM Website →
                            </a>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features */}
            <section style={{ padding: '64px 20px', background: 'white' }}>
                <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
                    <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                        <div style={{ display: 'inline-block', background: 'var(--accent)', color: 'white', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', padding: '4px 12px', borderRadius: '20px', marginBottom: '14px' }}>
                            Dashboard Features
                        </div>
                        <h2 style={{ fontSize: 'clamp(1.4rem, 3vw, 2rem)', fontWeight: 700, color: 'var(--text-dark)' }}>What You Can Do</h2>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
                        {FEATURES.map(f => (
                            <a key={f.title} href={f.href} style={{ background: '#fafafa', border: '1px solid #eee', borderRadius: '12px', padding: '28px', textDecoration: 'none', display: 'block', transition: 'transform 0.2s, box-shadow 0.2s', borderTop: '3px solid var(--accent)' }}
                                onMouseOver={e => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; }}
                                onMouseOut={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}
                            >
                                <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'var(--accent-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', marginBottom: '14px' }}>
                                    {f.icon}
                                </div>
                                <h3 style={{ color: 'var(--text-dark)', fontWeight: 700, marginBottom: '8px', fontSize: '1.05rem' }}>{f.title}</h3>
                                <p style={{ color: '#555', lineHeight: 1.65, fontSize: '0.93rem', marginBottom: '14px' }}>{f.desc}</p>
                                <span style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.88rem' }}>{f.label} →</span>
                            </a>
                        ))}
                    </div>
                </div>
            </section>

            {/* How to use */}
            <section style={{ padding: '64px 20px', background: '#fafafa' }}>
                <div style={{ maxWidth: '900px', margin: '0 auto' }}>
                    <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                        <div style={{ display: 'inline-block', background: 'var(--accent-muted)', color: 'white', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', padding: '4px 12px', borderRadius: '20px', marginBottom: '14px' }}>
                            How To Use
                        </div>
                        <h2 style={{ fontSize: 'clamp(1.4rem, 3vw, 2rem)', fontWeight: 700, color: 'var(--text-dark)' }}>Getting Started</h2>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px' }}>
                        {STEPS.map(s => (
                            <div key={s.num} style={{ background: 'white', borderRadius: '12px', padding: '28px', border: '1px solid #eee', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                                <div style={{ fontSize: '2rem', fontWeight: 900, color: 'var(--accent)', marginBottom: '10px', lineHeight: 1 }}>{s.num}</div>
                                <h3 style={{ color: 'var(--text-dark)', fontWeight: 700, marginBottom: '8px', fontSize: '1rem' }}>{s.title}</h3>
                                <p style={{ color: '#666', lineHeight: 1.65, fontSize: '0.92rem' }}>{s.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section style={{
                background: 'linear-gradient(135deg, #2c3e50 0%, #34495e 100%)',
                color: 'white', padding: '64px 20px', textAlign: 'center',
            }}>
                <h2 style={{ fontSize: 'clamp(1.4rem, 3vw, 2rem)', fontWeight: 700, marginBottom: '12px' }}>
                    Ready to explore Michigan child welfare data?
                </h2>
                <p style={{ opacity: 0.85, marginBottom: '32px', fontSize: '1.05rem' }}>
                    Start with the agency directory, search the map, or dive into keyword patterns.
                </p>
                <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
                    <a href={`${BASE_URL}agencies.html`} style={{ background: 'white', color: '#2c3e50', padding: '14px 28px', borderRadius: '8px', textDecoration: 'none', fontWeight: 700 }}>
                        Open the Dashboard →
                    </a>
                    <a href={`${BASE_URL}map.html`} style={{ background: 'transparent', color: 'white', padding: '14px 28px', borderRadius: '8px', textDecoration: 'none', fontWeight: 600, border: '2px solid rgba(255,255,255,0.5)' }}>
                        View Map
                    </a>
                </div>
            </section>

            {/* Footer */}
            <footer style={{ background: '#1a252f', color: 'rgba(255,255,255,0.6)', padding: '32px 20px', textAlign: 'center', fontSize: '0.9rem', lineHeight: 1.7 }}>
                <p style={{ marginBottom: '12px' }}>
                    Built by{' '}
                    <a href="https://sph.umich.edu/biostat/statcom/" target="_blank" rel="noopener noreferrer" style={{ color: 'rgba(255,255,255,0.85)', textDecoration: 'none' }}>STATCOM</a>
                    {' '}at the University of Michigan in partnership with the{' '}
                    <a href="https://www.miyouthjustice.org/" target="_blank" rel="noopener noreferrer" style={{ color: 'rgba(255,255,255,0.85)', textDecoration: 'none' }}>Michigan Center for Youth Justice</a>.
                </p>
                <p>
                    Data from the{' '}
                    <a href="https://michildwelfarepubliclicensingsearch.michigan.gov/licagencysrch/" target="_blank" rel="noopener noreferrer" style={{ color: 'rgba(255,255,255,0.85)', textDecoration: 'none' }}>Michigan LARA Child Welfare Public Licensing Search</a>.
                    {' '}
                    <a href="https://github.com/statcom-um/MCYJ-Datapipeline" target="_blank" rel="noopener noreferrer" style={{ color: 'rgba(255,255,255,0.85)', textDecoration: 'none' }}>Source code on GitHub</a>.
                </p>
            </footer>
        </div>
    );
}

export default HomePage;
