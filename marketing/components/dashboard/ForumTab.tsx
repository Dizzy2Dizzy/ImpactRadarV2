"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { format, formatDistanceToNow } from "date-fns";

interface UserInfo {
  id: number;
  email: string;
  username: string;
  plan: string;
  avatar_url: string | null;
}

interface ReactionInfo {
  emoji: string;
  count: number;
  user_ids: number[];
}

interface ForumMessage {
  id: number;
  content: string;
  image_url: string | null;
  is_ai_response: boolean;
  ai_prompt: string | null;
  parent_message_id: number | null;
  reply_to: ForumMessage | null;
  created_at: string;
  edited_at: string | null;
  user: UserInfo;
  reactions: ReactionInfo[];
}

interface ForumAccessResponse {
  has_access: boolean;
  plan: string;
  message: string | null;
}

interface ForumUser {
  id: number;
  username: string;
  plan: string;
}

const EMOJI_OPTIONS = [
  { emoji: "thumbs_up", display: "👍" },
  { emoji: "rocket", display: "🚀" },
  { emoji: "fire", display: "🔥" },
  { emoji: "chart_increasing", display: "📈" },
  { emoji: "check", display: "✅" },
  { emoji: "star", display: "⭐" },
];

const PLAN_COLORS: Record<string, string> = {
  free: "bg-gray-500",
  pro: "bg-blue-500",
  team: "bg-purple-500",
  admin: "bg-red-500",
  enterprise: "bg-amber-500",
  ai: "bg-gradient-to-r from-emerald-500 to-teal-500",
};

const PLAN_LABELS: Record<string, string> = {
  free: "FREE",
  pro: "PRO",
  team: "TEAM",
  admin: "ADMIN",
  enterprise: "ENTERPRISE",
  ai: "AI",
};

