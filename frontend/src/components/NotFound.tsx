import React from 'react';
import { Link } from 'react-router-dom';

const NotFound: React.FC = () => (
  <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-6">
    <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
    <h2 className="text-2xl font-semibold text-gray-700 mb-2">Página não encontrada</h2>
    <p className="text-gray-500 mb-6">
      A rota que você tentou acessar não existe.
    </p>
    <Link
      to="/"
      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
    >
      Voltar ao Dashboard
    </Link>
  </div>
);

export default NotFound;
