import { Component, type ReactNode, type ErrorInfo } from 'react';
import { AlertTriangle, RefreshCw, Home, ChevronDown, ChevronUp, Copy, ArrowLeft, Check } from 'lucide-react';

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
  copied: boolean;
  errorTimestamp: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      copied: false,
      errorTimestamp: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error, errorTimestamp: new Date().toISOString() };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('SwissBuildingOS Error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private getErrorSummary(): string {
    const { error, errorInfo, errorTimestamp } = this.state;
    const lines = [`Timestamp: ${errorTimestamp}`, `Error: ${error?.message ?? 'Unknown error'}`];
    if (error?.stack) lines.push(`\nStack:\n${error.stack}`);
    if (errorInfo?.componentStack) lines.push(`\nComponent Stack:\n${errorInfo.componentStack}`);
    return lines.join('\n');
  }

  private handleCopy = () => {
    navigator.clipboard.writeText(this.getErrorSummary()).then(() => {
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    });
  };

  render() {
    if (this.state.hasError) {
      const { error, showDetails, copied, errorTimestamp, errorInfo } = this.state;
      return (
        <div data-testid="error-boundary" className="flex items-center justify-center min-h-[400px] p-8">
          <div className="text-center max-w-lg">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
              <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">Something went wrong</h2>
            <p className="text-slate-600 dark:text-slate-400 mb-2">{error?.message}</p>
            {errorTimestamp && <p className="text-xs text-slate-400 dark:text-slate-500 mb-6">{errorTimestamp}</p>}
            <div className="flex items-center justify-center gap-3 mb-4">
              <button
                data-testid="error-boundary-reload"
                onClick={() => window.location.reload()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                Reload
              </button>
              <a
                data-testid="error-boundary-home"
                href="/today"
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                <Home className="h-4 w-4" />
                Accueil
              </a>
              <button
                data-testid="error-boundary-copy"
                onClick={this.handleCopy}
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copied' : 'Copy error'}
              </button>
            </div>
            {(error?.stack || errorInfo?.componentStack) && (
              <div>
                <button
                  data-testid="error-boundary-toggle-details"
                  onClick={() => this.setState({ showDetails: !showDetails })}
                  className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                >
                  {showDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  {showDetails ? 'Hide details' : 'Show details'}
                </button>
                {showDetails && (
                  <pre
                    data-testid="error-boundary-details"
                    className="mt-3 p-4 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-left text-xs text-slate-600 dark:text-slate-400 overflow-auto max-h-64 whitespace-pre-wrap"
                  >
                    {error?.stack}
                    {errorInfo?.componentStack && `\n\nComponent Stack:${errorInfo.componentStack}`}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

interface PageErrorBoundaryProps {
  children: ReactNode;
  pageName?: string;
}

interface PageErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
  copied: boolean;
  retryCount: number;
  errorTimestamp: string | null;
}

export class PageErrorBoundary extends Component<PageErrorBoundaryProps, PageErrorBoundaryState> {
  constructor(props: PageErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      copied: false,
      retryCount: 0,
      errorTimestamp: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<PageErrorBoundaryState> {
    return { hasError: true, error, errorTimestamp: new Date().toISOString() };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`PageErrorBoundary${this.props.pageName ? ` [${this.props.pageName}]` : ''}:`, error, errorInfo);
    this.setState({ errorInfo });
  }

  private getErrorSummary(): string {
    const { error, errorInfo, errorTimestamp } = this.state;
    const lines = [
      `Page: ${this.props.pageName ?? 'Unknown'}`,
      `Timestamp: ${errorTimestamp}`,
      `Error: ${error?.message ?? 'Unknown error'}`,
    ];
    if (error?.stack) lines.push(`\nStack:\n${error.stack}`);
    if (errorInfo?.componentStack) lines.push(`\nComponent Stack:\n${errorInfo.componentStack}`);
    return lines.join('\n');
  }

  private handleCopy = () => {
    navigator.clipboard.writeText(this.getErrorSummary()).then(() => {
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    });
  };

  private handleRetry = () => {
    this.setState((prev) => ({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      copied: false,
      retryCount: prev.retryCount + 1,
      errorTimestamp: null,
    }));
  };

  private handleGoBack = () => {
    window.history.back();
  };

  render() {
    if (this.state.hasError) {
      const { error, showDetails, copied, retryCount, errorTimestamp, errorInfo } = this.state;
      return (
        <div data-testid="page-error-boundary" className="flex items-center justify-center py-16 px-4">
          <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-8 text-center max-w-lg shadow-sm">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
              <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
              {this.props.pageName
                ? `Error loading ${this.props.pageName}`
                : 'An error occurred / Une erreur est survenue'}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">{error?.message}</p>
            {errorTimestamp && <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">{errorTimestamp}</p>}
            {retryCount > 0 && (
              <p data-testid="page-error-retry-count" className="text-xs text-amber-600 dark:text-amber-400 mb-4">
                Retried {retryCount} {retryCount === 1 ? 'time' : 'times'}
              </p>
            )}
            <div className="flex items-center justify-center gap-3 mb-4">
              <button
                data-testid="page-error-retry"
                onClick={this.handleRetry}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                Retry
              </button>
              <button
                data-testid="page-error-back"
                onClick={this.handleGoBack}
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-sm rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Go back
              </button>
              <button
                data-testid="page-error-copy"
                onClick={this.handleCopy}
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-sm rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            {(error?.stack || errorInfo?.componentStack) && (
              <div>
                <button
                  data-testid="page-error-toggle-details"
                  onClick={() => this.setState({ showDetails: !showDetails })}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                >
                  {showDetails ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  {showDetails ? 'Hide details' : 'Show details'}
                </button>
                {showDetails && (
                  <pre
                    data-testid="page-error-details"
                    className="mt-3 p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-left text-xs text-slate-600 dark:text-slate-400 overflow-auto max-h-48 whitespace-pre-wrap"
                  >
                    {error?.stack}
                    {errorInfo?.componentStack && `\n\nComponent Stack:${errorInfo.componentStack}`}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