const POPULAR_GIFS = [
  { url: "https://media.giphy.com/media/YnkMcHgNIMW4Yfber6/giphy.gif", label: "Stonks" },
  { url: "https://media.giphy.com/media/67ThRZlYBvibtdF9JH/giphy.gif", label: "Money Rain" },
  { url: "https://media.giphy.com/media/trN9ht5RlE3Dcwavg2/giphy.gif", label: "Rocket" },
  { url: "https://media.giphy.com/media/n98BI9GgS6KxbplK1Q/giphy.gif", label: "Money" },
  { url: "https://media.giphy.com/media/Y2ZUWLrTy63j9T6qrK/giphy.gif", label: "Printer" },
  { url: "https://media.giphy.com/media/JtBZm3Getg3dqxK0zP/giphy.gif", label: "Charts" },
  { url: "https://media.giphy.com/media/QMHoU66sBXqqLqYvGO/giphy.gif", label: "This is Fine" },
  { url: "https://media.giphy.com/media/oNFP9kltPi7fp8TUAV/giphy.gif", label: "Moon" },
  { url: "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif", label: "Let's Go" },
  { url: "https://media.giphy.com/media/a5viI92PAF89q/giphy.gif", label: "Thinking" },
  { url: "https://media.giphy.com/media/d0DdMCREQChi3jGymW/giphy.gif", label: "Diamond" },
  { url: "https://media.giphy.com/media/YkYt0FzMNPJkFnSCxJ/giphy.gif", label: "Buy Dip" },
  { url: "https://media.giphy.com/media/Ogak8XuKHLs6PYcqlp/giphy.gif", label: "Bull" },
  { url: "https://media.giphy.com/media/Yl5aO3gdVfsQ0/giphy.gif", label: "Bear" },
  { url: "https://media.giphy.com/media/g9582DNuQppxC/giphy.gif", label: "Celebrate" },
  { url: "https://media.giphy.com/media/d2lcHJTG5Tscg/giphy.gif", label: "Sad" },
  { url: "https://media.giphy.com/media/26ufdipQqU2lhNA4g/giphy.gif", label: "Mind Blown" },
  { url: "https://media.giphy.com/media/CaiVJuZGvR8HK/giphy.gif", label: "Thumbs Up" },
  { url: "https://media.giphy.com/media/XsUtdIeJ0MWMo/giphy.gif", label: "Facepalm" },
  { url: "https://media.giphy.com/media/l4JyOCNEfXvVYEqB2/giphy.gif", label: "Wow" },
  { url: "https://media.giphy.com/media/3oKIPdGYRGEby6jQwE/giphy.gif", label: "Waiting" },
  { url: "https://media.giphy.com/media/l1J9EdzfOSgfyueLm/giphy.gif", label: "Wolf" },
  { url: "https://media.giphy.com/media/lptjRBxFKCJmFoibP3/giphy.gif", label: "HODL" },
  { url: "https://media.giphy.com/media/5efT9uLuaJoM3lGKIt/giphy.gif", label: "Profit" },
  { url: "https://media.giphy.com/media/3oriO04qxVReM5rJEA/giphy.gif", label: "Rich" },
  { url: "https://media.giphy.com/media/3o6ZtpxSZbQRRnwCKQ/giphy.gif", label: "Genius" },
  { url: "https://media.giphy.com/media/67ThRZlYBvibtdF9JH/giphy.gif", label: "Cash" },
  { url: "https://media.giphy.com/media/xT9IgN8YKRhByRBzMI/giphy.gif", label: "Trading" },
  { url: "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif", label: "Perfect" },
  { url: "https://media.giphy.com/media/l0HlvtIPzPdt2usKs/giphy.gif", label: "Approved" },
  { url: "https://media.giphy.com/media/5VKbvrjxpVJCM/giphy.gif", label: "Panic" },
  { url: "https://media.giphy.com/media/l41YtZOb9EUABnuqA/giphy.gif", label: "Shocked" },
  { url: "https://media.giphy.com/media/3o7TKTDn976rzVgky4/giphy.gif", label: "Yes" },
  { url: "https://media.giphy.com/media/l0Iy8hSJalxmgTOF2/giphy.gif", label: "No" },
  { url: "https://media.giphy.com/media/3ohzdIuqJoo8QdKlnW/giphy.gif", label: "Excited" },
  { url: "https://media.giphy.com/media/l3q2K5jinAlChoCLS/giphy.gif", label: "Boom" },
  { url: "https://media.giphy.com/media/3oKIPf3C7HqqYBVcCk/giphy.gif", label: "Cheers" },
  { url: "https://media.giphy.com/media/l46CyJmS9KUbokzsI/giphy.gif", label: "Smart" },
  { url: "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif", label: "Clapping" },
  { url: "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif", label: "Agree" },
];

