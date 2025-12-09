// src/App.jsx
import { useState } from 'react';
import ItemsPage from './pages/ItemsPage';
import PricingPage from './pages/PricingPage';
import RecipePage from './pages/RecipePage'; // <- NOVO
import './styles/App.css';
import ProfilesPage from './pages/ProfilesPage';

function App() {
  const [activeTab, setActiveTab] = useState('items');

  return (
    <div className="app">
      <header className="app-header">
        <h1>Simulador de Preço</h1>
      </header>

      <nav className="app-nav">
        <button
          className={activeTab === 'items' ? 'tab-button active' : 'tab-button'}
          onClick={() => setActiveTab('items')}
        >
          Itens
        </button>
        <button
          className={activeTab === 'recipes' ? 'tab-button active' : 'tab-button'}
          onClick={() => setActiveTab('recipes')}
        >
          Ficha Técnica
        </button>
        <button
          className={activeTab === 'pricing' ? 'tab-button active' : 'tab-button'}
          onClick={() => setActiveTab('pricing')}
        >
          Simulador
        </button>
        <button  
        className={activeTab === 'profile' ? 'tab-button active' : 'tab-button'}
        onClick={() => setActiveTab('profiles')}>Perfis</button>
      </nav>

      <main className="app-main">
        {activeTab === 'items' && <ItemsPage />}
        {activeTab === 'recipes' && <RecipePage />}   {/* NOVO */}
        {activeTab === 'pricing' && <PricingPage />}
         {activeTab === 'profiles' && <ProfilesPage />} 
      </main>
    </div>
  );
}

export default App;
