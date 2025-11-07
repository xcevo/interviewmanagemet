import React, { useState, useEffect } from 'react';
import {
  fetchCriteria,
  createCriteria,
  fetchCategories,
  updateCriteria,
  deleteCriteria
} from '../api/api';
import { FaEdit, FaTrash } from 'react-icons/fa';
import './Criteria.css'; // Link your CSS here

function Criteria() {
  const [criteriaList, setCriteriaList] = useState([]);
  const [form, setForm] = useState({
    name: '',
    category: '',
    easy: 0,
    medium: 0,
    hard: 0,
    time: 0,
    passing_marks: 0,
    valid_from: '',
    valid_to: '',
  });
  const [categories, setCategories] = useState([]);
  const [editingId, setEditingId] = useState(null);

  const load = async () => {
       const res = await fetchCriteria();
   setCriteriaList(res.data);
   const cats = await fetchCategories();
   const normalized = (cats.data ?? []).map(x => ({
     ...x,
     // name kabhi object aa raha hai: { name: "…" }
     name: typeof x?.name === 'string' ? x.name : (x?.name?.name ?? String(x?.name ?? '')),
   }));
   setCategories(normalized);
    
  };

  const handleSubmit = async () => {
    if (editingId) {
      await updateCriteria(editingId, form);
      setEditingId(null);
    } else {
      await createCriteria(form);
    }
    resetForm();
    load();
  };

  const resetForm = () => {
    setForm({
      name: '',
      category: '',
      easy: 0,
      medium: 0,
      hard: 0,
      time: 0,
      passing_marks: 0,
      valid_from: '',
      valid_to: '',
    });
  };

  const handleEdit = (c) => {
    setForm({
      name: c.name,
      category: c.category?.id || '',
      easy: c.easy || 0,
      medium: c.medium || 0,
      hard: c.hard || 0,
      time: c.time || 0,
      passing_marks: c.passing_marks || 0,
      valid_from: (c.valid_from || '').slice?.(0,10) || '',
      valid_to:   (c.valid_to   || '').slice?.(0,10) || '',
    });
    setEditingId(c._id);
  };

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this criteria?")) {
      await deleteCriteria(id);
      load();
    }
  };

  useEffect(() => {
    load();
  }, []);

 return (
  <div className="criteria-container">
    <h2>📋 Interview Criteria</h2>

    <div className="criteria-layout">
      {/* Scrollable List */}
      <div className="scrollable-criteria-list">
        {criteriaList.map(c => (
          <div
            key={c._id}
            className="criteria-card"
            onClick={() => handleEdit(c)}   
            style={{ cursor: 'pointer' }}
          >
            <div>
              <h4>{c.name}</h4>
              <p>Category: {c.category?.name || 'N/A'}</p>
              <p>Passing: {c.passing_marks} | Time: {c.time} min</p>
              {/* 🗓️ NEW: show validity range inline */}
              <p onClick={(e)=>{ e.stopPropagation(); handleEdit(c); }}>
                Validity: {c.valid_from ? c.valid_from.slice(0,10) : '—'} → {c.valid_to ? c.valid_to.slice(0,10) : '—'}
              </p>
            </div>
            <div className="card-actions" onClick={(e)=>e.stopPropagation()}>
              <FaEdit onClick={() => handleEdit(c)} title="Edit" className="icon-btn" />
              <FaTrash onClick={() => handleDelete(c._id)} title="Delete" className="icon-btn delete" />
            </div>
          </div>
        ))}
      </div>

      {/* Scrollable Form */}
      <div className="criteria-form-container">
        <div className="criteria-form">
          <h3>{editingId ? '✏️ Edit Criteria' : '➕ Add New Criteria'}</h3>

          {/* ✨ Row: Name + Topics (2-column) */}
          <div className="two-col">
            <div className="form-group">
              <label>Name</label>
              <input
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="e.g., Technical Round"
              />
            </div>
            <div className="form-group">
              <label>Topics</label>
              <select
                value={form.category}
                onChange={e => setForm({ ...form, category: e.target.value })}
              >
                <option value="">Select Topic</option>
               {categories.map(c => (
                  <option key={c._id} value={c._id}>
                    {typeof c?.name === 'string'
                      ? c.name
                      : (c?.name?.name ?? JSON.stringify(c?.name ?? ''))}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <fieldset className="fieldset">
            <legend>🎯 Difficulty Count</legend>
            <div className="difficulty-inputs">
              <div className="form-group">
                <label>Easy</label>
                <input type="number" value={form.easy}
                  onChange={e => setForm({ ...form, easy: Number(e.target.value) })} />
              </div>
              <div className="form-group">
                <label>Medium</label>
                <input type="number" value={form.medium}
                  onChange={e => setForm({ ...form, medium: Number(e.target.value) })} />
              </div>
              <div className="form-group">
                <label>Hard</label>
                <input type="number" value={form.hard}
                  onChange={e => setForm({ ...form, hard: Number(e.target.value) })} />
              </div>
            </div>
          </fieldset>
          
          {/* ✨ New: Timing & Marks BEFORE validity */}
          <fieldset className="fieldset">
            <legend>⏱️ Timing & Marks</legend>
            <div className="two-col">
              <div className="form-group">
                <label>Time (minutes)</label>
                <input
                  type="number"
                  value={form.time}
                  onChange={e => setForm({ ...form, time: Number(e.target.value) })}
                  min={1}
                />
              </div>
              <div className="form-group">
                <label>Passing Marks</label>
                <input
                  type="number"
                  value={form.passing_marks}
                 onChange={e => setForm({ ...form, passing_marks: Number(e.target.value) })}
                  min={1}
                />
              </div>
            </div>
          </fieldset>
          <fieldset className="fieldset">
            <legend>🗓️ Interview Validity</legend>
            <div className="two-col">
              <div className="form-group">
                <label>Valid From</label>
                <input
                  type="date"
                  value={form.valid_from}
                  onChange={e => setForm({ ...form, valid_from: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Valid To</label>
                <input
                  type="date"
                  value={form.valid_to}
                  onChange={e => setForm({ ...form, valid_to: e.target.value })}
                />
              </div>
            </div>
          </fieldset>

          <button onClick={handleSubmit}>
            {editingId ? 'Update Criteria' : 'Create Criteria'}
          </button>
        </div>
      </div>
    </div>
  </div>
);

}

export default Criteria;
