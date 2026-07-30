export interface User {
  id: number;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
}

export interface Instrument {
  id: number;
  symbol: string;
  name: string;
  exchange: string;
  sector: string | null;
  instrument_type: string;
  currency: string;
  is_active: boolean;
}

export interface Quote {
  symbol: string;
  name: string;
  exchange: string;
  last_price: number;
  change: number;
  change_pct: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
}

export interface OHLCVPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Watchlist {
  id: number;
  user_id: number;
  name: string;
  item_count: number;
  items?: WatchlistItem[];
  created_at: string;
  updated_at: string;
}

export interface WatchlistItem {
  id: number;
  symbol: string;
  added_at: string;
}

export interface Portfolio {
  id: number;
  user_id: number;
  name: string;
  initial_cash: number;
  cash_balance: number;
  is_paper: boolean;
  created_at: string;
  updated_at: string;
}

export interface Holding {
  id: number;
  symbol: string;
  quantity: number;
  average_price: number;
  current_price: number | null;
  cost_basis: number | null;
  market_value: number | null;
  unrealised_pnl: number | null;
  unrealised_pnl_pct: number | null;
}

export interface Transaction {
  id: number;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  total_value: number;
  executed_at: string;
}

export interface PortfolioSummary {
  portfolio: Portfolio;
  cash_balance: number;
  invested_cost: number;
  market_value: number;
  equity: number;
  unrealised_pnl: number;
  unrealised_pnl_pct: number;
  holdings: Holding[];
  recent_transactions: Transaction[];
}

export interface Signal {
  symbol: string;
  timestamp: string;
  direction: "BUY" | "SELL" | "HOLD";
  confidence: number;
  features_used: string[];
  reasoning: string[];
}

export interface Analysis {
  symbol: string;
  name: string;
  exchange: string;
  indicators: Record<string, number | null>;
  signal: Signal;
  explanation: {
    summary: string;
    reasoning: string[];
    disclaimer: string;
  };
}

export interface BacktestResult {
  total_return: number;
  total_return_pct: number;
  num_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown_pct: number;
  initial_capital: number;
  final_equity: number;
  equity_curve: { timestamp: string; equity: number; price: number }[];
  trades: { timestamp: string; side: string; price: number; quantity: number; cost?: number; proceeds?: number }[];
}

export interface Alert {
  id: number;
  symbol: string;
  alert_type: string;
  threshold_value: number | null;
  is_active: boolean;
  created_at: string;
}

export interface RiskAnalysis {
  total_equity: number;
  cash_balance: number;
  num_positions: number;
  concentration: {
    max_single_position_pct: number;
    positions: { symbol: string; market_value: number; sector: string; weight_pct: number }[];
  };
  sector_concentration: Record<string, { value: number; weight_pct: number }>;
  position_sizing: { max_position_pct: number; suggested_max_per_symbol: number };
  recommendations: string[];
}
