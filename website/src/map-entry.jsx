import React from 'react';
import { createRoot } from 'react-dom/client';
import { MapPage } from './pages/MapPage.jsx';
import 'leaflet/dist/leaflet.css';
import './styles/common.css';

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<MapPage />);