export function ForumTab() {
  const [hasAccess, setHasAccess] = useState<boolean | null>(null);
  const [accessMessage, setAccessMessage] = useState<string>("");
  const [messages, setMessages] = useState<ForumMessage[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState<number | null>(null);
  const [replyTo, setReplyTo] = useState<ForumMessage | null>(null);
  const [showGifPicker, setShowGifPicker] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [forumUsers, setForumUsers] = useState<ForumUser[]>([]);
  const [showMentionList, setShowMentionList] = useState(false);
  const [mentionFilter, setMentionFilter] = useState("");
  const [mentionCursorPos, setMentionCursorPos] = useState(0);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const prevMessageCountRef = useRef<number>(0);
  const isInitialLoadRef = useRef<boolean>(true);

  const isNearBottom = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return true;
    const threshold = 100;
    return container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  }, []);

  const scrollToBottom = useCallback((force = false) => {
    if (force || isNearBottom()) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [isNearBottom]);

  const checkAccess = useCallback(async () => {
    try {
      const response = await fetch("/api/proxy/forum/access");
      if (response.ok) {
        const data: ForumAccessResponse = await response.json();
        setHasAccess(data.has_access);
        setAccessMessage(data.message || "");
      } else {
        setHasAccess(false);
        setAccessMessage("Unable to verify forum access. Please try again later.");
      }
    } catch (err) {
      console.error("Error checking forum access:", err);
      setHasAccess(false);
      setAccessMessage("Unable to verify forum access. Please try again later.");
    }
  }, []);

  const fetchCurrentUser = useCallback(async () => {
    try {
      const response = await fetch("/api/proxy/account/summary");
      if (response.ok) {
        const data = await response.json();
        setCurrentUserId(data.id);
      }
    } catch (err) {
      console.error("Error fetching current user:", err);
    }
  }, []);

  const fetchMessages = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    try {
      const response = await fetch("/api/proxy/forum/messages?limit=100");
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages);
        setError(null);
      } else if (response.status === 403) {
        setHasAccess(false);
      }
    } catch (err) {
      console.error("Error fetching messages:", err);
      setError("Failed to load messages");
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      const response = await fetch("/api/proxy/forum/users");
      if (response.ok) {
        const data = await response.json();
        setForumUsers(data.users || []);
      }
    } catch (err) {
      console.error("Error fetching users:", err);
    }
  }, []);

  useEffect(() => {
    const initialize = async () => {
      await checkAccess();
      await fetchCurrentUser();
    };
    initialize();
  }, [checkAccess, fetchCurrentUser]);

  useEffect(() => {
    if (hasAccess) {
      fetchMessages();
      fetchUsers();

      pollIntervalRef.current = setInterval(() => {
        fetchMessages(false);
      }, 3000);

      return () => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
        }
      };
    }
  }, [hasAccess, fetchMessages, fetchUsers]);

  useEffect(() => {
    const currentCount = messages.length;
    const prevCount = prevMessageCountRef.current;
    
    if (currentCount > 0) {
      if (isInitialLoadRef.current) {
        scrollToBottom(true);
        isInitialLoadRef.current = false;
      } else if (currentCount > prevCount) {
        if (isNearBottom()) {
          scrollToBottom(true);
        }
      }
    }
    
    prevMessageCountRef.current = currentCount;
  }, [messages, scrollToBottom, isNearBottom]);

  const handleSendMessage = async () => {
    if ((!newMessage.trim() && !selectedImage) || isSending) return;

    setIsSending(true);
    try {
      const response = await fetch("/api/proxy/forum/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: newMessage.trim(),
          image_url: selectedImage,
          parent_message_id: replyTo?.id || null,
        }),
      });

      if (response.ok) {
        setNewMessage("");
        setSelectedImage(null);
        setReplyTo(null);
        await fetchMessages(false);
        scrollToBottom(true);
        inputRef.current?.focus();
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to send message");
      }
    } catch (err) {
      console.error("Error sending message:", err);
      setError("Failed to send message");
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
    if (e.key === "Escape") {
      setShowMentionList(false);
      setShowGifPicker(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    const cursorPos = e.target.selectionStart || 0;
    setNewMessage(value);

    const textBeforeCursor = value.substring(0, cursorPos);
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/);
    
    if (mentionMatch) {
      setShowMentionList(true);
      setMentionFilter(mentionMatch[1].toLowerCase());
      setMentionCursorPos(cursorPos - mentionMatch[0].length);
    } else {
      setShowMentionList(false);
    }
  };

  const insertMention = (username: string) => {
    const before = newMessage.substring(0, mentionCursorPos);
    const after = newMessage.substring(inputRef.current?.selectionStart || mentionCursorPos);
    const afterClean = after.replace(/^@\w*/, "");
    setNewMessage(`${before}@${username} ${afterClean}`);
    setShowMentionList(false);
    inputRef.current?.focus();
  };

  const handleReaction = async (messageId: number, emoji: string) => {
    try {
      const response = await fetch(`/api/proxy/forum/messages/${messageId}/reactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ emoji }),
      });

      if (response.ok) {
        await fetchMessages(false);
      }
    } catch (err) {
      console.error("Error adding reaction:", err);
    }
    setShowEmojiPicker(null);
  };

  const handleDeleteMessage = async (messageId: number) => {
    if (!confirm("Are you sure you want to delete this message?")) return;

    try {
      const response = await fetch(`/api/proxy/forum/messages/${messageId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        await fetchMessages(false);
      }
    } catch (err) {
      console.error("Error deleting message:", err);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleGifSelect = (gifUrl: string) => {
    setSelectedImage(gifUrl);
    setShowGifPicker(false);
  };

  const formatMessageTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

    if (diffInHours < 24) {
      return formatDistanceToNow(date, { addSuffix: true });
    }
    return format(date, "MMM d, yyyy 'at' h:mm a");
  };

  const getAvatarInitial = (username: string) => {
    return username.charAt(0).toUpperCase();
  };

  const getAvatarColor = (userId: number) => {
    const colors = [
      "from-blue-500 to-blue-600",
      "from-purple-500 to-purple-600",
      "from-emerald-500 to-emerald-600",
      "from-amber-500 to-amber-600",
      "from-pink-500 to-pink-600",
      "from-cyan-500 to-cyan-600",
      "from-red-500 to-red-600",
      "from-indigo-500 to-indigo-600",
    ];
    return colors[userId % colors.length];
  };

  const filteredMentionUsers = forumUsers.filter(
    (user) =>
      user.username.toLowerCase().includes(mentionFilter) ||
      mentionFilter === ""
  );

  if (hasAccess === null) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-180px)] min-h-[600px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!hasAccess) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-180px)] min-h-[600px] text-center px-4">
        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center mb-4">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            <path d="M8 10h.01" />
            <path d="M12 10h.01" />
            <path d="M16 10h.01" />
          </svg>
        </div>
        <h3 className="text-xl font-bold text-[--text] mb-2">Community Forum</h3>
        <p className="text-[--muted] mb-6 max-w-md">
          {accessMessage || "Join our community to discuss strategies, share insights, and get help from @Quant AI."}
        </p>
        <button
          onClick={() => window.location.href = "/#pricing"}
          className="px-6 py-3 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium hover:from-emerald-600 hover:to-teal-600 transition-all"
        >
          Upgrade to Pro
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-180px)] min-h-[700px] bg-[--panel] rounded-xl border border-[--border] overflow-hidden">
      <div className="px-4 py-3 border-b border-[--border] flex items-center justify-between bg-[--surface-strong]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h2 className="text-sm font-semibold text-[--text]">Community Chat</h2>
        </div>
        <div className="flex items-center gap-2 text-xs text-[--muted]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Live
          </span>
        </div>
      </div>

      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-[--muted] mb-2">No messages yet</p>
            <p className="text-xs text-[--muted]">Be the first to start a conversation!</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`group flex gap-3 hover:bg-[--surface-muted] p-2 -mx-2 rounded-lg transition-colors ${
                message.is_ai_response ? "bg-emerald-500/5" : ""
              }`}
            >
              <div
                className={`w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center text-white font-bold text-sm shadow-lg ${
                  message.is_ai_response
                    ? "bg-gradient-to-br from-emerald-500 to-teal-500"
                    : `bg-gradient-to-br ${getAvatarColor(message.user.id)}`
                }`}
              >
                {message.is_ai_response ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 8V4H8" />
                    <rect x="8" y="8" width="8" height="8" rx="2" />
                    <path d="M12 20v-4h4" />
                    <path d="M20 12h-4v-4" />
                    <path d="M4 12h4v4" />
                  </svg>
                ) : (
                  getAvatarInitial(message.user.username)
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`font-semibold text-sm ${message.is_ai_response ? "text-emerald-400" : "text-[--text]"}`}>
                    {message.is_ai_response ? "Quant" : message.user.username}
                  </span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold text-white ${
                      PLAN_COLORS[message.user.plan] || "bg-gray-500"
                    }`}
                  >
                    {PLAN_LABELS[message.user.plan] || message.user.plan.toUpperCase()}
                  </span>
                  <span className="text-xs text-[--muted]">
                    {formatMessageTime(message.created_at)}
                  </span>
                  {message.edited_at && (
                    <span className="text-xs text-[--muted] italic">(edited)</span>
                  )}
                </div>

                {message.reply_to && (
                  <div className="mt-1 mb-2 pl-3 border-l-2 border-blue-500/50 bg-blue-500/5 rounded-r py-1.5 px-2">
                    <div className="text-xs text-blue-400 font-medium">
                      Replying to @{message.reply_to.user.username}
                    </div>
                    <div className="text-xs text-[--muted] truncate max-w-md">
                      {message.reply_to.content.substring(0, 100)}
                      {message.reply_to.content.length > 100 ? "..." : ""}
                    </div>
                  </div>
                )}

                {message.ai_prompt && message.is_ai_response && (
                  <div className="mt-1 mb-2 text-xs text-emerald-400/70 italic">
                    Responding to: {message.ai_prompt.substring(0, 100)}
                    {message.ai_prompt.length > 100 ? "..." : ""}
                  </div>
                )}

                <div className="mt-1 text-sm text-[--text] whitespace-pre-wrap break-words">
                  {message.content}
                </div>

                {message.image_url && (
                  <div className="mt-2">
                    <img
                      src={message.image_url}
                      alt="Shared image"
                      className="max-w-sm max-h-64 rounded-lg border border-[--border]"
                      loading="lazy"
                    />
                  </div>
                )}

                <div className="mt-2 flex items-center gap-2 flex-wrap">
                  {message.reactions.map((reaction) => {
                    const emojiDisplay = EMOJI_OPTIONS.find((e) => e.emoji === reaction.emoji)?.display || reaction.emoji;
                    const hasReacted = currentUserId ? reaction.user_ids.includes(currentUserId) : false;
                    return (
                      <button
                        key={reaction.emoji}
                        onClick={() => handleReaction(message.id, reaction.emoji)}
                        className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors ${
                          hasReacted
                            ? "bg-blue-500/20 border border-blue-500/50 text-blue-400"
                            : "bg-[--surface-muted] hover:bg-[--surface-hover] text-[--muted]"
                        }`}
                      >
                        <span>{emojiDisplay}</span>
                        <span>{reaction.count}</span>
                      </button>
                    );
                  })}

                  <button
                    onClick={() => setReplyTo(message)}
                    className="opacity-0 group-hover:opacity-100 flex items-center justify-center w-7 h-7 rounded-md bg-[--surface-muted] hover:bg-[--surface-hover] text-[--muted] transition-all"
                    title="Reply"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="9 17 4 12 9 7" />
                      <path d="M20 18v-2a4 4 0 0 0-4-4H4" />
                    </svg>
                  </button>

                  <div className="relative">
                    <button
                      onClick={() => setShowEmojiPicker(showEmojiPicker === message.id ? null : message.id)}
                      className="opacity-0 group-hover:opacity-100 flex items-center justify-center w-7 h-7 rounded-md bg-[--surface-muted] hover:bg-[--surface-hover] text-[--muted] transition-all"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M8 14s1.5 2 4 2 4-2 4-2" />
                        <line x1="9" y1="9" x2="9.01" y2="9" />
                        <line x1="15" y1="9" x2="15.01" y2="9" />
                      </svg>
                    </button>

                    {showEmojiPicker === message.id && (
                      <div className="absolute bottom-full left-0 mb-1 p-2 bg-[--surface-strong] rounded-lg border border-[--border] shadow-xl flex gap-1 z-10">
                        {EMOJI_OPTIONS.map((option) => (
                          <button
                            key={option.emoji}
                            onClick={() => handleReaction(message.id, option.emoji)}
                            className="w-8 h-8 flex items-center justify-center rounded hover:bg-[--surface-hover] transition-colors"
                          >
                            {option.display}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {currentUserId === message.user.id && !message.is_ai_response && (
                    <button
                      onClick={() => handleDeleteMessage(message.id)}
                      className="opacity-0 group-hover:opacity-100 flex items-center justify-center w-7 h-7 rounded-md bg-[--surface-muted] hover:bg-red-500/20 text-[--muted] hover:text-red-400 transition-all"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 6h18" />
                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/20 text-red-400 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {replyTo && (
        <div className="px-4 py-2 bg-blue-500/10 border-t border-blue-500/20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 17 4 12 9 7" />
              <path d="M20 18v-2a4 4 0 0 0-4-4H4" />
            </svg>
            <span className="text-sm text-blue-400">
              Replying to <span className="font-medium">@{replyTo.user.username}</span>
            </span>
            <span className="text-xs text-[--muted] truncate max-w-xs">
              {replyTo.content.substring(0, 50)}...
            </span>
          </div>
          <button
            onClick={() => setReplyTo(null)}
            className="text-[--muted] hover:text-[--text] transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>
      )}

      {selectedImage && (
        <div className="px-4 py-2 bg-[--surface-strong] border-t border-[--border] flex items-center gap-3">
          <div className="relative">
            <img
              src={selectedImage}
              alt="Selected"
              className="h-16 rounded-lg border border-[--border]"
            />
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center text-xs hover:bg-red-600 transition-colors"
            >
              ×
            </button>
          </div>
          <span className="text-sm text-[--muted]">Image ready to send</span>
        </div>
      )}

      <div className="px-4 py-3 border-t border-[--border] bg-[--surface-strong] relative">
        {showGifPicker && (
          <div className="absolute bottom-full left-4 right-4 mb-2 p-3 bg-[--surface-strong] rounded-xl border border-[--border] shadow-2xl z-20">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-[--text]">Popular GIFs</h3>
              <button
                onClick={() => setShowGifPicker(false)}
                className="text-[--muted] hover:text-[--text] transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 6 6 18" />
                  <path d="m6 6 12 12" />
                </svg>
              </button>
            </div>
            <div className="grid grid-cols-5 gap-2 max-h-64 overflow-y-auto">
              {POPULAR_GIFS.map((gif, index) => (
                <button
                  key={index}
                  onClick={() => handleGifSelect(gif.url)}
                  className="relative rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-500 transition-all group aspect-square"
                >
                  <img
                    src={gif.url}
                    alt={gif.label}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="text-[10px] text-white font-medium text-center px-1">{gif.label}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {showMentionList && filteredMentionUsers.length > 0 && (
          <div className="absolute bottom-full left-4 mb-2 w-64 p-2 bg-[--surface-strong] rounded-xl border border-[--border] shadow-2xl z-20 max-h-48 overflow-y-auto">
            {filteredMentionUsers.slice(0, 8).map((user) => (
              <button
                key={user.id}
                onClick={() => insertMention(user.username)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[--surface-hover] transition-colors text-left"
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold bg-gradient-to-br ${getAvatarColor(user.id)}`}>
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <span className="text-sm text-[--text]">@{user.username}</span>
                <span className={`ml-auto px-1.5 py-0.5 rounded text-[9px] font-bold text-white ${PLAN_COLORS[user.plan] || "bg-gray-500"}`}>
                  {PLAN_LABELS[user.plan] || user.plan.toUpperCase()}
                </span>
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2 items-center">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="h-10 w-10 flex-shrink-0 rounded-lg bg-[--input-bg] border border-[--border] flex items-center justify-center text-[--muted] hover:text-[--text] hover:bg-[--surface-hover] transition-colors"
            title="Upload Image"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="9" cy="9" r="2" />
              <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
            </svg>
          </button>
          <button
            onClick={() => setShowGifPicker(!showGifPicker)}
            className={`h-10 w-10 flex-shrink-0 rounded-lg border border-[--border] flex items-center justify-center transition-colors ${
              showGifPicker ? "bg-blue-500 text-white" : "bg-[--input-bg] text-[--muted] hover:text-[--text] hover:bg-[--surface-hover]"
            }`}
            title="Send GIF"
          >
            <span className="text-xs font-bold">GIF</span>
          </button>
          
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={newMessage}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type a message... Use @ to mention users"
              rows={1}
              className="w-full h-10 px-4 py-2.5 rounded-lg bg-[--input-bg] border border-[--border] text-[--text] placeholder-[#787b86] focus:outline-none focus:border-blue-500/50 resize-none transition-colors"
            />
            {newMessage.toLowerCase().includes("@quant") && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-emerald-400">
                AI will respond
              </div>
            )}
          </div>
          <button
            onClick={handleSendMessage}
            disabled={(!newMessage.trim() && !selectedImage) || isSending}
            className="h-10 px-4 flex-shrink-0 rounded-lg bg-blue-500 text-white font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {isSending ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m22 2-7 20-4-9-9-4Z" />
                <path d="M22 2 11 13" />
              </svg>
            )}
            <span className="text-sm">Send</span>
          </button>
        </div>
        <div className="mt-2 text-xs text-[--muted]">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
