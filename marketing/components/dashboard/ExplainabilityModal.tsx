"use client";

import { useState, useEffect } from "react";
import { Info, TrendingUp, TrendingDown, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface SHAPExplanation {
  event_id: number;
  horizon: string;
  feature_contributions: Record<string, number>;
  top_factors: Array<{ factor: string; contribution: number; direction: string }>;
  shap_summary: string;
  model_version: string;
}

interface ExplainabilityModalProps {
  eventId: number;
  open: boolean;
  onClose: () => void;
  horizon?: string;
}

export function ExplainabilityModal({ eventId, open, onClose, horizon = "1d" }: ExplainabilityModalProps) {
  const [explanation, setExplanation] = useState<SHAPExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedHorizon, setSelectedHorizon] = useState(horizon);
  
  useEffect(() => {
    if (open && eventId) {
      loadExplanation();
    }
  }, [open, eventId, selectedHorizon]);
  
  const loadExplanation = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`/api/proxy/explainability/event/${eventId}?horizon=${selectedHorizon}`);
      if (!response.ok) throw new Error("Failed to load explanation");
      setExplanation(await response.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const maxContribution = explanation ? 
    Math.max(...Object.values(explanation.feature_contributions).map(Math.abs)) : 0;
  
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Info className="h-5 w-5 text-[--primary]" />
            Why This Score?
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="flex gap-2">
            {["1d", "7d", "30d"].map((h) => (
              <Button 
                key={h} 
                size="sm" 
                variant={selectedHorizon === h ? "default" : "outline"}
                onClick={() => setSelectedHorizon(h)}
              >
                {h}
              </Button>
            ))}
          </div>
          
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-[--primary]" />
            </div>
          )}
          
          {error && (
            <div className="text-[--error] text-sm py-4">{error}</div>
          )}
          
          {explanation && !loading && (
            <>
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-[--muted]">Key Factors</h3>
                {explanation.top_factors.map((factor, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    {factor.direction === "positive" ? (
                      <TrendingUp className="h-4 w-4 text-[--success]" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-[--error]" />
                    )}
                    <span className="text-sm capitalize text-[--text]">{factor.factor.replace(/_/g, " ")}</span>
                    <div className="flex-1 h-2 bg-[--surface-glass] rounded overflow-hidden">
                      <div 
                        className={`h-full ${factor.direction === "positive" ? "bg-[--success]" : "bg-[--error]"}`}
                        style={{ width: `${Math.abs(factor.contribution) / maxContribution * 100}%` }}
                      />
                    </div>
                    <span className={`text-xs font-mono ${factor.direction === "positive" ? "text-[--success]" : "text-[--error]"}`}>
                      {factor.contribution > 0 ? "+" : ""}{(factor.contribution * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
              
              <div className="bg-[--surface-muted] rounded-lg p-4">
                <h3 className="text-sm font-semibold text-[--muted] mb-2">Analysis</h3>
                <p className="text-sm text-[--text]">{explanation.shap_summary}</p>
              </div>
              
              <div className="text-xs text-[--muted] text-right">
                Model: {explanation.model_version}
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
