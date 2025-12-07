/**
 * Structured Logger for Marketing Frontend
 * 
 * Provides structured logging with configurable levels and environment-aware output.
 * In production, logs are sanitized and formatted for observability.
 * In development, logs include full debug information.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  [key: string]: unknown;
}

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  context?: LogContext;
}

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const isDevelopment = process.env.NODE_ENV === 'development';
const minLevel = isDevelopment ? 'debug' : 'info';

function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[minLevel];
}

function sanitizeContext(context: LogContext): LogContext {
  const sanitized: LogContext = {};
  const sensitiveKeys = ['password', 'token', 'secret', 'key', 'authorization', 'cookie'];
  
  for (const [key, value] of Object.entries(context)) {
    const lowerKey = key.toLowerCase();
    if (sensitiveKeys.some(sk => lowerKey.includes(sk))) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = sanitizeContext(value as LogContext);
    } else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
}

function formatEntry(entry: LogEntry): string {
  const prefix = `[${entry.level.toUpperCase()}]`;
  const ctx = entry.context ? ` ${JSON.stringify(sanitizeContext(entry.context))}` : '';
  return `${prefix} ${entry.message}${ctx}`;
}

function log(level: LogLevel, message: string, context?: LogContext): void {
  if (!shouldLog(level)) return;
  
  const entry: LogEntry = {
    level,
    message,
    timestamp: new Date().toISOString(),
    context,
  };
  
  const formatted = formatEntry(entry);
  
  switch (level) {
    case 'debug':
      if (isDevelopment) console.debug(formatted);
      break;
    case 'info':
      console.info(formatted);
      break;
    case 'warn':
      console.warn(formatted);
      break;
    case 'error':
      console.error(formatted);
      break;
  }
}

export const logger = {
  debug: (message: string, context?: LogContext) => log('debug', message, context),
  info: (message: string, context?: LogContext) => log('info', message, context),
  warn: (message: string, context?: LogContext) => log('warn', message, context),
  error: (message: string, context?: LogContext) => log('error', message, context),
};

export default logger;
