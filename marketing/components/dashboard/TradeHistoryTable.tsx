'use client';

import { useState, useMemo } from 'react';
import { ArrowUpDown, TrendingUp, TrendingDown } from 'lucide-react';

interface Trade {
  id: number;
  ticker: string;
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  shares: number;
  return_pct: number;
  profit_loss: number;
  event_type?: string;
}

interface TradeHistoryTableProps {
  trades: Trade[];
  loading?: boolean;
}

type SortField = 'ticker' | 'entry_date' | 'exit_date' | 'return_pct' | 'profit_loss';
type SortDirection = 'asc' | 'desc';

export function TradeHistoryTable({ trades, loading }: TradeHistoryTableProps) {
  const [sortField, setSortField] = useState<SortField>('entry_date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [filterTicker, setFilterTicker] = useState('');
  const [filterProfitable, setFilterProfitable] = useState<'all' | 'profit' | 'loss'>('all');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedAndFilteredTrades = useMemo(() => {
    let filtered = [...trades];

    if (filterTicker) {
      filtered = filtered.filter(t => 
        t.ticker.toLowerCase().includes(filterTicker.toLowerCase())
      );
    }

    if (filterProfitable === 'profit') {
      filtered = filtered.filter(t => t.profit_loss > 0);
    } else if (filterProfitable === 'loss') {
      filtered = filtered.filter(t => t.profit_loss < 0);
    }

    filtered.sort((a, b) => {
      let aVal: any = a[sortField];
      let bVal: any = b[sortField];

      if (sortField === 'entry_date' || sortField === 'exit_date') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      }

      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return filtered;
  }, [trades, sortField, sortDirection, filterTicker, filterProfitable]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400"></div>
      </div>
    );
  }

  if (!trades || trades.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-[--muted]">No trades to display</p>
        <p className="text-sm text-[--muted] mt-2">Run a backtest to see trade history</p>
      </div>
    );
  }

  const SortIcon = ({ field }: { field: SortField }) => (
    <ArrowUpDown 
      className={`h-4 w-4 ml-1 inline ${sortField === field ? 'text-emerald-400' : 'text-[--muted]'}`}
    />
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  };

  const formatCurrency = (value: number) => {
    return value.toLocaleString(undefined, { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Filter by ticker..."
          value={filterTicker}
          onChange={(e) => setFilterTicker(e.target.value)}
          className="px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text] text-sm"
        />
        <select
          value={filterProfitable}
          onChange={(e) => setFilterProfitable(e.target.value as any)}
          className="px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text] text-sm"
        >
          <option value="all">All Trades</option>
          <option value="profit">Profitable Only</option>
          <option value="loss">Losses Only</option>
        </select>
        <div className="text-sm text-[--muted] flex items-center">
          Showing {sortedAndFilteredTrades.length} of {trades.length} trades
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th 
                className="text-left py-3 px-4 font-semibold text-[--text] cursor-pointer hover:bg-white/5"
                onClick={() => handleSort('ticker')}
              >
                Ticker <SortIcon field="ticker" />
              </th>
              <th 
                className="text-left py-3 px-4 font-semibold text-[--text] cursor-pointer hover:bg-white/5"
                onClick={() => handleSort('entry_date')}
              >
                Entry Date <SortIcon field="entry_date" />
              </th>
              <th 
                className="text-left py-3 px-4 font-semibold text-[--text] cursor-pointer hover:bg-white/5"
                onClick={() => handleSort('exit_date')}
              >
                Exit Date <SortIcon field="exit_date" />
              </th>
              <th className="text-right py-3 px-4 font-semibold text-[--text]">
                Entry Price
              </th>
              <th className="text-right py-3 px-4 font-semibold text-[--text]">
                Exit Price
              </th>
              <th className="text-right py-3 px-4 font-semibold text-[--text]">
                Shares
              </th>
              <th 
                className="text-right py-3 px-4 font-semibold text-[--text] cursor-pointer hover:bg-white/5"
                onClick={() => handleSort('return_pct')}
              >
                Return % <SortIcon field="return_pct" />
              </th>
              <th 
                className="text-right py-3 px-4 font-semibold text-[--text] cursor-pointer hover:bg-white/5"
                onClick={() => handleSort('profit_loss')}
              >
                P/L <SortIcon field="profit_loss" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedAndFilteredTrades.map((trade) => (
              <tr 
                key={trade.id} 
                className="border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <td className="py-3 px-4 font-semibold text-[--text]">
                  {trade.ticker}
                </td>
                <td className="py-3 px-4 text-[--muted]">
                  {formatDate(trade.entry_date)}
                </td>
                <td className="py-3 px-4 text-[--muted]">
                  {formatDate(trade.exit_date)}
                </td>
                <td className="py-3 px-4 text-right text-[--text]">
                  {formatCurrency(trade.entry_price)}
                </td>
                <td className="py-3 px-4 text-right text-[--text]">
                  {formatCurrency(trade.exit_price)}
                </td>
                <td className="py-3 px-4 text-right text-[--muted]">
                  {trade.shares}
                </td>
                <td className={`py-3 px-4 text-right font-semibold flex items-center justify-end gap-1 ${
                  trade.return_pct > 0 ? 'text-green-400' : trade.return_pct < 0 ? 'text-red-400' : 'text-[--muted]'
                }`}>
                  {trade.return_pct > 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : trade.return_pct < 0 ? (
                    <TrendingDown className="h-3 w-3" />
                  ) : null}
                  {trade.return_pct > 0 ? '+' : ''}{trade.return_pct.toFixed(2)}%
                </td>
                <td className={`py-3 px-4 text-right font-semibold ${
                  trade.profit_loss > 0 ? 'text-green-400' : trade.profit_loss < 0 ? 'text-red-400' : 'text-[--muted]'
                }`}>
                  {trade.profit_loss > 0 ? '+' : ''}{formatCurrency(trade.profit_loss)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
