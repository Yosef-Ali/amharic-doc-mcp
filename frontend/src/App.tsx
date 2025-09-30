import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import { AccessibilityProvider } from './components/AccessibilityProvider'

function App() {
  return (
    <AccessibilityProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
          </Routes>
        </Layout>
      </Router>
    </AccessibilityProvider>
  )
}

export default App
