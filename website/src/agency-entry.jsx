import React from 'react';
import { createRoot } from 'react-dom/client';
import { AgencyPage } from './pages/AgencyPage.jsx';
import './styles/common.css';

// Render the AgencyPage component
const container = document.getElementById('root');
const root = createRoot(container);
root.render(<AgencyPage />);
