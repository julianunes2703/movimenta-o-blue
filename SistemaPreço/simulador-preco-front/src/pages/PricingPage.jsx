// src/pages/PricingPage.jsx
import { useEffect, useState } from 'react';
import api from '../api';
import '../styles/PricingPage.css';

function PricingPage() {
  const [items, setItems] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState('');
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [precoAtual, setPrecoAtual] = useState('');
  const [result, setResult] = useState(null);
  const [loadingItems, setLoadingItems] = useState(false);
  const [loadingSim, setLoadingSim] = useState(false);

  async function loadItems() {
    try {
      setLoadingItems(true);
      const res = await api.get('/items');
      const filtered = res.data.filter(
        (i) => i.type === 'PRODUTO_FICHA' || i.type === 'PRODUTO_UNITARIO'
      );
      setItems(filtered);
    } catch (err) {
      console.error(err);
      alert('Erro ao carregar itens');
    } finally {
      setLoadingItems(false);
    }
  }

  async function loadProfiles() {
    try {
      const res = await api.get('/profiles');
      setProfiles(res.data);
    } catch (err) {
      console.error(err);
      alert('Erro ao carregar perfis de precificação');
    }
  }

  useEffect(() => {
    loadItems();
    loadProfiles();
  }, []);

  async function handleSimulate(e) {
    e.preventDefault();
    if (!selectedItemId) {
      alert('Selecione um produto');
      return;
    }

    try {
      setLoadingSim(true);
      const payload = {
        itemId: Number(selectedItemId),
        profileId: selectedProfileId ? Number(selectedProfileId) : null,
        precoAtual: precoAtual === '' ? null : Number(precoAtual),
      };
      const res = await api.post('/pricing/simular', payload);
      setResult(res.data);
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.error || 'Erro na simulação';
      alert(msg);
    } finally {
      setLoadingSim(false);
    }
  }

  return (
    <div className="pricing-page">
      <h2>Simulador de Preço</h2>
      <p>
        Selecione um produto e um perfil de precificação para calcular o preço ideal.
      </p>

      <form className="pricing-form" onSubmit={handleSimulate}>
        <div className="pricing-form-row">
          <div className="pricing-form-group">
            <label>Produto</label>
            <select
              value={selectedItemId}
              onChange={(e) => setSelectedItemId(e.target.value)}
            >
              <option value="">Selecione...</option>
              {items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} ({item.type})
                </option>
              ))}
            </select>
          </div>

          <div className="pricing-form-group">
            <label>Perfil de precificação</label>
            <select
              value={selectedProfileId}
              onChange={(e) => setSelectedProfileId(e.target.value)}
            >
              <option value="">Padrão (default)</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.is_default ? '(padrão)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="pricing-form-group">
            <label>Preço atual (opcional)</label>
            <input
              type="number"
              value={precoAtual}
              onChange={(e) => setPrecoAtual(e.target.value)}
              step="0.01"
              min="0"
              placeholder="Ex: 20.00"
            />
          </div>
        </div>

        <button type="submit" className="pricing-button" disabled={loadingSim}>
          {loadingSim ? 'Calculando...' : 'Simular'}
        </button>
      </form>

      {result && (
        <section className="pricing-result">
          <h3>Resultado</h3>

          <div className="pricing-result-grid">
            <div className="result-card">
              <span className="label">Produto</span>
              <span className="value">{result.nome}</span>
            </div>
            <div className="result-card">
              <span className="label">Perfil</span>
              <span className="value">{result.profileName}</span>
            </div>
            <div className="result-card">
              <span className="label">Custo</span>
              <span className="value">
                R$ {Number(result.custo).toFixed(2)}
              </span>
            </div>
            <div className="result-card">
              <span className="label">Preço ideal</span>
              <span className="value">
                R$ {Number(result.precoIdeal).toFixed(2)}
              </span>
            </div>
            {result.precoAtual != null && (
              <>
                <div className="result-card">
                  <span className="label">Preço atual</span>
                  <span className="value">
                    R$ {Number(result.precoAtual).toFixed(2)}
                  </span>
                </div>
                <div className="result-card">
                  <span className="label">Diferença de preço</span>
                  <span className="value">
                    R$ {Number(result.difPreco).toFixed(2)}
                  </span>
                </div>
                <div className="result-card">
                  <span className="label">Markup ideal</span>
                  <span className="value">
                    {(Number(result.markupDesejado) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="result-card">
                  <span className="label">Markup atual</span>
                  <span className="value">
                    {(Number(result.markupAtual) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="result-card">
                  <span className="label">Diferença de margem (p.p.)</span>
                  <span className="value">
                    {(Number(result.difMargemPP) * 100).toFixed(1)} p.p.
                  </span>
                </div>
              </>
            )}
          </div>

          {/* NOVO: tabela com os percentuais e valores */}
          {result.components && (
            <div className="pricing-components">
              <h4>Componentes do preço ideal</h4>
              <table>
                <thead>
                  <tr>
                    <th>Componente</th>
                    <th>Percentual</th>
                    <th>Valor em R$</th>
                  </tr>
                </thead>
                <tbody>
                  {result.components.map((c) => (
                    <tr key={c.key}>
                      <td>{c.label}</td>
                      <td>{c.percent.toFixed(2)}%</td>
                      <td>R$ {Number(c.value).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="components-total">
                Soma dos percentuais: {result.totalPercentual.toFixed(2)}%
              </p>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default PricingPage;
