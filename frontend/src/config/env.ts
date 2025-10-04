/**
 * Environment Configuration
 * Handles environment variables for both Vite and Jest
 */

// Check if we're in a browser environment with import.meta
const isVite = typeof import.meta !== 'undefined' && import.meta.env;

// In Jest/Node environment, use process.env
// In Vite/Browser environment, use import.meta.env
export const API_BASE_URL = isVite
  ? import.meta.env.VITE_API_URL || 'http://localhost:8000'
  : (typeof process !== 'undefined' && process.env?.VITE_API_URL) || 'http://localhost:8000';
