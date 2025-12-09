// src/pages/ItemsPage.jsx
import { useEffect, useState } from 'react';
import api from '../api';
import ItemForm from '../components/ItemForm';
import '../styles/ItemsPage.css';

function ItemsPage() {
  const [items, setItems] = useState([]);
  const [editingItem, setEditingItem] = useState(null);
  const [loading, setLoading] = useState(false);

  async function loadItems() {
    try {
      setLoading(true);
      const res = await api.get('/items');
      setItems(res.data);
    } catch (err) {
      console.error(err);
      alert('Erro ao carregar itens');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadItems();
  }, []);

  function handleEdit(item) {
    setEditingItem(item);
  }

  function handleClearEdit() {
    setEditingItem(null);
  }

async function handleDelete(id) {
  if (!confirm("Tem certeza que deseja excluir este item?")) return;

  try {
    await api.delete(`/items/${id}`);
    alert("Item excluído com sucesso!");
    loadItems();
  } catch (err) {
    alert("Erro ao excluir item");
  }
}


  async function handleSave(formData) {
    try {
      if (editingItem) {
        await api.put(`/items/${editingItem.id}`, formData);
      } else {
        await api.post('/items', formData);
      }
      handleClearEdit();
      await loadItems();
    } catch (err) {
      console.error(err);
      alert('Erro ao salvar item');
    }
  }

  return (
    <div className="items-page">
      <div className="items-header">
        <h2>Cadastro de Itens</h2>
        <p>
          Cadastre insumos, produtos com ficha técnica e produtos unitários
          (revenda).
        </p>
      </div>

      <section className="items-form-section">
        <ItemForm onSave={handleSave} editingItem={editingItem} onCancelEdit={handleClearEdit} />
      </section>

      <section className="items-list-section">
        <div className="items-list-header">
          <h3>Itens cadastrados</h3>
          <button className="reload-button" onClick={loadItems} disabled={loading}>
            {loading ? 'Atualizando...' : 'Recarregar'}
          </button>
        </div>

        <table className="items-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nome</th>
              <th>Tipo</th>
              <th>Unidade</th>
              <th>Custo/unid</th>
              <th>Ativo</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center' }}>
                  Nenhum item cadastrado.
                </td>
              </tr>
            )}
            {items.map((item) => (
              <tr key={item.id} className={!item.is_active ? 'inactive-row' : ''}>
                <td>{item.id}</td>
                <td>{item.name}</td>
                <td>{item.type}</td>
                <td>{item.unit}</td>
                <td>R$ {Number(item.cost_per_unit).toFixed(2)}</td>
                <td>{item.is_active ? 'Sim' : 'Não'}</td>
                <td>
                  <button className="table-button" onClick={() => handleEdit(item)}>
                    Editar
                  </button>
                      <button className="delete-btn" onClick={() => handleDelete(item.id)}>
                        Excluir
                      </button>

                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export default ItemsPage;
