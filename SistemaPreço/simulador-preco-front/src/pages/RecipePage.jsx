// src/pages/RecipePage.jsx
import { useEffect, useState } from 'react';
import api from '../api';
import '../styles/RecipePage.css';

const emptyLine = {
  ingredientId: '',
  ingredientName: '',
  unit: '',
  unitCost: 0,
  qty: '',
  lineCost: 0,
};

function RecipePage() {
  const [products, setProducts] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [lines, setLines] = useState([ { ...emptyLine } ]);
  const [wasteFactor, setWasteFactor] = useState(1.15); // 1,15 = +15% desperdício
  const [saving, setSaving] = useState(false);

  // carrega itens do banco
  useEffect(() => {
    async function loadItems() {
      try {
        const res = await api.get('/items');
        const all = res.data || [];

        const ingr = all.filter((i) => i.type === 'INGREDIENTE');
        const prods = all.filter((i) => i.type === 'PRODUTO_FICHA');

        setIngredients(ingr);
        setProducts(prods);
      } catch (err) {
        console.error(err);
        alert('Erro ao carregar itens para ficha técnica');
      }
    }

    loadItems();
  }, []);

  // recalcula custo de uma linha
  function recalcLine(line) {
    const qtyNumber = line.qty === '' ? 0 : Number(line.qty);
    const costNumber = Number(line.unitCost || 0);
    return {
      ...line,
      lineCost: qtyNumber * costNumber,
    };
  }

  // recalcula tudo
  function recalcAllLines(newLines) {
    return newLines.map(recalcLine);
  }

  function handleChangeIngredient(index, ingredientId) {
    const ingredient = ingredients.find((i) => String(i.id) === String(ingredientId));
    setLines((prev) => {
      const copy = [...prev];
      const line = { ...copy[index] };

      line.ingredientId = ingredientId;
      line.ingredientName = ingredient ? ingredient.name : '';
      line.unit = ingredient ? ingredient.unit : '';
      line.unitCost = ingredient ? Number(ingredient.cost_per_unit) : 0;

      copy[index] = recalcLine(line);
      return copy;
    });
  }

  function handleChangeQty(index, qty) {
    setLines((prev) => {
      const copy = [...prev];
      const line = { ...copy[index], qty };
      copy[index] = recalcLine(line);
      return copy;
    });
  }

  function handleAddLine() {
    setLines((prev) => [...prev, { ...emptyLine }]);
  }

  function handleRemoveLine(index) {
    setLines((prev) => prev.filter((_, i) => i !== index));
  }

  const totalCost = lines.reduce((sum, line) => sum + Number(line.lineCost || 0), 0);
  const wasteFactorNumber = Number(wasteFactor || 0);
  const totalWithWaste = totalCost * (isNaN(wasteFactorNumber) ? 1 : wasteFactorNumber);

  async function handleSave(e) {
    e.preventDefault();

    if (!selectedProductId) {
      alert('Selecione um produto final para esta ficha técnica.');
      return;
    }

    const usedLines = lines.filter(
      (l) => l.ingredientId && Number(l.qty || 0) > 0
    );

    if (usedLines.length === 0) {
      alert('Adicione pelo menos um ingrediente com quantidade.');
      return;
    }

    const payload = {
      item_id: Number(selectedProductId),
      yield_qty: 1, // 1 porção/unidade
      yield_unit: 'porção',
      itens: usedLines.map((l) => ({
        item_id: Number(l.ingredientId),
        qty: Number(l.qty),
      })),
    };

    try {
      setSaving(true);
      await api.post('/recipes', payload);
      alert('Ficha técnica salva e custo do produto atualizado!');
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.error || 'Erro ao salvar ficha técnica';
      alert(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="recipe-page">
      <h2>Ficha Técnica de Produto</h2>
      <p>
        Monte o produto selecionando os insumos cadastrados, informe a quantidade
        de cada um e veja o custo total e o custo com desperdício.
      </p>

      <form className="recipe-form" onSubmit={handleSave}>
        <div className="recipe-header-row">
          <div className="recipe-form-group">
            <label>Produto (produto final)</label>
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
            >
              <option value="">Selecione...</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <small>
              Cadastre o produto como <strong>Produto com ficha técnica</strong> na aba
              Itens.
            </small>
          </div>

          <div className="recipe-form-group small">
            <label>Fator de desperdício</label>
            <input
              type="number"
              step="0.01"
              value={wasteFactor}
              onChange={(e) => setWasteFactor(e.target.value)}
            />
            <small>Ex: 1.15 = custo total × 1,15 (15% de desperdício)</small>
          </div>
        </div>

        {/* Tabela de ingredientes */}
        <div className="recipe-table-wrapper">
          <table className="recipe-table">
            <thead>
              <tr>
                <th>Ingrediente</th>
                <th>Unidade</th>
                <th>Custo/unidade</th>
                <th>Quantidade na receita</th>
                <th>Preço un (linha)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => (
                <tr key={index}>
                  <td>
                    <select
                      value={line.ingredientId}
                      onChange={(e) =>
                        handleChangeIngredient(index, e.target.value)
                      }
                    >
                      <option value="">Selecione...</option>
                      {ingredients.map((ing) => (
                        <option key={ing.id} value={ing.id}>
                          {ing.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>{line.unit || '-'}</td>
                  <td>
                    {line.ingredientId
                      ? `R$ ${Number(line.unitCost).toFixed(2)}`
                      : '-'}
                  </td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      step="0.0001"
                      value={line.qty}
                      onChange={(e) => handleChangeQty(index, e.target.value)}
                      placeholder="Ex: 0.3 (kg), 0.05..."
                    />
                  </td>
                  <td>
                    {line.ingredientId
                      ? `R$ ${Number(line.lineCost || 0).toFixed(2)}`
                      : '-'}
                  </td>
                  <td>
                    {lines.length > 1 && (
                      <button
                        type="button"
                        className="recipe-remove-btn"
                        onClick={() => handleRemoveLine(index)}
                      >
                        Remover
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              <tr>
                <td colSpan="6">
                  <button
                    type="button"
                    className="recipe-add-btn"
                    onClick={handleAddLine}
                  >
                    + Adicionar ingrediente
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Totais */}
        <div className="recipe-totals">
          <div className="total-card">
            <span className="label">Custo total (soma dos preços un)</span>
            <span className="value">R$ {totalCost.toFixed(2)}</span>
          </div>
          <div className="total-card">
            <span className="label">Custo com desperdício</span>
            <span className="value">R$ {totalWithWaste.toFixed(2)}</span>
          </div>
        </div>

        <div className="recipe-actions">
          <button type="submit" disabled={saving}>
            {saving ? 'Salvando...' : 'Salvar ficha técnica'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default RecipePage;
