export interface SignalSummary {
  pattern: string
  volume_surge: boolean
  volume_ratio: number
  above_key_mas: boolean
  rsi_14: number
  macd_signal: string
  macd_histogram: number | null
  volatility_contracting: boolean
  pct_from_52w_high: number
  ml_breakout_prob: number
}

export interface Fundamentals {
  eps_growth_yoy: string
  revenue_growth_yoy: string
  peg_ratio: number | null
  catalyst: string
}

export interface BpsResult {
  ticker: string
  breakout_probability_score: number
  conviction: 'HIGH' | 'MEDIUM' | 'WATCH' | 'PASS'
  technical_score: number
  fundamental_score: number
  signal_summary: SignalSummary
  fundamentals: Fundamentals
  risk_flags: string[]
  entry_zone: string
  stop_loss: string
  target_1: string
  target_2: string
  risk_reward: string
  timeframe: string
}

export interface WatchlistAlert {
  ticker: string
  status: 'TRIGGERED' | 'STILL_VALID' | 'BREAKING_DOWN' | 'STOPPED_OUT' | 'PATTERN_EXTENDED'
  urgency: 'HIGH' | 'MEDIUM' | 'LOW'
  current_price: number
  action: string
  updated_bps: number
  notes: string
}

export interface BacktestSummary {
  total_signals: number
  win_rate_t1: number
  stop_out_rate: number
  avg_return_winners_pct: number
  avg_return_losers_pct: number
  expectancy_per_trade_pct: number
  profit_factor: number
  max_drawdown_pct: number
  sharpe_ratio: number
  avg_days_to_resolution: number
  starting_capital: number
  final_capital: number
  total_return_pct: number
  total_pnl_usd: number
  equity_curve: { trade: number; date: string; capital: number }[]
  signals: any[]
}

export interface NewsItem {
  ticker: string
  headline: string
  source: string
  url: string
  sentiment: 'bullish' | 'bearish' | 'neutral'
  published_at: string
}
