"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ApiKey {
  id: number;
  masked_key: string;
  plan: string;
  status: string;
  monthly_call_limit: number;
  calls_used: number;
  cycle_start: string | null;
  created_at: string | null;
  last_used_at: string | null;
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRotateDialog, setShowRotateDialog] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [rotating, setRotating] = useState(false);

  const loadKeys = async () => {
    try {
      const response = await fetch("/api/proxy/keys", {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setKeys(data.keys || []);
      }
    } catch (error) {
      console.error("Failed to load API keys:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKeys();
  }, []);

  const handleCreateKey = async () => {
    setRotating(true);
    try {
      const response = await fetch("/api/proxy/keys/create", {
        method: "POST",
        credentials: "include",
      });
      
      if (response.ok) {
        const data = await response.json();
        setNewKey(data.raw_key);
        setShowRotateDialog(true);
        await loadKeys();
      } else {
        const error = await response.json();
        alert(`Failed to create key: ${error.detail || "Unknown error"}`);
      }
    } catch (error) {
      alert("Failed to create API key. Please try again.");
    } finally {
      setRotating(false);
    }
  };

  const handleRotateKey = async () => {
    setRotating(true);
    try {
      const response = await fetch("/api/proxy/keys/rotate", {
        method: "POST",
        credentials: "include",
      });
      
      if (response.ok) {
        const data = await response.json();
        setNewKey(data.raw_key);
        setShowRotateDialog(true);
        await loadKeys();
      } else {
        const error = await response.json();
        alert(`Failed to rotate key: ${error.detail || "Unknown error"}`);
      }
    } catch (error) {
      alert("Failed to rotate API key. Please try again.");
    } finally {
      setRotating(false);
    }
  };

  const copyToClipboard = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      alert("API key copied to clipboard");
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
      window.location.href = "/";
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getUsagePercentage = (key: ApiKey) => {
    return Math.round((key.calls_used / key.monthly_call_limit) * 100);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white p-8">
        <div className="max-w-4xl mx-auto">
          <p className="text-gray-400">Loading API keys...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">API Keys</h1>
            <p className="text-gray-400">
              Manage your Impact Radar API keys for programmatic access
            </p>
          </div>
          <Button
            onClick={handleLogout}
            variant="outline"
            className="border-zinc-700 hover:bg-zinc-800"
          >
            Log Out
          </Button>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
          {keys.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-400 mb-6">
                Generate your first API key to access the Impact Radar API programmatically.
              </p>
              <Button
                onClick={handleCreateKey}
                disabled={rotating}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {rotating ? "Generating..." : "Generate API Key"}
              </Button>
              <p className="text-xs text-gray-500 mt-4">
                API keys are available for Pro and Team plans only.
              </p>
            </div>
          ) : (
            <>
              {keys.map((key) => (
                <div key={key.id} className="mb-6 pb-6 border-b border-zinc-800 last:border-0">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <code className="text-sm bg-zinc-800 px-3 py-1 rounded font-mono">
                          {key.masked_key}
                        </code>
                        <span className={`text-xs px-2 py-1 rounded ${
                          key.status === "active" 
                            ? "bg-green-900/30 text-green-400" 
                            : "bg-red-900/30 text-red-400"
                        }`}>
                          {key.status}
                        </span>
                        <span className="text-xs px-2 py-1 rounded bg-blue-900/30 text-blue-400">
                          {key.plan.toUpperCase()}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Created</p>
                          <p className="text-gray-300">{formatDate(key.created_at)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Last Used</p>
                          <p className="text-gray-300">{formatDate(key.last_used_at)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mb-3">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">Usage this cycle</span>
                      <span className="text-gray-300">
                        {key.calls_used.toLocaleString()} / {key.monthly_call_limit.toLocaleString()} calls
                        ({getUsagePercentage(key)}%)
                      </span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          getUsagePercentage(key) >= 90
                            ? "bg-red-500"
                            : getUsagePercentage(key) >= 75
                            ? "bg-yellow-500"
                            : "bg-green-500"
                        }`}
                        style={{ width: `${Math.min(getUsagePercentage(key), 100)}%` }}
                      />
                    </div>
                  </div>

                  {key.cycle_start && (
                    <p className="text-xs text-gray-500">
                      Cycle resets on {formatDate(
                        new Date(new Date(key.cycle_start).getTime() + 30 * 24 * 60 * 60 * 1000).toISOString()
                      )}
                    </p>
                  )}
                </div>
              ))}

              <Button
                onClick={handleRotateKey}
                disabled={rotating || keys.every(k => k.status !== "active")}
                className="w-full mt-4 bg-blue-600 hover:bg-blue-700"
              >
                {rotating ? "Rotating..." : "Rotate API Key"}
              </Button>
              <p className="text-xs text-gray-500 mt-2">
                Rotating will revoke your current key and generate a new one.
              </p>
            </>
          )}
        </div>

        <Dialog open={showRotateDialog} onOpenChange={setShowRotateDialog}>
          <DialogContent className="bg-zinc-900 border-zinc-800 text-white">
            <DialogHeader>
              <DialogTitle>New API Key Generated</DialogTitle>
              <DialogDescription className="text-gray-400">
                This key will only be shown once. Store it securely.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="bg-zinc-800 p-4 rounded-lg">
                <code className="text-sm font-mono break-all text-green-400">
                  {newKey}
                </code>
              </div>
              <Button onClick={copyToClipboard} className="w-full">
                Copy to Clipboard
              </Button>
              <p className="text-xs text-gray-500">
                Make sure to save this key somewhere safe. You will not be able to see it again.
              </p>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
