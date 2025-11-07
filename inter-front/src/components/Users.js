import React, { useEffect, useState } from 'react';
import {
  uploadCandidates,
  fetchCandidates,
  updateCandidate,
  deleteCandidate
} from '../api/api';
import './Users.css';

function Users() {
  const [file, setFile] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});

  const loadCandidates = async () => {
    try {
      const res = await fetchCandidates();
      setCandidates(res.data.candidates);
    } catch (err) {
      alert("Error fetching candidates.");
    }
  };

  useEffect(() => {
    loadCandidates();
  }, []);

  const handleUpload = async () => {
    if (!file) return alert("Please select an Excel file.");

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    try {
      const res = await uploadCandidates(formData);
      alert(res.data.message);
      loadCandidates();
      setFile(null);
    } catch (err) {
      alert(err?.response?.data?.error || err?.message || "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (candidate) => {
    setEditingId(candidate.candidateId);
    setEditData({ ...candidate });
  };

  const handleUpdate = async () => {
    try {
      await updateCandidate(editingId, editData);
      alert("Candidate updated!");
      setEditingId(null);
      loadCandidates();
    } catch (err) {
      alert("Update failed.");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure to delete?")) return;
    try {
      await deleteCandidate(id);
      alert("Candidate deleted.");
      loadCandidates();
    } catch (err) {
      alert("Delete failed.");
    }
  };

  return (
    <div className="users-container">
      <fieldset style={{ marginBottom: '2rem' }}>
        <legend>📤 Upload Candidate Excel</legend>
        <input
          type="file"
          accept=".xlsx"
          onChange={e => setFile(e.target.files[0])}
        />
        <button onClick={handleUpload} disabled={loading}>
          {loading ? 'Uploading...' : 'Upload'}
        </button>
      </fieldset>

      <fieldset>
        <legend>👥 Your Uploaded Candidates</legend>
        {candidates.length === 0 ? (
          <p>No candidates yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Candidate ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Interview</th>
                <th>Date</th>
                <th>Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map(c => (
                <tr key={c.candidateId}>
                  {editingId === c.candidateId ? (
                    <>
                      <td>{c.candidateId}</td>
                      <td><input value={editData.name || ''} onChange={e => setEditData({ ...editData, name: e.target.value })} /></td>
                      <td><input value={editData.email || ''} onChange={e => setEditData({ ...editData, email: e.target.value })} /></td>
                      <td><input value={editData.phone || ''} onChange={e => setEditData({ ...editData, phone: e.target.value })} /></td>
                      <td><input value={editData.interview_name || ''} onChange={e => setEditData({ ...editData, interview_name: e.target.value })} /></td>
                      <td><input value={editData.interview_date || ''} onChange={e => setEditData({ ...editData, interview_date: e.target.value })} /></td>
                      <td><input value={editData.interview_time || ''} onChange={e => setEditData({ ...editData, interview_time: e.target.value })} /></td>
                      <td>
                        <button onClick={handleUpdate}>💾 Save</button>
                        <button onClick={() => setEditingId(null)}>❌ Cancel</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{c.candidateId}</td>
                      <td>{c.name}</td>
                      <td>{c.email}</td>
                      <td>{c.phone}</td>
                      <td>{c.interview_name}</td>
                      <td>{c.interview_date}</td>
                      <td>{c.interview_time}</td>
                      <td>
                        <button onClick={() => handleEdit(c)}>✏️ Edit</button>
                        <button onClick={() => handleDelete(c.candidateId)}>🗑️ Delete</button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </fieldset>
    </div>
  );
}

export default Users;
