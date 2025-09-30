import { CopilotKit } from '@copilotkit/react-core'
import { CopilotSidebar } from '@copilotkit/react-ui'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { I18nextProvider } from 'react-i18next'
import i18n from './i18n'

// Layout components (to be implemented)
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <I18nextProvider i18n={i18n}>
        <CopilotKit url="/api/mcp">
          <Router>
            <div className="flex h-screen">
              <CopilotSidebar
                instructions="You are an AI assistant helping with Amharic document processing. You can help users upload documents, track processing progress, search through processed documents, and export results."
                labels={{
                  title: "Document Assistant",
                  initial: "How can I help you with your Amharic documents today?",
                }}
              >
                <Layout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    {/* Additional routes will be added during implementation */}
                  </Routes>
                </Layout>
              </CopilotSidebar>
            </div>
          </Router>
        </CopilotKit>
      </I18nextProvider>
    </QueryClientProvider>
  )
}

export default App