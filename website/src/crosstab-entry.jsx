import React from 'react';
import { createRoot } from 'react-dom/client';
import { CrosstabPage } from './pages/CrosstabPage.jsx';
import './styles/common.css';

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<CrosstabPage />);
