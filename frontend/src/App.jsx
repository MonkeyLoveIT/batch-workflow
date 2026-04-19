import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import WorkflowList from './views/WorkflowList'
import WorkflowEditor from './views/WorkflowEditor'
import History from './views/History'
import './App.css'

function App() {
  const [currentView, setCurrentView] = useState('list')
  const [editingWorkflow, setEditingWorkflow] = useState(null)

  const handleEdit = (workflow) => {
    setEditingWorkflow(workflow)
    setCurrentView('editor')
  }

  const handleNew = () => {
    setEditingWorkflow(null)
    setCurrentView('editor')
  }

  const handleBack = () => {
    setEditingWorkflow(null)
    setCurrentView('list')
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Batch Workflow</h1>
        <nav>
          <button
            className={currentView === 'list' ? 'active' : ''}
            onClick={() => setCurrentView('list')}
          >
            工作流
          </button>
          <button
            className={currentView === 'editor' ? 'active' : ''}
            onClick={handleNew}
          >
            新建
          </button>
          <button
            className={currentView === 'history' ? 'active' : ''}
            onClick={() => setCurrentView('history')}
          >
            历史
          </button>
        </nav>
      </header>

      <main className="main">
        {currentView === 'list' && (
          <WorkflowList onEdit={handleEdit} onNew={handleNew} />
        )}
        {currentView === 'editor' && (
          <WorkflowEditor workflow={editingWorkflow} onBack={handleBack} />
        )}
        {currentView === 'history' && (
          <History />
        )}
      </main>
    </div>
  )
}

export default App
