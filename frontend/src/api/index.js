import axios from 'axios'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
})

// Workflow APIs
export const listWorkflows = () => api.get('/workflows').then(r => r.data)

export const listFolders = () => api.get('/workflows/folders').then(r => r.data)

export const createFolder = (path) => api.post('/workflows/folders', { path }).then(r => r.data)

export const deleteFolder = (path) => api.delete(`/workflows/folders/${encodeURIComponent(path)}`).then(r => r.data)

export const renameFolder = (path, newName) => api.put(`/workflows/folders/${encodeURIComponent(path)}`, { new_name: newName }).then(r => r.data)

export const getWorkflow = (id) => api.get(`/workflows/${id}`).then(r => r.data)

export const createWorkflow = (data) => api.post('/workflows', data).then(r => r.data)

export const updateWorkflow = (id, data) => api.put(`/workflows/${id}`, data).then(r => r.data)

export const deleteWorkflow = (id) => api.delete(`/workflows/${id}`).then(r => r.data)

export const executeWorkflow = (id) => api.post(`/workflows/${id}/execute`).then(r => r.data)

export const getWorkflowStatus = (id) => api.get(`/workflows/${id}/status`).then(r => r.data)

export const stopWorkflow = (id) => api.post(`/workflows/${id}/stop`).then(r => r.data)

export const exportWorkflow = (id) => api.get(`/workflows/export/${id}`).then(r => r.data)

export const importWorkflow = (file) => {
  const formData = new FormData()
  formData.append('file', file, file.name)
  return api.post('/workflows/import', formData).then(r => r.data)
}

// Plugin APIs
export const getPluginTypes = () => api.get('/plugins/types').then(r => r.data)

export const listPlugins = () => api.get('/plugins/list').then(r => r.data)

// History APIs
export const listExecutions = (workflowId) => {
  const params = workflowId ? { workflow_id: workflowId } : {}
  return api.get('/history', { params }).then(r => r.data)
}

export const getExecution = (id) => api.get(`/history/${id}`).then(r => r.data)

export const getStats = () => api.get('/history/stats').then(r => r.data)

export default api
