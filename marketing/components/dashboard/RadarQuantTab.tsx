"use client";

import { useState, useEffect, useRef } from "react";
import { Sparkles, TrendingUp, AlertCircle, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import { useDashboardModeStore } from "@/stores/dashboardModeStore";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface QuotaInfo {
  remaining: number;
  limit: number;
  resets_at: string;
}

interface AnalyzeResponse {
  analysis: string;
  context_used: {
    events_count: number;
    portfolio_count: number;
    watchlist_count: number;
    stats_count: number;
  };
  metadata: {
    model: string;
    tokens_used: number;
    processing_time: number;
  };
}

export function RadarQuantTab() {
  const { mode } = useDashboardModeStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [quota, setQuota] = useState<QuotaInfo | null>(null);
  const [quotaLoading, setQuotaLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadQuota();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadQuota = async () => {
    try {
      setQuotaLoading(true);
      const res = await fetch("/api/proxy/ai/quota");
      
      if (!res.ok) {
        throw new Error("Failed to load quota information");
      }

      const data = await res.json();
      setQuota(data);
    } catch (err: any) {
      console.error("Failed to load quota:", err);
      setError("Unable to load quota information");
    } finally {
      setQuotaLoading(false);
    }
  };

  const handlePreset = async (question: string) => {
    setInput(question);
    await handleSend(question);
  };

  const handleSend = async (customInput?: string) => {
    const messageText = customInput || input;
    if (!messageText.trim() || loading) return;

    const userMessage: Message = {
      role: "user",
      content: messageText,
      timestamp: new Date().toISOString(),
    };

    // Capture the updated messages array before the async operation
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/proxy/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: updatedMessages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
          context_mode: mode,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Unknown error" }));
        
        if (res.status === 429) {
          throw new Error("Daily quota exceeded. Upgrade your plan for more requests.");
        } else if (res.status === 402) {
          throw new Error("Payment required. Please upgrade your plan.");
        }
        
        throw new Error(errorData.detail || "Failed to get response");
      }

      const data: AnalyzeResponse = await res.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.analysis,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      await loadQuota();
    } catch (err: any) {
      console.error("Chat error:", err);
      setError(err.message || "Failed to send message");
      
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${err.message || "Failed to process your request. Please try again."}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const presetQuestions = [
    "What are the highest impact events in my portfolio?",
    "Show me recent FDA approvals affecting biotech stocks",
    "Summarize earnings events from the past week",
    "What M&A activity should I be aware of?",
  ];

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Image 
              src="/radarquant-logo.png" 
              alt="RadarQuant AI" 
              width={32} 
              height={32} 
              className="rounded-lg"
              priority
              unoptimized
            />
            <h2 className="text-2xl font-bold text-[--text]">RadarQuant AI</h2>
          </div>
          <p className="text-[--muted]">
            Your intelligent assistant for event analysis and market insights
          </p>
        </div>
        
        {/* Quota Display */}
        {!quotaLoading && quota && (
          <div className="bg-[--surface-muted] border border-[--border] rounded-lg px-4 py-2">
            <div className="text-xs text-[--muted] mb-1">Daily Requests</div>
            <div className="text-lg font-semibold text-[--text]">
              {quota.remaining} / {quota.limit}
            </div>
            <div className="text-xs text-[--muted] mt-1">
              Resets {new Date(quota.resets_at).toLocaleTimeString()}
            </div>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 flex gap-3">
        <AlertCircle className="h-5 w-5 text-[--primary] flex-shrink-0 mt-0.5" />
        <div className="text-sm text-[--primary]">
          <strong>Note:</strong> RadarQuant AI analyzes your portfolio, watchlist, and event data.
          It does not provide investment advice. Always verify information with official sources.
        </div>
      </div>

      {/* Chat Container */}
      <div className="bg-[--surface-muted] border border-[--border] rounded-lg overflow-hidden">
        {/* Messages Area */}
        <div className="h-[500px] overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Sparkles className="h-12 w-12 text-[--primary] mb-4" />
              <h3 className="text-xl font-semibold text-[--text] mb-2">
                Start a conversation
              </h3>
              <p className="text-[--muted] mb-6 max-w-md">
                Ask questions about your events, portfolio, or market trends.
                Try one of the suggestions below.
              </p>
              
              {/* Preset Buttons */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
                {presetQuestions.map((question, idx) => (
                  <button
                    key={idx}
                    onClick={() => handlePreset(question)}
                    disabled={loading}
                    className="bg-[--surface-muted] hover:bg-[--surface-hover] border border-[--border] rounded-lg p-4 text-left transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="flex items-start gap-2">
                      <TrendingUp className="h-4 w-4 text-[--primary] flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-[--text]">{question}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((message, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {message.role === "assistant" && (
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-lg overflow-hidden bg-[--primary-light] flex items-center justify-center">
                        <Image 
                          src="/radarquant-logo.png" 
                          alt="RadarQuant AI" 
                          width={32} 
                          height={32}
                          className="object-cover"
                          priority
                          unoptimized
                        />
                      </div>
                    </div>
                  )}
                  
                  <div
                    className={`max-w-[80%] rounded-lg p-4 ${
                      message.role === "user"
                        ? "bg-[--primary-soft] text-[--text]"
                        : "bg-[--surface-muted] border border-[--border] text-[--text]"
                    }`}
                  >
                    <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                    <div className="text-xs text-[--muted] mt-2">
                      {formatTime(message.timestamp)}
                    </div>
                  </div>
                  
                  {message.role === "user" && (
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-[--surface-glass] flex items-center justify-center">
                        <span className="text-sm font-medium text-[--text]">You</span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              
              {loading && (
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-lg overflow-hidden bg-[--primary-light] flex items-center justify-center">
                      <Image 
                        src="/radarquant-logo.png" 
                        alt="RadarQuant AI" 
                        width={32} 
                        height={32}
                        className="object-cover"
                        priority
                        unoptimized
                      />
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] border border-[--border] rounded-lg p-4">
                    <Loader2 className="h-4 w-4 text-[--primary] animate-spin" />
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-[--border] p-4">
          {error && (
            <div className="mb-3 bg-red-500/10 border border-red-500/20 rounded-lg p-3 flex gap-2">
              <AlertCircle className="h-4 w-4 text-[--error] flex-shrink-0 mt-0.5" />
              <span className="text-sm text-[--error]">{error}</span>
            </div>
          )}
          
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about your events, portfolio, or market trends..."
              disabled={loading}
              rows={2}
              className="flex-1 bg-[--surface-muted] border border-[--border] rounded-lg px-4 py-2 text-[--text] placeholder:text-[--muted] focus:outline-none focus:ring-2 focus:ring-[--primary] disabled:opacity-50 disabled:cursor-not-allowed resize-none"
            />
            <Button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="self-end"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          
          <div className="mt-2 text-xs text-[--muted]">
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>
      </div>
    </div>
  );
}
