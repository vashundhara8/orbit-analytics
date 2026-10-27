import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  X,
  Download,
  RefreshCw,
  Clock,
  Database,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '../api/client';
import { IngestionStatusResponse, IngestionUploadResponse } from '../types/api';

interface DataOnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDataIngested: () => void;
  tenantName: string;
  tenantId: string;
}

export const DataOnboardingModal: React.FC<DataOnboardingModalProps> = ({
  isOpen,
  onClose,
  onDataIngested,
  tenantName,
  tenantId,
}) => {
  const [statusData, setStatusData] = useState<IngestionStatusResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<IngestionUploadResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showErrorSamples, setShowErrorSamples] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      loadStatus();
      setSelectedFile(null);
      setUploadResult(null);
      setErrorMessage(null);
    }
  }, [isOpen]);

  const loadStatus = async () => {
    try {
      setLoadingStatus(true);
      const res = await api.getIngestionStatus();
      setStatusData(res);
    } catch {
      // Silently proceed with blank state if status endpoint is not yet populated
    } finally {
      setLoadingStatus(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith('.csv')) {
        setErrorMessage('Please select a valid .csv file.');
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (!file.name.toLowerCase().endsWith('.csv')) {
        setErrorMessage('Please drop a valid .csv file.');
        return;
      }
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      setErrorMessage(null);
      const res = await api.uploadCustomerCsv(selectedFile);
      setUploadResult(res);
      await loadStatus();
      onDataIngested();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred during file upload.');
      }
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  const quality = uploadResult ? uploadResult.quality_summary : statusData?.quality_summary;

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="modal-onboarding-title">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-info">
            <div className="modal-icon-badge">
              <UploadCloud size={20} />
            </div>
            <div>
              <h2 id="modal-onboarding-title" className="modal-title">
                Customer Data Onboarding
              </h2>
              <p className="modal-subtitle">
                Ingest customer event telemetry directly into isolated tenant storage
              </p>
            </div>
          </div>
          <button onClick={onClose} className="modal-close-btn" aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Active Tenant Storage Context */}
          <div className="modal-context-bar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Database size={18} color="var(--accent-teal)" />
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {tenantName}
                  </span>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      padding: '2px 6px',
                      background: 'var(--bg-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-muted)',
                      fontFamily: 'monospace',
                    }}
                  >
                    {tenantId}
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  {loadingStatus ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <RefreshCw size={12} className="spin-icon" /> Checking tenant storage...
                    </span>
                  ) : statusData?.has_data ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--accent-lime)' }}>
                      <ShieldCheck size={13} /> Tenant-Isolated Dataset Ingested
                    </span>
                  ) : (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--accent-amber)' }}>
                      <Clock size={13} /> Viewing Synthetic Reference Data
                    </span>
                  )}
                </div>
              </div>
            </div>

            <a
              href={api.getTemplateDownloadUrl()}
              download="orbit_analytics_template.csv"
              className="btn-export"
              title="Download canonical CSV format template"
            >
              <Download size={14} />
              <span>CSV Template</span>
            </a>
          </div>

          {/* Schema Requirements Banner */}
          <div className="modal-data-contract">
            <div className="contract-header">
              <span className="contract-title">Data Contract & Canonical Events</span>
              <span className="contract-limits">Max size: 10MB • Max rows: 100,000</span>
            </div>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Required columns:{' '}
              <code style={{ color: 'var(--accent-teal)', fontFamily: 'monospace' }}>user_id</code>,{' '}
              <code style={{ color: 'var(--accent-teal)', fontFamily: 'monospace' }}>event_name</code>,{' '}
              <code style={{ color: 'var(--accent-teal)', fontFamily: 'monospace' }}>event_timestamp</code>.{' '}
              Optional:{' '}
              <code style={{ color: 'var(--text-muted)', fontFamily: 'monospace' }}>acquisition_channel</code>.
            </p>
            <div className="contract-events">
              {['signup', 'workspace_created', 'invite_sent', 'first_project', 'paid'].map((evt) => (
                <span key={evt} className="event-pill">
                  {evt}
                </span>
              ))}
            </div>
          </div>

          {/* Upload Dropzone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`modal-dropzone ${selectedFile ? 'active' : ''}`}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
            }}
            aria-label="Upload CSV dropzone"
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".csv"
              style={{ display: 'none' }}
            />
            <div className="dropzone-icon">
              <FileText size={24} />
            </div>
            {selectedFile ? (
              <div>
                <p style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {selectedFile.name}
                </p>
                <p style={{ fontSize: '0.78rem', color: 'var(--accent-teal)', marginTop: '2px' }}>
                  {(selectedFile.size / 1024).toFixed(1)} KB — Ready to validate & ingest
                </p>
              </div>
            ) : (
              <div>
                <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Click to select or drag and drop a customer CSV file
                </p>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Standard UTF-8 encoded CSV with user events
                </p>
              </div>
            )}
          </div>

          {/* Error Message Alert */}
          {errorMessage && (
            <div className="modal-alert-error" role="alert">
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ display: 'block', marginBottom: '2px' }}>Validation Rejected</strong>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Ingestion & Quality Summary Panel */}
          {quality && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifySelf: 'stretch', justifyContent: 'space-between' }}>
                <h3
                  style={{
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: 'var(--text-muted)',
                  }}
                >
                  Data Quality & Observation Summary
                </h3>
                {uploadResult && (
                  <span
                    className="tab-badge"
                    style={{
                      background:
                        uploadResult.status === 'success'
                          ? 'var(--accent-lime-subtle)'
                          : 'var(--accent-amber-subtle)',
                      color:
                        uploadResult.status === 'success' ? 'var(--accent-lime)' : 'var(--accent-amber)',
                      borderColor:
                        uploadResult.status === 'success'
                          ? 'rgba(132, 204, 22, 0.3)'
                          : 'rgba(245, 158, 11, 0.3)',
                    }}
                  >
                    {uploadResult.status === 'success' ? 'Validated & Ingested' : 'Ingested with Warnings'}
                  </span>
                )}
              </div>

              <div className="quality-grid">
                <div className="quality-card">
                  <span className="quality-card-label">Accepted Events</span>
                  <span className="quality-card-value" style={{ color: 'var(--accent-lime)' }}>
                    {quality.accepted_rows.toLocaleString()}
                  </span>
                </div>
                <div className="quality-card">
                  <span className="quality-card-label">Total Accounts</span>
                  <span className="quality-card-value" style={{ color: 'var(--accent-teal)' }}>
                    {quality.total_unique_users.toLocaleString()}
                  </span>
                </div>
                <div className="quality-card">
                  <span className="quality-card-label">Rejected Rows</span>
                  <span
                    className="quality-card-value"
                    style={{ color: quality.rejected_rows > 0 ? 'var(--accent-coral)' : 'var(--text-muted)' }}
                  >
                    {quality.rejected_rows.toLocaleString()}
                  </span>
                </div>
                <div className="quality-card">
                  <span className="quality-card-label">Coverage Window</span>
                  <span className="quality-card-value" style={{ color: 'var(--accent-sky)' }}>
                    {quality.coverage_days} day{quality.coverage_days === 1 ? '' : 's'}
                  </span>
                </div>
              </div>

              {/* Window Completeness & Warnings */}
              {quality.warnings.length > 0 && (
                <div className="quality-advisory">
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontWeight: 600,
                      color: 'var(--accent-amber)',
                      marginBottom: '4px',
                    }}
                  >
                    <AlertTriangle size={14} />
                    <span>Data Quality Advisory</span>
                  </div>
                  <ul
                    style={{
                      paddingLeft: '18px',
                      margin: 0,
                      color: 'var(--text-secondary)',
                      fontSize: '0.78rem',
                    }}
                  >
                    {quality.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Sample Rejections Collapsible */}
              {quality.rejected_rows > 0 && quality.rejection_samples.length > 0 && (
                <div className="rejections-collapsible">
                  <button
                    type="button"
                    onClick={() => setShowErrorSamples(!showErrorSamples)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                    }}
                  >
                    <span>Inspect Sample Rejections ({quality.rejection_samples.length} shown)</span>
                    {showErrorSamples ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                  {showErrorSamples && (
                    <div
                      style={{
                        marginTop: '8px',
                        padding: '8px 12px',
                        background: 'var(--bg-app)',
                        borderRadius: 'var(--radius-sm)',
                        fontFamily: 'monospace',
                        fontSize: '0.75rem',
                        color: 'var(--accent-coral)',
                      }}
                    >
                      {quality.rejection_samples.map((sample, idx) => (
                        <div key={idx}>{sample}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Uploaded data replaces tenant mart and recalculates funnels live
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button onClick={onClose} className="btn-secondary" type="button">
              {uploadResult ? 'Done' : 'Cancel'}
            </button>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="btn-primary"
              type="button"
            >
              {uploading ? (
                <>
                  <RefreshCw size={14} className="spin-icon" />
                  <span>Ingesting & Computing...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={14} />
                  <span>Ingest Customer Data</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
