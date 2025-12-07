"use client";

import { useState, useEffect } from "react";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";

interface GlobalNotification {
  id: number;
  message: string;
  type: string;
  created_at: string;
  expires_at: string;
}

const API_BASE = "/api/proxy";

export function GlobalNotificationBanner() {
  const [notifications, setNotifications] = useState<GlobalNotification[]>([]);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const response = await fetch(`${API_BASE}/admin/notifications/global`);
        if (response.ok) {
          const data = await response.json();
          setNotifications(data);
        }
      } catch (error) {
        console.error("Failed to fetch notifications:", error);
      }
    };

    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000);

    return () => clearInterval(interval);
  }, []);

  const dismissNotification = (id: number) => {
    setDismissed((prev) => new Set([...prev, id]));
  };

  const activeNotifications = notifications.filter(
    (n) => !dismissed.has(n.id)
  );

  if (activeNotifications.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-16 left-0 right-0 z-50 px-4 py-2">
      <div className="max-w-4xl mx-auto space-y-2">
        {activeNotifications.map((notification) => (
          <div
            key={notification.id}
            className={`flex items-center justify-between px-4 py-3 rounded-lg shadow-lg backdrop-blur-sm ${
              notification.type === "success"
                ? "bg-green-500/90 text-white"
                : notification.type === "error"
                ? "bg-red-500/90 text-white"
                : "bg-blue-500/90 text-white"
            }`}
          >
            <div className="flex items-center gap-3">
              {notification.type === "success" ? (
                <CheckCircle className="h-5 w-5 flex-shrink-0" />
              ) : notification.type === "error" ? (
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
              ) : (
                <Info className="h-5 w-5 flex-shrink-0" />
              )}
              <span className="font-medium">{notification.message}</span>
            </div>
            <button
              onClick={() => dismissNotification(notification.id)}
              className="p-1 hover:bg-white/20 rounded-full transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
