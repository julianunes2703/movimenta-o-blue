// src/components/ItemForm.jsx
import { useEffect, useState } from 'react';
import '../styles/ItemForm.css';

const initialForm = {
  name: '',
  type: 'INGREDIENTE',
  unit: 'kg',
  cost_per_unit: '',
  yield_qty: '',
  is_active: true,
};

function ItemForm({ onSave, editingItem, onCancelEdit }) {
  const [form, setForm] = useState(initialForm);

  useEffect(() => {
    if (editingItem) {
      setForm({
        name: editingItem.name || '',
        type: editingItem.type || 'INGREDIENTE',
        unit: editingItem.unit || 'kg',
        cost_per_unit: editingItem.cost_per_unit ?? '',
        yield_qty: editingItem.yield_qty ?? '',
        is_active: editingItem.is_active ?? true,
      });
    } else {
      setForm(initialForm);
    }
  }, [editingItem]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    const payload = {
      ...form,
      cost_per_unit: form.cost_per_unit === '' ? 0 : Number(form.cost_per_unit),
      yield_qty:
        form.yield_qty === '' || form.yield_qty === null
          ? null
          : Number(form.yield_qty),
    };
    onSave(payload);
  }

  function handleReset() {
    if (editingItem) {
      onCancelEdit();
    } else {
      setForm(initialForm);
    }
  }

  return (
    <form className="item-form" onSubmit={handleSubmit}>
      <div className="item-form-row">
        <div className="item-form-group">
          <label>Nome</label>
          <input
            name="name"
            value={form.name}
            onChange={handleChange}
            required
            placeholder="Ex: Frango, Strogonoff, Coca 350ml"
          />
        </div>

        <div className="item-form-group">
          <label>Tipo</label>
          <select name="type" value={form.type} onChange={handleChange}>
            <option value="INGREDIENTE">Insumo</option>
            <option value="PRODUTO_FICHA">Produto com ficha técnica</option>
            <option value="PRODUTO_UNITARIO">Produto unitário</option>
          </select>
        </div>

        <div className="item-form-group">
          <label>Unidade padrão</label>
          <input
            name="unit"
            value={form.unit}
            onChange={handleChange}
            placeholder="kg, L, un..."
          />
        </div>
      </div>

      <div className="item-form-row">
        <div className="item-form-group">
          <label>Custo por unidade</label>
          <input
            type="number"
            name="cost_per_unit"
            value={form.cost_per_unit}
            onChange={handleChange}
            step="0.0001"
            min="0"
          />
          <small>
            Para insumos e produtos unitários. Produtos com ficha podem ser
            atualizados pelo custo da receita.
          </small>
        </div>

        <div className="item-form-group">
          <label>Rendimento (opcional)</label>
          <input
            type="number"
            name="yield_qty"
            value={form.yield_qty}
            onChange={handleChange}
            step="0.0001"
            min="0"
          />
          <small>Ex: número de porções que este item rende.</small>
        </div>

        <div className="item-form-group item-form-checkbox">
          <label>
            <input
              type="checkbox"
              name="is_active"
              checked={form.is_active}
              onChange={handleChange}
            />
            Ativo
          </label>
        </div>
      </div>

      <div className="item-form-actions">
        <button type="submit" className="primary">
          {editingItem ? 'Salvar alterações' : 'Cadastrar'}
        </button>
        <button type="button" onClick={handleReset}>
          {editingItem ? 'Cancelar edição' : 'Limpar'}
        </button>
      </div>
    </form>
  );
}

export default ItemForm;
