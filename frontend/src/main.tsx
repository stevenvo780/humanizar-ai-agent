import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './SiteRouter';
import './styles.css';

const root = document.getElementById('root');
if (!root) throw new Error('No se encontró el contenedor de la aplicación.');
ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
