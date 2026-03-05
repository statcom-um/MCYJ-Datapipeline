import React from 'react';
import { getBaseUrl } from '../utils/helpers.js';

/**
 * AI Caution indicator — a prominent emoji linking to the AI methodology page.
 * Use this wherever AI-generated content is displayed.
 *
 * @param {Object} props
 * @param {string} [props.label] - Optional short text label to show next to the emoji
 * @param {boolean} [props.inline] - If true, renders inline (no block wrapper)
 */
export function AiCaution({ label, inline = true }) {
    const baseUrl = getBaseUrl();
    const Tag = inline ? 'span' : 'div';
    return (
        <Tag className="ai-caution">
            <a
                href={`${baseUrl}ai-methodology.html`}
                title="Caution: AI was used here — click to learn about our methodology"
                className="ai-caution-link"
            >
                <span className="ai-caution-emoji" aria-label="AI caution">🤖⚠️</span>
                {label && <span className="ai-caution-label">{label}</span>}
            </a>
        </Tag>
    );
}

export default AiCaution;
