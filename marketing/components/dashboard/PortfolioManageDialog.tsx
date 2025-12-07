'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Trash2 } from 'lucide-react';

interface Portfolio {
  id: number;
  name: string;
  created_at: string;
  positions_count: number;
}

interface PortfolioManageDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPortfolioDeleted?: () => void;
}

export function PortfolioManageDialog({ 
  open, 
  onOpenChange,
  onPortfolioDeleted
}: PortfolioManageDialogProps) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    if (open) {
      fetchPortfolios();
    }
  }, [open]);

  const fetchPortfolios = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/proxy/portfolio/list', {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch portfolios');
      }

      const data = await response.json();
      setPortfolios(data);
    } catch (error) {
      console.error('Error fetching portfolios:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (portfolioId: number) => {
    if (!confirm('Are you sure you want to delete this portfolio?')) {
      return;
    }

    setDeletingId(portfolioId);
    try {
      const response = await fetch(`/api/proxy/portfolio/${portfolioId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to delete portfolio');
      }

      setPortfolios(portfolios.filter(p => p.id !== portfolioId));
      
      if (onPortfolioDeleted) {
        onPortfolioDeleted();
      }
    } catch (error) {
      console.error('Error deleting portfolio:', error);
      alert('Failed to delete portfolio. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Manage Portfolios</DialogTitle>
          <DialogDescription>
            View and manage your uploaded portfolios
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-3">
          {isLoading ? (
            <div className="text-center py-8 text-[--muted]">
              Loading portfolios...
            </div>
          ) : portfolios.length === 0 ? (
            <div className="text-center py-8 text-[--muted]">
              No portfolios uploaded yet. Upload a CSV file to get started.
            </div>
          ) : (
            portfolios.map((portfolio) => (
              <div
                key={portfolio.id}
                className="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition-colors"
              >
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-[--text]">
                    {portfolio.name}
                  </h4>
                  <p className="text-xs text-[--muted] mt-1">
                    {portfolio.positions_count} positions • Uploaded {formatDate(portfolio.created_at)}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(portfolio.id)}
                  disabled={deletingId === portfolio.id}
                  className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Delete portfolio"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
