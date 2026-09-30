const ACRONYMS = new Set(['API', 'ID', 'UPI', 'AI', 'OTP', 'AVS', 'CVV', 'IP', 'SMS', 'POD', 'URL', 'KYC', 'GST']);

// Turns enum-style values (e.g. "ORDER_ID_MATCH") into sentence-case labels ("Order ID match").
export function humanize(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/_/g, ' ')
    .trim()
    .split(/\s+/)
    .map((word, idx) => {
      const upper = word.toUpperCase();
      if (ACRONYMS.has(upper)) return upper;
      const lower = word.toLowerCase();
      return idx === 0 ? lower.charAt(0).toUpperCase() + lower.slice(1) : lower;
    })
    .join(' ');
}

export function formatINR(amount) {
  return `₹${Number(amount).toLocaleString('en-IN')}`;
}
