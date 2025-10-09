import React, { useState, useEffect } from 'react';
import {
  fetchCategories,
  fetchQuestions,
  uploadQuestions
} from '../api/api';
import './Questions.css';

function Questions() {
  const [categories, setCategories] = useState([]);
  const [viewCategory, setViewCategory] = useState(null);
  const [uploadCategory, setUploadCategory] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [pdfFile, setPdfFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
      fetchCategories().then(res => {
    const normalized = (res.data ?? []).map(c => ({
      ...c,
      name:
        typeof c?.name === 'string'
          ? c.name
          : (c?.name?.name ?? String(c?.name ?? ''))
    }));
    setCategories(normalized);
  });
 }, []);

  useEffect(() => {
    if (viewCategory) {
      fetchQuestions(viewCategory)
        .then(res => setQuestions(res.data.questions || []))
        .catch(err => {
          console.error(err);
          setQuestions([]);
        });
    }
  }, [viewCategory]);

  const handlePDFUpload = async () => {
    if (!uploadCategory || !pdfFile) {
      alert('Please select a category and upload a file.');
      return;
    }

    const formData = new FormData();
    formData.append('category_id', uploadCategory);
    formData.append('file', pdfFile);

    setUploading(true);
    try {
      const res = await uploadQuestions(formData);
      alert(res.data.message);
      setPdfFile(null);
    } catch (err) {
      alert(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="questions-container">
      {/* Upload PDF Section */}
      <fieldset style={{ marginBottom: '2rem' }}>
        <legend>📤 Upload Questions from PDF</legend>
        <select
          value={uploadCategory || ''}
          onChange={e => setUploadCategory(e.target.value)}
        >
          <option value="">-- Select Category for Upload --</option>
           {categories.map(cat => (
   <option key={cat._id} value={cat._id}>
     {typeof cat?.name === 'string'
       ? cat.name
       : (cat?.name?.name ?? JSON.stringify(cat?.name ?? ''))}
   </option>
 ))}
        </select>

        <input
          type="file"
          accept="application/pdf"
          onChange={e => setPdfFile(e.target.files[0])}
          style={{ display: 'block', margin: '1rem 0' }}
        />

        <button onClick={handlePDFUpload} disabled={uploading}>
          {uploading ? 'Uploading...' : 'Upload PDF'}
        </button>
      </fieldset>

      {/* View Questions Section */}
      <fieldset>
        <legend>📄 Questions Management</legend>
        <select
          value={viewCategory || ''}
          onChange={e => setViewCategory(e.target.value)}
        >
          <option value="">-- Select Category to View Questions --</option>
          {categories.map(cat => (
            <option key={cat._id} value={cat._id}>{cat.name}</option>
          ))}
        </select>

        {viewCategory && (
          <div className="scrollable-questions">
            {questions.length === 0 ? (
              <p>No questions found.</p>
            ) : (
              questions.map(q => (
                <div key={q._id} className="question-card">
                  <div className="question-header">
                    <h4>Q{q.qno}: {q.question}</h4>
                  </div>
                  {q.image_url && (
                    <img src={`http://localhost:5000${q.image_url}`} alt={`Q${q.qno}`} />
                  )}
                  <p><strong>Answer:</strong> {q.answer}</p>
                  <p><strong>Difficulty:</strong> {q.difficulty}</p>
                </div>
              ))
            )}
          </div>
        )}
      </fieldset>
    </div>
  );
}

export default Questions;
