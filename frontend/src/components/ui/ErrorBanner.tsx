interface ErrorBannerProps {
  message: string
  onDismiss?: () => void
}

export default function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 dark:border-red-800 dark:bg-red-900/20">
      <div className="flex items-center justify-between">
        <p className="text-sm text-red-600 dark:text-red-400">{message}</p>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="ml-4 text-sm text-red-400 hover:text-red-600 dark:hover:text-red-300 cursor-pointer"
            aria-label="Dismiss error"
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  )
}
