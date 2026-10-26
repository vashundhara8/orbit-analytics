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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-800 rounded-xl shadow-2xl text-slate-100 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80 sticky top-0 z-10 backdrop-blur">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Customer Data Onboarding</h2>
              <p className="text-xs text-slate-400">
                Ingest customer event telemetry directly into isolated tenant storage
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6 flex-1">
          {/* Active Tenant Storage Context */}
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <Database className="w-5 h-5 text-indigo-400" />
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-semibold text-slate-300">{tenantName}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                    {tenantId}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {loadingStatus ? (
                    <span className="text-slate-400 flex items-center gap-1">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Checking tenant storage...
                    </span>
                  ) : statusData?.has_data ? (
                    <span className="text-emerald-400 flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" /> Tenant-Isolated Dataset Ingested
                    </span>
                  ) : (
                    <span className="text-amber-400 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> Viewing Synthetic Reference Data
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <a
                href={api.getTemplateDownloadUrl()}
                download="orbit_analytics_template.csv"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition border border-slate-700"
              >
                <Download className="w-3.5 h-3.5" />
                <span>CSV Template</span>
              </a>
            </div>
          </div>

          {/* Schema Requirements Pill Banner */}
          <div className="p-4 rounded-lg bg-indigo-950/20 border border-indigo-900/40 text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-indigo-300">Data Contract & Canonical Events</span>
              <span className="text-[10px] text-slate-400">Max size: 10MB • Max rows: 100,000</span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              Required columns: <code className="text-indigo-400 font-mono">user_id</code>,{' '}
              <code className="text-indigo-400 font-mono">event_name</code>,{' '}
              <code className="text-indigo-400 font-mono">event_timestamp</code>. Optional:{' '}
              <code className="text-slate-400 font-mono">acquisition_channel</code>.
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {['signup', 'workspace_created', 'invite_sent', 'first_project', 'paid'].map((evt) => (
                <span
                  key={evt}
                  className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 font-mono text-[11px] border border-slate-700"
                >
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
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
              selectedFile
                ? 'border-indigo-500 bg-indigo-500/5'
                : 'border-slate-700 hover:border-slate-500 bg-slate-950/40 hover:bg-slate-950/70'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".csv"
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center space-y-2">
              <div className="p-3 rounded-full bg-slate-800 text-slate-300">
                <FileText className="w-6 h-6" />
              </div>
              {selectedFile ? (
                <div>
                  <p className="text-sm font-medium text-white">{selectedFile.name}</p>
                  <p className="text-xs text-indigo-400 mt-0.5">
                    {(selectedFile.size / 1024).toFixed(1)} KB — Ready to validate & ingest
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-medium text-slate-300">
                    Click to select or drag and drop a customer CSV file
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Standard UTF-8 encoded CSV with user events
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Error Message Alert */}
          {errorMessage && (
            <div className="p-3 rounded-lg bg-red-950/40 border border-red-900/60 text-red-300 text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-semibold">Validation Rejected</p>
                <p className="mt-0.5">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Ingestion & Quality Summary Panel */}
          {quality && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Data Quality & Observation Summary
                </h3>
                {uploadResult && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                      uploadResult.status === 'success'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}
                  >
                    {uploadResult.status === 'success' ? 'Validated & Ingested' : 'Ingested with Warnings'}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Accepted Events</span>
                  <span className="text-base font-bold text-emerald-400 font-mono">
                    {quality.accepted_rows.toLocaleString()}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Total Accounts</span>
                  <span className="text-base font-bold text-indigo-400 font-mono">
                    {quality.total_unique_users.toLocaleString()}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Rejected Rows</span>
                  <span
                    className={`text-base font-bold font-mono ${
                      quality.rejected_rows > 0 ? 'text-rose-400' : 'text-slate-400'
                    }`}
                  >
                    {quality.rejected_rows.toLocaleString()}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Coverage Window</span>
                  <span className="text-base font-bold text-cyan-400 font-mono">
                    {quality.coverage_days} day{quality.coverage_days === 1 ? '' : 's'}
                  </span>
                </div>
              </div>

              {/* Window Completeness & Warnings */}
              {quality.warnings.length > 0 && (
                <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-900/50 space-y-1">
                  <div className="flex items-center space-x-1.5 text-xs font-semibold text-amber-300">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                    <span>Data Quality Advisory</span>
                  </div>
                  <ul className="text-xs text-amber-200/90 list-disc list-inside space-y-0.5 pl-1">
                    {quality.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Sample Rejections Collapsible */}
              {quality.rejected_rows > 0 && quality.rejection_samples.length > 0 && (
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                  <button
                    onClick={() => setShowErrorSamples(!showErrorSamples)}
                    className="flex items-center justify-between w-full text-slate-400 hover:text-slate-200"
                  >
                    <span>Inspect Sample Rejections ({quality.rejection_samples.length} shown)</span>
                    {showErrorSamples ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                  {showErrorSamples && (
                    <div className="mt-2 space-y-1 font-mono text-[11px] text-rose-300/80 bg-slate-900 p-2 rounded">
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
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/80">
          <span className="text-[11px] text-slate-500">
            Uploaded data replaces tenant mart and recalculates funnels live
          </span>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
            >
              {uploadResult ? 'Done' : 'Cancel'}
            </button>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className={`flex items-center space-x-2 px-4 py-2 text-xs font-semibold rounded-lg transition shadow-lg ${
                !selectedFile || uploading
                  ? 'bg-indigo-600/50 text-indigo-300 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30'
              }`}
            >
              {uploading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Ingesting & Computing...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
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
