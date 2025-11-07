// src/components/Validity.js
import React, { useEffect, useState } from 'react';
import { fetchValidity, createValidity, updateValidityWindow } from '../api/api';

function Validity() {
  const [loading, setLoading] = useState(true);
  const [current, setCurrent] = useState(null); // { _id, valid_from, valid_to }
  const [form, setForm] = useState({ valid_from: '', valid_to: '' });
  const [msg, setMsg] = useState('');

  const load = async () => {
    setLoading(true);
    setMsg('');
    try {
      const res = await fetchValidity();
      const v = res?.data?.validity || null;
      setCurrent(v);
      setForm({
        valid_from: v?.valid_from?.slice(0, 10) || '',
        valid_to:   v?.valid_to?.slice(0, 10)   || '',
      });
    } catch (e) {
      // no existing window or server error
      setCurrent(null);
      setForm({ valid_from: '', valid_to: '' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const onSubmit = async (e) => {
    e.preventDefault();
    setMsg('');
    if (!form.valid_from || !form.valid_to) {
      setMsg('Both dates are required.');
      return;
    }
    try {
      if (current?._id) {
        await updateValidityWindow(current._id, {
          valid_from: form.valid_from,
          valid_to: form.valid_to,
        });
        setMsg('✅ Validity window updated.');
      } else {
        await createValidity({
          valid_from: form.valid_from,
          valid_to: form.valid_to,
        });
        setMsg('✅ Validity window created.');
      }
      await load();
    } catch (err) {
      setMsg(err?.response?.data?.error || 'Operation failed.');
    }
  };

  const isActive = () => {
    if (!current?.valid_from || !current?.valid_to) return null;
    const today = new Date().toISOString().slice(0, 10);
    return (today >= current.valid_from.slice(0,10) && today <= current.valid_to.slice(0,10));
  };

  return (
    <div style={styles.wrap}>
      <h2 style={styles.title}>🗓️ Interview Validity Window</h2>
      {loading ? <p>Loading…</p> : (
        <>
          <div style={styles.card}>
            <p style={{marginBottom:8}}>
              <strong>Current:</strong>{' '}
              {current
                ? `${current.valid_from?.slice(0,10)} → ${current.valid_to?.slice(0,10)}`
                : '— none —'}
            </p>
            {current && (
              <p style={{marginTop:0}}>
                Status: <strong>{isActive() ? 'ACTIVE' : 'INACTIVE'}</strong>
              </p>
            )}
          </div>

          <form onSubmit={onSubmit} style={styles.form}>
            <div style={styles.row}>
              <label style={styles.label}>Valid From</label>
              <input
                type="date"
                value={form.valid_from}
                onChange={e => setForm(f => ({ ...f, valid_from: e.target.value }))}
                style={styles.input}
                required
              />
            </div>

            <div style={styles.row}>
              <label style={styles.label}>Valid To</label>
              <input
                type="date"
                value={form.valid_to}
                onChange={e => setForm(f => ({ ...f, valid_to: e.target.value }))}
                style={styles.input}
                required
              />
            </div>

            <button type="submit" style={styles.button}>
              {current?._id ? 'Update Window' : 'Create Window'}
            </button>

            {msg && <p style={{marginTop:12}}>{msg}</p>}
          </form>
        </>
      )}
    </div>
  );
}

const styles = {
  wrap: { padding: '1rem' },
  title: { marginBottom: '1rem' },
  card: {
    background: '#111827',
    color: '#e5e7eb',
    padding: '12px 14px',
    borderRadius: 8,
    marginBottom: 16,
  },
  form: {
    display: 'grid',
    gap: 12,
    maxWidth: 420,
    background: '#111827',
    color: '#e5e7eb',
    padding: 16,
    borderRadius: 8,
  },
  row: { display: 'grid', gap: 6 },
  label: { fontSize: 14, color: '#cbd5e1' },
  input: {
    padding: '10px',
    borderRadius: 6,
    border: '1px solid #374151',
    background: '#0b1220',
    color: '#e5e7eb',
  },
  button: {
    padding: '10px 12px',
    borderRadius: 6,
    border: 'none',
    background: '#4f46e5',
    color: '#fff',
    fontWeight: 600,
    cursor: 'pointer',
  },
};

export default Validity;
