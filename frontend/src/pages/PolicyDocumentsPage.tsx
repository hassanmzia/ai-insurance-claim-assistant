import React, { useEffect, useState, useRef } from 'react';
import { FiUpload, FiDatabase, FiFile, FiCheck, FiLoader, FiTrash2 } from 'react-icons/fi';
import toast from 'react-hot-toast';
import api from '../services/api';
import { PolicyDocument } from '../types';
import { formatDate, formatDateTime, statusLabel } from '../utils/helpers';

const PolicyDocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<PolicyDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [indexingId, setIndexingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Upload form state
  const [title, setTitle] = useState('');
  const [policyType, setPolicyType] = useState('auto');
  const [effectiveDate, setEffectiveDate] = useState('');
  const [version, setVersion] = useState('1.0');
  const [showUploadForm, setShowUploadForm] = useState(false);

  const fetchDocuments = () => {
    api.getPolicyDocuments()
      .then((res) => setDocuments(res.results || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchDocuments(); }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      toast.error('Please select a PDF file');
      return;
    }
    if (!title.trim()) {
      toast.error('Please enter a document title');
      return;
    }
    if (!effectiveDate) {
      toast.error('Please select an effective date');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('document', file);
      formData.append('title', title);
      formData.append('policy_type', policyType);
      formData.append('effective_date', effectiveDate);
      formData.append('version', version);

      await api.uploadPolicyDocument(formData);
      toast.success('Policy document uploaded successfully');
      setTitle('');
      setPolicyType('auto');
      setEffectiveDate('');
      setVersion('1.0');
      setShowUploadForm(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchDocuments();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleIndex = async (docId: string) => {
    setIndexingId(docId);
    try {
      const result = await api.indexPolicyDocument(docId);
      toast.success(`Indexed ${result.chunks} chunks into vector store`);
      fetchDocuments();
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Indexing failed');
    } finally {
      setIndexingId(null);
    }
  };

  const policyTypeLabels: Record<string, string> = {
    auto: 'Auto Insurance',
    home: 'Home Insurance',
    health: 'Health Insurance',
    life: 'Life Insurance',
    commercial: 'Commercial Insurance',
  };

  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Policy Documents</h2>
          <p className="subtitle">Upload and index insurance policy PDFs for AI-powered retrieval</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowUploadForm(!showUploadForm)}>
          <FiUpload /> Upload Policy
        </button>
      </div>

      {showUploadForm && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header"><h3>Upload New Policy Document</h3></div>
          <div className="card-body">
            <form onSubmit={handleUpload}>
              <div className="form-row">
                <div className="form-group">
                  <label>Document Title *</label>
                  <input
                    type="text"
                    className="form-control"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Auto Insurance Policy 2026"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Policy Type</label>
                  <select
                    className="form-control"
                    value={policyType}
                    onChange={(e) => setPolicyType(e.target.value)}
                  >
                    {Object.entries(policyTypeLabels).map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Effective Date *</label>
                  <input
                    type="date"
                    className="form-control"
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Version</label>
                  <input
                    type="text"
                    className="form-control"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="1.0"
                  />
                </div>
              </div>
              <div className="form-group">
                <label>PDF File *</label>
                <input
                  type="file"
                  className="form-control"
                  ref={fileInputRef}
                  accept=".pdf"
                  required
                />
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                <button type="submit" className="btn btn-primary" disabled={uploading}>
                  {uploading ? <><FiLoader style={{ animation: 'spin 1s linear infinite' }} /> Uploading...</> : <><FiUpload /> Upload</>}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowUploadForm(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Uploaded Policies ({documents.length})</h3>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {documents.length === 0 ? (
            <div className="empty-state">
              <FiFile style={{ fontSize: '48px' }} />
              <h3>No policy documents uploaded</h3>
              <p>Upload a policy PDF to enable AI-powered RAG retrieval for claim processing.</p>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Version</th>
                    <th>Effective</th>
                    <th>Indexed</th>
                    <th>Chunks</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <FiFile style={{ color: '#ef4444', flexShrink: 0 }} />
                          <span style={{ fontWeight: 600 }}>{doc.title}</span>
                        </div>
                      </td>
                      <td>
                        <span className="badge" style={{ background: '#eff6ff', color: '#1a56db' }}>
                          {policyTypeLabels[doc.policy_type] || doc.policy_type}
                        </span>
                      </td>
                      <td>v{doc.version}</td>
                      <td>{formatDate(doc.effective_date)}</td>
                      <td>
                        {doc.is_indexed ? (
                          <span className="badge" style={{ background: '#ecfdf5', color: '#10b981' }}>
                            <FiCheck style={{ marginRight: '4px' }} /> Indexed
                          </span>
                        ) : (
                          <span className="badge" style={{ background: '#fef3c7', color: '#f59e0b' }}>
                            Not Indexed
                          </span>
                        )}
                      </td>
                      <td>{doc.chunk_count > 0 ? doc.chunk_count : '—'}</td>
                      <td style={{ fontSize: '13px', color: '#6b7280' }}>
                        {formatDateTime(doc.created_at)}
                      </td>
                      <td>
                        {!doc.is_indexed && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handleIndex(doc.id)}
                            disabled={indexingId === doc.id}
                          >
                            {indexingId === doc.id ? (
                              <><FiLoader style={{ animation: 'spin 1s linear infinite' }} /> Indexing...</>
                            ) : (
                              <><FiDatabase /> Index in ChromaDB</>
                            )}
                          </button>
                        )}
                        {doc.is_indexed && (
                          <span style={{ fontSize: '12px', color: '#10b981' }}>Ready for RAG</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '24px' }}>
        <div className="card-header"><h3>How Policy Indexing Works</h3></div>
        <div className="card-body">
          <div className="processing-steps">
            <div className="processing-step completed">
              <div className="step-icon" style={{ background: '#eff6ff', color: '#1a56db' }}>1</div>
              <div className="step-info">
                <div className="step-name">Upload PDF</div>
                <div className="step-detail">Upload an insurance policy document in PDF format</div>
              </div>
            </div>
            <div className="processing-step completed">
              <div className="step-icon" style={{ background: '#faf5ff', color: '#7c3aed' }}>2</div>
              <div className="step-info">
                <div className="step-name">Extract & Chunk</div>
                <div className="step-detail">The document is parsed, text extracted, and split into semantic chunks</div>
              </div>
            </div>
            <div className="processing-step completed">
              <div className="step-icon" style={{ background: '#ecfdf5', color: '#10b981' }}>3</div>
              <div className="step-info">
                <div className="step-name">Generate Embeddings</div>
                <div className="step-detail">Each chunk is embedded using the all-MiniLM-L6-v2 model into 384-dimensional vectors</div>
              </div>
            </div>
            <div className="processing-step completed">
              <div className="step-icon" style={{ background: '#fff7ed', color: '#f97316' }}>4</div>
              <div className="step-info">
                <div className="step-name">Store in ChromaDB</div>
                <div className="step-detail">Vectors and text are stored in ChromaDB for similarity search during claim processing</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PolicyDocumentsPage;
