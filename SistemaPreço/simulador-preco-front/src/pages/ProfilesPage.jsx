// src/pages/ProfilesPage.jsx
import { useEffect, useState } from 'react';
import api from '../api';
import '../styles/ProfilesPage.css';

const emptyForm = {
  name: '',
  desp_adm: '',
  desp_log: '',
  desp_op: '',
  desp_com: '',
  taxas: '',
  imposto: '',
  lucro: '',
  is_default: false,
};

function ProfilesPage() {
  const [profiles, setProfiles] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(false);

  async function loadProfiles() {
    try {
      setLoading(true);
      const res = await api.get('/profiles');
      setProfiles(res.data);
    } catch (err) {
      console.error(err);
      alert('Erro ao carregar perfis');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProfiles();
  }, []);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  }

  function handleEdit(profile) {
    setEditing(profile);
    setForm({
      name: profile.name || '',
      desp_adm: profile.desp_adm ?? '',
      desp_log: profile.desp_log ?? '',
      desp_op: profile.desp_op ?? '',
      desp_com: profile.desp_com ?? '',
      taxas: profile.taxas ?? '',
      imposto: profile.imposto ?? '',
      lucro: profile.lucro ?? '',
      is_default: profile.is_default ?? false,
    });
  }

  function handleCancel() {
    setEditing(null);
    setForm(emptyForm);
  }

  async function handleDelete(id) {
    if (!window.confirm('Deseja excluir este perfil?')) return;

    try {
      await api.delete(`/profiles/${id}`);
      await loadProfiles();
    } catch (err) {
      console.error(err);
      alert('Erro ao excluir perfil');
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();

    const payload = {
      ...form,
      desp_adm: form.desp_adm === '' ? 0 : Number(form.desp_adm),
      desp_log: form.desp_log === '' ? 0 : Number(form.desp_log),
      desp_op:  form.desp_op  === '' ? 0 : Number(form.desp_op),
      desp_com: form.desp_com === '' ? 0 : Number(form.desp_com),
      taxas:    form.taxas    === '' ? 0 : Number(form.taxas),
      imposto:  form.imposto  === '' ? 0 : Number(form.imposto),
      lucro:    form.lucro    === '' ? 0 : Number(form.lucro),
    };

    try {
      if (editing) {
        await api.put(`/profiles/${editing.id}`, payload);
      } else {
        await api.post('/profiles', payload);
      }
      handleCancel();
      await loadProfiles();
    } catch (err) {
      console.error(err);
      alert('Erro ao salvar perfil');
    }
  }

  return (
    <div className="profiles-page">
      <h2>Perfis de Precificação</h2>
      <p>Cadastre diferentes conjuntos de percentuais de despesas, impostos e lucro.</p>

      <form className="profiles-form" onSubmit={handleSubmit}>
        <div className="profiles-form-row">
          <div className="profiles-form-group">
            <label>Nome do perfil</label>
            <input
              name="name"
              value={form.name}
              onChange={handleChange}
              required
              placeholder="Ex: Padrão, Atacado, Delivery"
            />
          </div>

          <div className="profiles-form-group checkbox">
            <label>
              <input
                type="checkbox"
                name="is_default"
                checked={form.is_default}
                onChange={handleChange}
              />
              Perfil padrão
            </label>
            <small>Usado automaticamente quando nenhum perfil é escolhido no simulador.</small>
          </div>
        </div>

        <div className="profiles-grid">
          {[
            ['desp_adm', 'Desp. administrativas (%)'],
            ['desp_log', 'Desp. logísticas (%)'],
            ['desp_op',  'Desp. operacionais (%)'],
            ['desp_com', 'Desp. comerciais (%)'],
            ['taxas',    'Taxas (%)'],
            ['imposto',  'Impostos (%)'],
            ['lucro',    'Lucro (%)'],
          ].map(([field, label]) => (
            <div key={field} className="profiles-form-group small">
              <label>{label}</label>
              <input
                type="number"
                step="0.01"
                name={field}
                value={form[field]}
                onChange={handleChange}
              />
            </div>
          ))}
        </div>

        <div className="profiles-actions">
          <button type="submit" className="primary">
            {editing ? 'Salvar alterações' : 'Criar perfil'}
          </button>
          {editing && (
            <button type="button" onClick={handleCancel}>
              Cancelar edição
            </button>
          )}
        </div>
      </form>

      <section className="profiles-list">
        <div className="profiles-list-header">
          <h3>Perfis cadastrados</h3>
         <button className="reload-button" onClick={loadProfiles} disabled={loading}>
            {loading ? 'Atualizando...' : 'Recarregar'}
          </button>
        </div>

        <table className="profiles-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nome</th>
              <th>Desp. Adm</th>
              <th>Log</th>
              <th>Op</th>
              <th>Com</th>
              <th>Taxas</th>
              <th>Imposto</th>
              <th>Lucro</th>
              <th>Padrão</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {profiles.length === 0 && (
              <tr>
                <td colSpan="11" style={{ textAlign: 'center' }}>
                  Nenhum perfil cadastrado.
                </td>
              </tr>
            )}
            {profiles.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.name}</td>
                <td>{p.desp_adm}%</td>
                <td>{p.desp_log}%</td>
                <td>{p.desp_op}%</td>
                <td>{p.desp_com}%</td>
                <td>{p.taxas}%</td>
                <td>{p.imposto}%</td>
                <td>{p.lucro}%</td>
                <td>{p.is_default ? 'Sim' : 'Não'}</td>
                <td>
                  <button onClick={() => handleEdit(p)}>Editar</button>
                  <button className="danger" onClick={() => handleDelete(p.id)}>
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

export default ProfilesPage;
