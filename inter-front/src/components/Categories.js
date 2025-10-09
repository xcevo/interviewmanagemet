import React, { useEffect, useState } from 'react';
import { fetchCategories, createCategory, deleteCategory, updateCategory } from '../api/api';
import './Categories.css';

function Categories({ onSelect }) {
  const [cats, setCats] = useState([]);
  const [name, setName] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');

  const load = async () => {
    const res = await fetchCategories();
    setCats(res.data);
  };

  const add = async () => {
    if (name.trim()) {
      await createCategory(name);
      setName('');
      load();
    }
  };

  const startEdit = (cat) => {
    setEditingId(cat._id);
    setEditName(cat.name);
  };

  const saveEdit = async () => {
    await updateCategory(editingId, { name: editName });
    setEditingId(null);
    load();
  };

  const remove = async (id) => {
    if (window.confirm('Delete this category?')) {
      await deleteCategory(id);
      load();
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="categories-container">
      <h2>📁 Manage Categories</h2>

      <div className="add-form">
        <input
          type="text"
          placeholder="New category name"
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <button onClick={add}>➕ Add</button>
      </div>

      <ul className="category-list">
        {cats.map(c => (
          <li key={c._id} className="category-item">
            {editingId === c._id ? (
              <>
                <input
                  type="text"
                  value={editName}
                  onChange={e => setEditName(e.target.value)}
                />
                <button onClick={saveEdit}>💾</button>
                <button onClick={() => setEditingId(null)}>❌</button>
              </>
            ) : (
              <>
                <span onClick={() => onSelect(c)}>
   {typeof c?.name === "string" ? c.name : (c?.name?.name ?? JSON.stringify(c?.name ?? ""))}
 </span>
                <div className="actions">
                  <button onClick={() => startEdit(c)}>✏️</button>
                  <button onClick={() => remove(c._id)}>🗑️</button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Categories;
