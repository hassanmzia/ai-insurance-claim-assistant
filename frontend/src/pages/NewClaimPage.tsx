import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiArrowLeft, FiSend } from 'react-icons/fi';
import toast from 'react-hot-toast';
import api from '../services/api';
import { InsurancePolicy } from '../types';

const NewClaimPage: React.FC = () => {
  const [policies, setPolicies] = useState<InsurancePolicy[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    policy: '',
    loss_type: 'collision',
    date_of_loss: '',
    loss_description: '',
    loss_location: '',
    estimated_repair_cost: '',
    vehicle_details: '{}',
    third_party_involved: false,
    police_report_number: '',
    priority: 'medium',
  });
  const navigate = useNavigate();

  useEffect(() => {
    api.getPolicies().then((res) => setPolicies(res.results || [])).catch(console.error);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      let vehicleDetails = {};
      try { vehicleDetails = JSON.parse(form.vehicle_details); } catch {}

      const claimData = {
        ...form,
        estimated_repair_cost: parseFloat(form.estimated_repair_cost) || 0,
        vehicle_details: vehicleDetails,
      };

      const result = await api.createClaim(claimData);
      toast.success(`Claim ${result.claim_number} submitted successfully`);
      navigate(`/claims/${result.id}`);
    } catch (err: any) {
      const errors = err.response?.data;
      if (errors && typeof errors === 'object') {
        const firstError = Object.values(errors).flat()[0];
        toast.error(String(firstError));
      } else {
        toast.error('Failed to create claim');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/claims')}>
            <FiArrowLeft /> Back
          </button>
          <div>
            <h2>Submit New Claim</h2>
            <p className="subtitle">File an insurance claim for processing</p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Insurance Policy *</label>
                <select name="policy" className="form-control" value={form.policy} onChange={handleChange} required>
                  <option value="">Select a policy...</option>
                  {policies.map((p) => (
                    <option key={p.id} value={p.id}>{p.policy_number} - {p.policy_type.charAt(0).toUpperCase() + p.policy_type.slice(1)} Insurance - {p.holder_name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Loss Type *</label>
                <select name="loss_type" className="form-control" value={form.loss_type} onChange={handleChange}>
                  <option value="collision">Collision</option>
                  <option value="comprehensive">Comprehensive</option>
                  <option value="liability">Liability</option>
                  <option value="personal_injury">Personal Injury</option>
                  <option value="property_damage">Property Damage</option>
                  <option value="theft">Theft</option>
                  <option value="vandalism">Vandalism</option>
                  <option value="weather">Weather Damage</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Date of Loss *</label>
                <input type="date" name="date_of_loss" className="form-control" value={form.date_of_loss} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label>Estimated Repair Cost ($) *</label>
                <input type="number" name="estimated_repair_cost" className="form-control" value={form.estimated_repair_cost} onChange={handleChange} placeholder="0.00" min="0" step="0.01" required />
              </div>
            </div>

            <div className="form-group">
              <label>Loss Description *</label>
              <textarea name="loss_description" className="form-control" value={form.loss_description} onChange={handleChange} placeholder="Describe the incident in detail..." rows={4} required />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Loss Location</label>
                <input type="text" name="loss_location" className="form-control" value={form.loss_location} onChange={handleChange} placeholder="Address or location description" />
              </div>
              <div className="form-group">
                <label>Police Report Number</label>
                <input type="text" name="police_report_number" className="form-control" value={form.police_report_number} onChange={handleChange} placeholder="Optional" />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Priority</label>
                <select name="priority" className="form-control" value={form.priority} onChange={handleChange}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
              <div className="form-group">
                <label>Vehicle Details (JSON)</label>
                <input type="text" name="vehicle_details" className="form-control" value={form.vehicle_details} onChange={handleChange} placeholder='{"make_model": "2022 Honda City"}' />
              </div>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" name="third_party_involved" checked={form.third_party_involved} onChange={handleChange} />
                Third party involved in the incident
              </label>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
              <button type="button" className="btn btn-secondary" onClick={() => navigate('/claims')}>Cancel</button>
              <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
                <FiSend /> {loading ? 'Submitting...' : 'Submit Claim'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default NewClaimPage;
