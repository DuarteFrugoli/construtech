import DOMPurify from 'dompurify';

interface HousePlanPreviewProps {
  svgContent: string | null
}

export default function HousePlanPreview({ svgContent }: HousePlanPreviewProps) {
  if (!svgContent) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] bg-slate-50 dark:bg-slate-800 rounded-lg border-2 border-dashed border-slate-300 dark:border-slate-700">
        <svg
          className="w-16 h-16 text-slate-400 dark:text-slate-600 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
          />
        </svg>
        <p className="text-slate-500 dark:text-slate-400 text-center">
          Your house plan will appear here
        </p>
      </div>
    )
  }

  return (
    <div className="relative w-full h-[400px] bg-white dark:bg-slate-800 rounded-lg overflow-hidden">
      <div
        className="w-full h-full"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(svgContent) }}
      />
      <div className="absolute bottom-4 right-4">
        <button
          onClick={() => {
            const blob = new Blob([svgContent], { type: 'image/svg+xml' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'house-plan.svg'
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
          }}
          className="btn-secondary flex items-center space-x-2"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          <span>Download SVG</span>
        </button>
      </div>
    </div>
  )
} 