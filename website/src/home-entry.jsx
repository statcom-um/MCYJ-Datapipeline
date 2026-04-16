import React from 'react';
import { createRoot } from 'react-dom/client';
import { HomePage } from './pages/HomePage.jsx';
import './styles/common.css';

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<HomePage />);