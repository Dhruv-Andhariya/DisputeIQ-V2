import React, { useEffect, useState } from 'react';
import { Download, FileText, Package, Receipt, MessageSquare, ShieldCheck, AlertOctagon, Upload } from 'lucide-react';
import StatusBadge from './StatusBadge';
import CardHeader from './CardHeader';
import { humanize } from '../utils/format';
import { apiErrorMessage, downloadEvidence, fetchEvidenceProcessing, processEvidence } from '../api';

const EVIDENCE_TYPES = ['PAYMENT_RECEIPT', 'INVOICE', 'ORDER_RECORD', 'TRANSACTION_RECORD', 'SHIPPING_DOCUMENT', 'DELIVERY_PROOF', 'REFUND_RECORD', 'CANCELLATION_RECORD', 'CUSTOMER_COMMUNICATION', 'IDENTITY_DOCUMENT', 'SCREENSHOT', 'OTHER'];

export default function EvidenceMatrix({ evidenceList, uploadedEvidence = [], onUpload, canUpload = false }) {
  const [evidenceType, setEvidenceType] = useState('PAYMENT_RECEIPT');
  const [sourceType, setSourceType] = useState('MERCHANT_UPLOAD');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState({});
  const [processingId, setProcessingId] = useState(null);
  const [ocrOpen, setOcrOpen] = useState({});

  useEffect(() => {
    let active = true;
    Promise.all(uploadedEvidence.map(async (item) => {
      try {
        return [item.id, (await fetchEvidenceProcessing(item.id)).data];
      } catch {
        return null;
      }
    })).then((entries) => {
      if (active) setProcessing(Object.fromEntries(entries.filter(Boolean)));
    });
    return () => { active = false; };
  }, [uploadedEvidence]);
  const getCategoryIcon = (category) => {
    switch (category) {
      case 'PROOF_OF_DELIVERY': return Package;
      case 'INVOICE': return Receipt;
      case 'ORDER_CONFIRMATION': return FileText;
      case 'CUSTOMER_COMMUNICATION': return MessageSquare;
      case 'TERMS_AND_CONDITIONS': return ShieldCheck;
      default: return FileText;
    }
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!file || !onUpload) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('evidence_type', evidenceType);
      formData.append('source_type', sourceType);
      formData.append('file', file);
      await onUpload(formData);
      setFile(null);
      event.target.reset();
    } catch (err) {
      setError(apiErrorMessage(err, 'Evidence upload failed.'));
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (item) => {
    try {
      const response = await downloadEvidence(item.id);
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = item.original_filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(apiErrorMessage(err, 'Evidence download failed.'));
    }
  };

  const handleProcess = async (item) => {
    setProcessingId(item.id);
    setError(null);
    try {
      const result = (await processEvidence(item.id)).data;
      setProcessing((current) => ({ ...current, [item.id]: result }));
    } catch (err) {
      setError(apiErrorMessage(err, 'Document processing failed.'));
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <section className="card">
      <CardHeader
        icon={FileText}
        tone="blue"
        title="Evidence Matrix & Document Verification"
        subtitle="Retrieved records with deterministic status verification"
        action={<span className="chip">{evidenceList.length} Documents Attached</span>}
      />

      <div className="card-body grid grid-cols-1 gap-4 md:grid-cols-2">
        {evidenceList.map((item) => {
          const Icon = getCategoryIcon(item.category);
          const isContradiction = item.verification_status === 'CONTRADICTED';

          return (
            <div
              key={item.evidence_id}
              className={`flex flex-col rounded-lg border p-4 transition-colors ${
                isContradiction
                  ? 'border-rose-500/30 bg-rose-500/[0.04]'
                  : 'border-line bg-raised/50 hover:border-line-strong'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <div
                    className={`icon-tile ${
                      isContradiction
                        ? 'border-rose-500/25 bg-rose-500/10 text-rose-400'
                        : 'border-line bg-surface text-ink-muted'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-medium text-ink">{humanize(item.category)}</h4>
                    <p className="truncate font-mono text-xs text-ink-subtle" title={item.file_name}>{item.file_name}</p>
                  </div>
                </div>
                <StatusBadge status={item.verification_status} type="evidence" />
              </div>

              {isContradiction && (
                <div className="mt-3 flex items-start gap-2 text-[13px] leading-5 text-rose-300">
                  <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                  <p>Evidence Contradiction: Data in this document conflicts with payment or carrier records.</p>
                </div>
              )}

              {/* JSON preview */}
              <div className="code-block mt-3 max-h-28">
                <pre>{JSON.stringify(item.content, null, 2)}</pre>
              </div>
            </div>
          );
        })}
      </div>

      <div className="border-t border-line p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h4 className="text-sm font-semibold">Uploaded evidence artifacts</h4>
            <p className="mt-1 text-xs text-ink-subtle">Stored with provenance and SHA-256 integrity metadata. No authenticity judgment is made here.</p>
          </div>
          <span className="chip">{uploadedEvidence.length} Artifacts</span>
        </div>

        {canUpload && (
          <form onSubmit={handleUpload} className="mb-5 grid grid-cols-1 gap-3 rounded-lg border border-line bg-raised/40 p-4 md:grid-cols-4">
            <select className="input" value={evidenceType} onChange={(e) => setEvidenceType(e.target.value)} aria-label="Evidence type">
              {EVIDENCE_TYPES.map((type) => <option key={type} value={type}>{humanize(type)}</option>)}
            </select>
            <select className="input" value={sourceType} onChange={(e) => setSourceType(e.target.value)} aria-label="Evidence source">
              {['MERCHANT_UPLOAD', 'CUSTOMER_UPLOAD', 'SYSTEM_GENERATED', 'API_IMPORT', 'EXTERNAL_INTEGRATION'].map((type) => <option key={type} value={type}>{humanize(type)}</option>)}
            </select>
            <input className="input" type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.json,.csv,.txt" required />
            <button className="btn btn-primary" type="submit" disabled={!file || uploading}>
              <Upload className="h-4 w-4" />
              <span>{uploading ? 'Uploading...' : 'Upload evidence'}</span>
            </button>
          </form>
        )}

        {error && <div className="mb-4 panel-danger p-3 text-sm text-rose-300">{error}</div>}
        <div className="space-y-3">
          {uploadedEvidence.length === 0 && <p className="text-sm text-ink-muted">No uploaded artifacts for this dispute.</p>}
          {uploadedEvidence.map((item) => (
            <div key={item.id} className="space-y-3 rounded-lg border border-line bg-surface p-4">
              {(() => {
                const result = processing[item.id];
                return <>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium">{item.original_filename}</span>
                  <StatusBadge status={result?.status || item.status} />
                </div>
                <div className="mt-1 text-xs text-ink-muted">
                  {humanize(item.evidence_type)} · {humanize(item.source_type)} · {new Date(item.uploaded_at).toLocaleString()}
                </div>
                <div className="mt-1 truncate font-mono text-2xs text-ink-subtle" title={item.content_hash}>SHA-256: {item.content_hash}</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {canUpload && (!result || result.status === 'FAILED') && (
                  <button onClick={() => handleProcess(item)} className="btn btn-primary btn-sm" disabled={processingId === item.id}>
                    <FileText className="h-4 w-4" />
                    <span>{processingId === item.id ? 'Processing...' : result ? 'Retry processing' : 'Process document'}</span>
                  </button>
                )}
                <button onClick={() => handleDownload(item)} className="btn btn-secondary btn-sm">
                  <Download className="h-4 w-4" />
                  <span>Download</span>
                </button>
              </div>
              {result?.status === 'PROCESSED' && (
                <div className="border-t border-line pt-3">
                  <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                    <div><div className="eyebrow">Document type</div><div className="mt-1 text-ink">{humanize(result.document_type)}</div></div>
                    <div><div className="eyebrow">Processor</div><div className="mt-1 text-ink">{result.processor}</div></div>
                    <div><div className="eyebrow">OCR confidence</div><div className="mt-1 text-ink">{Math.round((result.confidence_metadata.ocr_confidence || 0) * 100)}%</div></div>
                    <div><div className="eyebrow">Schema</div><div className="mt-1 text-ink">{result.extraction_schema}</div></div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button onClick={() => setOcrOpen((current) => ({ ...current, [item.id]: !current[item.id] }))} className="btn btn-ghost btn-sm">
                      <span>{ocrOpen[item.id] ? 'Hide raw OCR' : 'View raw OCR'}</span>
                    </button>
                  </div>
                  {ocrOpen[item.id] && <pre className="code-block mt-3 max-h-48 overflow-auto whitespace-pre-wrap text-xs">{result.raw_text || 'No raw OCR text returned.'}</pre>}
                  <div className="mt-3"><div className="eyebrow mb-1">Extracted information</div><pre className="code-block max-h-48 overflow-auto text-xs">{JSON.stringify(result.structured_data, null, 2)}</pre></div>
                </div>
              )}
              {result?.status === 'FAILED' && <p className="text-xs text-rose-300">{result.error_message}</p>}
                </>;
              })()}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
