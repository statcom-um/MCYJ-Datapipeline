import React from 'react';
import { createRoot } from 'react-dom/client';
import { DocumentsPage } from './pages/DocumentsPage.jsx';
import './styles/common.css';

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<DocumentsPage />);
