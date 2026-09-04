export interface MandateLimits {
  max_per_transaction: number;
  max_cumulative: number;
  cumulative_window_hours: number;
  max_attempts_per_minute: number;
}

export interface MandateScope {
  allowed_mcc: string[];
  allowed_merchants: string[];
  blocked_categories: string[];
}

export interface Mandate {
  mandate_id: string;
  user_id: string;
  created_at: string;
  limits: MandateLimits;
  scope: MandateScope;
  status: "active" | "revoked" | "expired";
  revoked_at: string | null;
}

export interface Stats {
  approved_count: number;
  blocked_count: number;
  total_spend_inr: number;
  cumulative_limit_inr: number;
}

export interface AuditEntry {
  timestamp: string;
  tool_call: {
    tool: string;
    args: {
      merchant_id: string;
      items: { sku: string; qty: number; name: string }[];
      amount_inr: number;
    };
  };
  decision: {
    approved: boolean;
    code: string;
    reason: string;
  };
}

export interface Product {
  sku: string;
  name: string;
  price_inr: number;
  category: string;
}

export interface Catalog {
  merchant_id: string;
  merchant_name: string;
  mcc: string;
  products: Product[];
}

export interface ApiState {
  mandate: Mandate;
  stats: Stats;
  audit_log: AuditEntry[];
}