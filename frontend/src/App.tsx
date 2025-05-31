import React from 'react'
import HousePlanForm from './components/HousePlanForm'

function App() {
  const handleGenerate = () => {
    // Handle the generated SVG if needed
    console.log('House plan generated')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="bg-white/80 backdrop-blur-sm shadow-sm border-b border-gray-100">
        <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center">
                <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent">
                View AI
              </h1>
            </div>
            <p className="text-sm text-gray-500">House Plan Generator</p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-12 sm:px-6 lg:px-8">
        <div className="px-4 sm:px-0">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">
              Design Your Dream Home
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Generate beautiful and functional house plans with our AI-powered design tool. 
              Customize every aspect of your future home with just a few clicks.
            </p>
          </div>
          <HousePlanForm onGenerate={handleGenerate} />
        </div>
      </main>

      <footer className="mt-16 py-8 border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            © 2024 View AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App