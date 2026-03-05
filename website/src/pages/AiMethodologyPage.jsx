import React, { useState, useEffect } from 'react';
import { Header, Loading, Error } from '../components/index.js';
import { AiCaution } from '../components/AiCaution.jsx';
import { getBaseUrl } from '../utils/helpers.js';

const BASE_URL = getBaseUrl();

/**
 * Friendly display names for theming prompt files
 */
const THEMING_DISPLAY_NAMES = {
    sir_theming: 'SIR Severity Classification Criteria',
    staffing_theming: 'Staffing Violation Analysis Prompt'
};

const QUERY_DISPLAY_NAMES = {
    sir_summary: 'SIR Summary Generation',
    violation_level: 'Violation Severity Classification'
};

/**
 * AiMethodologyPage — describes how AI is used in this project,
 * including model selection, prompting strategy, and the actual prompts.
 */
export function AiMethodologyPage() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [methodology, setMethodology] = useState(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const response = await fetch(`${BASE_URL}data/ai_methodology.json`);
            if (!response.ok) {
                throw new Error(`Failed to load AI methodology data: ${response.statusText}`);
            }
            const data = await response.json();
            setMethodology(data);
            setLoading(false);
        } catch (err) {
            console.error('Error loading AI methodology data:', err);
            setError(`Failed to load data: ${err.message}`);
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <>
                <Header
                    title="AI Methodology"
                    subtitle="Michigan Child Welfare Licensing Dashboard"
                />
                <div className="container">
                    <a href={`${BASE_URL}`} className="back-link">← Back to Dashboard</a>
                    <Loading message="Loading methodology data..." />
                </div>
            </>
        );
    }

    if (error) {
        return (
            <>
                <Header
                    title="AI Methodology"
                    subtitle="Michigan Child Welfare Licensing Dashboard"
                />
                <div className="container">
                    <a href={`${BASE_URL}`} className="back-link">← Back to Dashboard</a>
                    <Error message={error} />
                </div>
            </>
        );
    }

    const modelName = methodology?.model || 'Unknown';
    const themingPrompts = methodology?.theming_prompts || {};
    const queryTemplates = methodology?.query_templates || {};

    return (
        <>
            <Header
                title="AI Methodology"
                subtitle="Michigan Child Welfare Licensing Dashboard"
            />
            <div className="container">
                <a href={`${BASE_URL}`} className="back-link">← Back to Dashboard</a>

                <div className="methodology-container">
                    {/* Intro */}
                    <div className="methodology-intro">
                        <h2>
                            <AiCaution />
                            {' '}How We Use AI
                        </h2>
                        <p>
                            This dashboard uses artificial intelligence to help analyze child welfare licensing documents.
                            Whenever you see the <AiCaution /> symbol on this site, it means AI was used to generate
                            that content. We believe in full transparency about our process.
                        </p>
                        <p>
                            <strong>AI-generated content may contain errors.</strong> All outputs should be verified
                            against original source documents before being relied upon for decision-making.
                        </p>
                    </div>

                    {/* Model Info */}
                    <div className="methodology-section">
                        <h3>🧠 Model Selection</h3>
                        <div className="methodology-model-card">
                            <div className="methodology-model-name">{modelName}</div>
                            <p>
                                We use the <strong>{modelName}</strong> model via the OpenRouter API. This model was
                                selected for its strong performance on document analysis and classification tasks,
                                while maintaining cost-effectiveness for large-scale processing.
                            </p>
                            <p>
                                All queries are sent through the OpenRouter API, which provides access to the model
                                with prompt caching to reduce costs for repeated document structures.
                            </p>
                        </div>
                    </div>

                    {/* AI Tasks */}
                    <div className="methodology-section">
                        <h3>📋 What AI Does on This Site</h3>
                        <div className="methodology-tasks">
                            <div className="methodology-task-card">
                                <h4>1. SIR Summary Generation</h4>
                                <p>
                                    Special Investigation Reports (SIRs) are summarized by AI to provide a quick
                                    overview of what happened and whether violations were substantiated.
                                </p>
                            </div>
                            <div className="methodology-task-card">
                                <h4>2. Violation Severity Classification</h4>
                                <p>
                                    For SIRs with substantiated violations, AI classifies the severity as
                                    <strong> low</strong>, <strong> moderate</strong>, or <strong> severe</strong> based
                                    on a defined categorization framework (see prompts below).
                                </p>
                            </div>
                            <div className="methodology-task-card">
                                <h4>3. Staffing Violation Analysis</h4>
                                <p>
                                    AI determines whether violations were primarily caused by staffing issues
                                    such as understaffing, ratio gaps, or coverage failures, with a confidence rating.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Theming Prompts */}
                    {Object.keys(themingPrompts).length > 0 && (
                        <div className="methodology-section">
                            <h3>📝 Classification Criteria (Theming Prompts)</h3>
                            <p className="methodology-section-desc">
                                These are the exact criteria provided to the AI model for classifying documents.
                                They are maintained in our codebase and automatically injected into this page during each build.
                            </p>
                            {Object.entries(themingPrompts).map(([key, content]) => (
                                <div key={key} className="methodology-prompt-block">
                                    <h4>{THEMING_DISPLAY_NAMES[key] || key}</h4>
                                    <pre className="methodology-prompt-text">{content}</pre>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Query Templates */}
                    {Object.keys(queryTemplates).length > 0 && (
                        <div className="methodology-section">
                            <h3>💬 Query Templates</h3>
                            <p className="methodology-section-desc">
                                These are the prompt templates sent to the AI model for each analysis task.
                                Document text is inserted at the indicated placeholder positions.
                            </p>
                            {Object.entries(queryTemplates).map(([key, data]) => (
                                <div key={key} className="methodology-prompt-block">
                                    <h4>{data.description || QUERY_DISPLAY_NAMES[key] || key}</h4>
                                    <pre className="methodology-prompt-text">{data.prompt}</pre>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Data Source */}
                    <div className="methodology-section">
                        <h3>🔗 Data Source</h3>
                        <p>
                            All documents analyzed come from the Michigan Department of Licensing and Regulatory Affairs
                            (LARA) public API. Raw documents are available for verification on the individual document pages.
                        </p>
                    </div>
                </div>
            </div>

            <div id="commitHash" style={{ textAlign: 'center', padding: '20px', color: '#999', fontSize: '0.8em', fontFamily: 'monospace' }}>
                Version: {__COMMIT_HASH__}
            </div>
        </>
    );
}

export default AiMethodologyPage;
