import { useEffect, useState } from "react";

const API_URL = "http://192.168.42.200:8000";

type CreditResponse = {
  remaining_irt: number;
  account_tier: number;
  limit?: number;
  credit_sources?: {
    grants: any[];
    packages: any[];
  };
};

function CreditDisplay() {
  const [credit, setCredit] = useState<CreditResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCredit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/avalai/credit`);
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Server error ${res.status}: ${errText}`);
      }
      const data: CreditResponse = await res.json();
      setCredit(data);
    } catch (err: any) {
      console.error("Credit fetch failed:", err);
      setError(err.message || "Failed to load credit.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCredit();
  }, []);

  if (loading) {
    return <span className="extracting-spinner" aria-label="Loading" />;
  }

  if (error) {
    return (
      <span
        className="credit-badge error"
        title={error}
        onClick={fetchCredit}
        style={{ cursor: "pointer" }}
      >
        ⚠️ Credit error (click to retry)
      </span>
    );
  }

  if (!credit) return null;

  const remaining = credit.remaining_irt?.toLocaleString("en-US") ?? "—";

  return (
    <div
      className="credit-badge"
      title={`Account tier: ${credit.account_tier}`}
      onClick={fetchCredit}
      style={{ cursor: "pointer" }}
    >
      <span className="credit-amount">{remaining} T</span>
    </div>
  );
}

export default CreditDisplay;