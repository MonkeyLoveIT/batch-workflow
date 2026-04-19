import React, { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listWorkflows, listFolders, createFolder, deleteFolder, deleteWorkflow, executeWorkflow, importWorkflow, getWorkflow, updateWorkflow, renameFolder } from '../api'

// Build tree structure from flat folder list
const buildFolderTree = (folders) => {
  const tree = []
  const folderMap = {}

  folders.forEach(f => {
    folderMap[f.path] = { ...f, children: [], workflows: [] }
  })

  folders.forEach(f => {
    const node = folderMap[f.path]
    if (f.path.includes('/')) {
      const parentPath = f.path.substring(0, f.path.lastIndexOf('/'))
      if (folderMap[parentPath]) {
        folderMap[parentPath].children.push(node)
      } else {
        tree.push(node)
      }
    } else {
      tree.push(node)
    }
  })

  return tree
}

function WorkflowListView({ onEdit, onNew }) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showNewFolderModal, setShowNewFolderModal] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [showRenameFolderModal, setShowRenameFolderModal] = useState(false)
  const [renameFolderPath, setRenameFolderPath] = useState('')
  const [renameFolderName, setRenameFolderName] = useState('')
  const [showExportConfirm, setShowExportConfirm] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showDeleteFolderConfirm, setShowDeleteFolderConfirm] = useState(false)
  const [deleteFolderInfo, setDeleteFolderInfo] = useState(null)
  const [showMoveModal, setShowMoveModal] = useState(false)
  const [moveTargetFolder, setMoveTargetFolder] = useState('')
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [dragOverId, setDragOverId] = useState(null)
  const [dragSourceId, setDragSourceId] = useState(null)
  const [contextMenu, setContextMenu] = useState(null)
  const [folderKey, setFolderKey] = useState(0)

  // Close context menu on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && contextMenu) {
        setContextMenu(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [contextMenu])

  const { data: workflows = [], isLoading, error } = useQuery({
    queryKey: ['workflows'],
    queryFn: listWorkflows,
  })

  const { data: folderData = [] } = useQuery({
    queryKey: ['folders', folderKey],
    queryFn: listFolders,
    staleTime: 0,
  })

  const updateWorkflowMutation = useMutation({
    mutationFn: ({ id, data }) => updateWorkflow(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['workflows'])
      setFolderKey(k => k + 1)
    },
  })

  const deleteWorkflowMutation = useMutation({
    mutationFn: deleteWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries(['workflows'])
      setFolderKey(k => k + 1)
    },
  })

  const createFolderMutation = useMutation({
    mutationFn: createFolder,
    onSuccess: () => {
      setFolderKey(k => k + 1)
      setShowNewFolderModal(false)
      setNewFolderName('')
    },
    onError: (err) => {
      alert(err.response?.data?.detail || '创建文件夹失败')
    }
  })

  const deleteFolderMutation = useMutation({
    mutationFn: deleteFolder,
    onSuccess: () => {
      setFolderKey(k => k + 1)
      queryClient.invalidateQueries(['workflows'])
    },
    onError: (err) => {
      alert(err.response?.data?.detail || '删除文件夹失败')
    }
  })

  const renameFolderMutation = useMutation({
    mutationFn: ({ path, newName }) => renameFolder(path, newName),
    onSuccess: () => {
      setFolderKey(k => k + 1)
      queryClient.invalidateQueries(['workflows'])
      setShowRenameFolderModal(false)
      setRenameFolderPath('')
      setRenameFolderName('')
    },
    onError: (err) => {
      alert(err.response?.data?.detail || '重命名文件夹失败')
    }
  })

  const executeMutation = useMutation({
    mutationFn: executeWorkflow,
    onSuccess: () => queryClient.invalidateQueries(['executions']),
  })

  const [importFiles, setImportFiles] = useState(null)
  const [showImportConfirm, setShowImportConfirm] = useState(false)

  // Group workflows by folder
  const workflowsByFolder = {}
  workflows.forEach(w => {
    const folder = w.folder || ''
    if (!workflowsByFolder[folder]) workflowsByFolder[folder] = []
    workflowsByFolder[folder].push(w)
  })

  // Build folder tree with workflows
  const folderTree = (() => {
    const tree = buildFolderTree(folderData)
    tree.forEach(folder => {
      const addWorkflowsToFolder = (node, path) => {
        node.workflows = workflowsByFolder[path] || []
        node.children.forEach(child => addWorkflowsToFolder(child, child.path))
      }
      addWorkflowsToFolder(folder, folder.path)
    })
    return tree
  })()

  // Get all folder paths for dropdowns
  const allFolderPaths = (() => {
    const paths = []
    const collectPaths = (nodes, parent = '') => {
      nodes.forEach(n => {
        const fullPath = parent ? `${parent}/${n.name}` : n.name
        paths.push(fullPath)
        if (n.children.length > 0) {
          collectPaths(n.children, fullPath)
        }
      })
    }
    collectPaths(folderTree)
    return paths
  })()

  // Calculate folder info for deletion
  const getFolderDeleteInfo = (node) => {
    let subFolderCount = 0
    let workflowCount = workflowsByFolder[node.path]?.length || 0
    const countSubFolders = (n) => {
      n.children.forEach(child => {
        subFolderCount++
        workflowCount += workflowsByFolder[child.path]?.length || 0
        countSubFolders(child)
      })
    }
    if (node.children.length > 0) {
      countSubFolders(node)
    }
    return { subFolderCount, workflowCount }
  }

  // Flatten tree for rendering with visibility state
  const [collapsedPaths, setCollapsedPaths] = useState(new Set())

  const toggleCollapse = (path) => {
    const newSet = new Set(collapsedPaths)
    if (newSet.has(path)) {
      newSet.delete(path)
    } else {
      newSet.add(path)
    }
    setCollapsedPaths(newSet)
  }

  // Render tree recursively
  const renderTree = (nodes, depth = 0) => {
    return nodes.map(node => {
      const nodeId = node.path || '__root__'
      const isCollapsed = collapsedPaths.has(node.path)
      const indent = depth * 20
      const folderWorkflows = workflowsByFolder[node.path] || []
      const isDragOver = dragOverId === nodeId

      return (
        <React.Fragment key={nodeId}>
          {/* Folder row */}
          <tr
            style={{
              background: isDragOver ? '#e8e8f4' : '#f5f5f5',
              cursor: 'pointer',
              transition: 'background 0.15s'
            }}
            onDragOver={(e) => {
              e.preventDefault()
              if (dragSourceId && dragSourceId !== nodeId) {
                setDragOverId(nodeId)
              }
            }}
            onDragLeave={() => setDragOverId(null)}
            onDrop={(e) => {
              e.preventDefault()
              if (dragSourceId) {
                const wfId = parseInt(dragSourceId)
                const wf = workflows.find(w => w.id === wfId)
                if (wf && wf.folder !== node.path) {
                  updateWorkflowMutation.mutate({ id: wfId, data: { ...wf, folder: node.path } })
                }
              }
              setDragOverId(null)
              setDragSourceId(null)
            }}
            onClick={() => toggleCollapse(node.path)}
            onContextMenu={(e) => {
              e.preventDefault()
              setContextMenu({ x: e.clientX, y: e.clientY, node })
            }}
          >
            <td style={{ paddingLeft: `${indent}px`, width: '24px' }}>
              <span style={{ fontSize: '12px', color: '#666' }}>
                {isCollapsed ? '▶' : '▼'}
              </span>
            </td>
            <td style={{ paddingLeft: '4px' }}>
              <span style={{ fontSize: '14px' }}>📁</span>
            </td>
            <td colSpan={4} style={{ padding: '8px 0' }}>
              <span style={{ fontWeight: 500, fontSize: '14px' }}>{node.name}</span>
              <span style={{ marginLeft: '12px', color: '#999', fontSize: '12px' }}>
                ({folderWorkflows.length} 个工作流)
              </span>
            </td>
          </tr>
          {/* Child folders */}
          {!isCollapsed && node.children.length > 0 && renderTree(node.children, depth + 1)}
          {/* Workflows in folder */}
          {!isCollapsed && folderWorkflows.map(wf => (
            <tr
              key={wf.id}
              draggable
              onDragStart={(e) => {
                setDragSourceId(String(wf.id))
                e.dataTransfer.setData('text/plain', String(wf.id))
              }}
              style={{
                background: '#fff',
                cursor: 'grab',
                transition: 'background 0.15s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f5'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#fff'}
            >
              <td style={{ paddingLeft: `${indent + 24}px`, width: '24px' }}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(wf.id)}
                  onChange={(e) => {
                    e.stopPropagation()
                    const newSet = new Set(selectedIds)
                    if (e.target.checked) {
                      newSet.add(wf.id)
                    } else {
                      newSet.delete(wf.id)
                    }
                    setSelectedIds(newSet)
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
              </td>
              <td style={{ paddingLeft: '4px' }}>
                <span style={{ fontSize: '14px' }}>📄</span>
              </td>
              <td style={{ padding: '8px 0' }}>
                <span style={{ fontSize: '14px' }}>{wf.name}</span>
              </td>
              <td style={{ color: '#999', fontSize: '12px' }}>{wf.description || '-'}</td>
              <td style={{ color: '#999', fontSize: '12px', width: '140px' }}>
                {new Date(wf.updated_at).toLocaleDateString()}
              </td>
              <td style={{ width: '200px' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => executeMutation.mutate(wf.id)}
                  style={{ padding: '2px 8px', fontSize: '11px', marginRight: '4px' }}
                >
                  执行
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleEdit(wf)}
                  style={{ padding: '2px 8px', fontSize: '11px', marginRight: '4px' }}
                >
                  编辑
                </button>
                <button
                  className="btn btn-danger"
                  onClick={() => {
                    if (confirm(`删除 "${wf.name}"？`)) {
                      deleteWorkflowMutation.mutate(wf.id)
                    }
                  }}
                  style={{ padding: '2px 8px', fontSize: '11px' }}
                >
                  删除
                </button>
              </td>
            </tr>
          ))}
        </React.Fragment>
      )
    })
  }

  // Root level workflows
  const rootWorkflows = workflowsByFolder[''] || []

  // Filter workflows by search
  const filteredRootWorkflows = rootWorkflows.filter(w =>
    w.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleEdit = async (workflow) => {
    try {
      const fullWorkflow = await getWorkflow(workflow.id)
      onEdit(fullWorkflow)
    } catch (err) {
      alert('加载失败: ' + err.message)
    }
  }

  const handleImport = async () => {
    if (!importFiles || importFiles.length === 0) return
    try {
      let successCount = 0, failCount = 0
      const errors = []
      for (const file of Array.from(importFiles)) {
        try {
          await importWorkflow(file)
          successCount++
        } catch (err) {
          failCount++
          errors.push(`${file.name}: ${err.response?.data?.detail || err.message}`)
        }
      }
      queryClient.invalidateQueries(['workflows'])
      queryClient.invalidateQueries(['folders'])
      setShowImportConfirm(false)
      setImportFiles(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      alert(failCount > 0
        ? `成功 ${successCount}，失败 ${failCount}:\n${errors.join('\n')}`
        : `成功导入 ${successCount} 个工作流`)
    } catch (err) {
      alert('导入失败: ' + err.message)
    }
  }

  const handleExportSelected = async () => {
    if (selectedIds.size === 0) {
      alert('请先选择工作流')
      return
    }
    setShowExportConfirm(true)
  }

  const confirmExport = async () => {
    setShowExportConfirm(false)
    try {
      const { default: JSZip } = await import('jszip')
      const zip = new JSZip()
      for (const wf of workflows.filter(w => selectedIds.has(w.id))) {
        const resp = await fetch(`/api/workflows/export/${wf.id}`)
        const data = await resp.json()
        zip.file(`${wf.name}.yaml`, data.yaml)
      }
      const blob = await zip.generateAsync({ type: 'blob' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `workflows_${Date.now()}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert('导出失败: ' + err.message)
    }
  }

  const handleDeleteSelected = () => {
    if (selectedIds.size === 0) {
      alert('请先选择工作流')
      return
    }
    setShowDeleteConfirm(true)
  }

  const confirmDelete = () => {
    setShowDeleteConfirm(false)
    selectedIds.forEach(id => deleteWorkflowMutation.mutate(id))
    setSelectedIds(new Set())
  }

  const handleMoveSelected = () => {
    if (selectedIds.size === 0) {
      alert('请先选择工作流')
      return
    }
    setMoveTargetFolder('')
    setShowMoveModal(true)
  }

  const confirmMove = () => {
    workflows.filter(w => selectedIds.has(w.id)).forEach(wf => {
      updateWorkflowMutation.mutate({ id: wf.id, data: { ...wf, folder: moveTargetFolder } })
    })
    setShowMoveModal(false)
    setSelectedIds(new Set())
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredRootWorkflows.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredRootWorkflows.map(w => w.id)))
    }
  }

  if (isLoading) return <div style={{ padding: '20px' }}>加载中...</div>
  if (error) return <div style={{ padding: '20px', color: 'red' }}>错误: {error.message}</div>

  return (
    <div style={{ padding: '20px' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>工作流</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="搜索..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ padding: '6px 12px', border: '1px solid #ddd', borderRadius: '6px', width: '180px' }}
          />
          <button className="btn btn-secondary" onClick={() => { setNewFolderName(''); setShowNewFolderModal(true) }}>+ 新建文件夹</button>
          <input type="file" accept=".yaml,.yml" multiple ref={fileInputRef} id="import-file" style={{ display: 'none' }}
            onChange={(e) => { if (e.target.files[0]) { setImportFiles(e.target.files); setShowImportConfirm(true) } }} />
          <label htmlFor="import-file" className="btn btn-secondary" style={{ cursor: 'pointer' }}>导入</label>
          <button className="btn btn-secondary" onClick={handleExportSelected} disabled={selectedIds.size === 0}>
            导出 ({selectedIds.size})
          </button>
          <button className="btn btn-secondary" onClick={handleMoveSelected} disabled={selectedIds.size === 0}>
            移动 ({selectedIds.size})
          </button>
          <button className="btn btn-danger" onClick={handleDeleteSelected} disabled={selectedIds.size === 0}>
            删除 ({selectedIds.size})
          </button>
          <button className="btn btn-primary" onClick={onNew}>+ 新建</button>
        </div>
      </div>

      {/* Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <thead>
          <tr style={{ background: '#f5f5f5' }}>
            <th style={{ padding: '10px 8px', width: '24px', textAlign: 'left' }}>
              <input type="checkbox" checked={selectedIds.size === filteredRootWorkflows.length && filteredRootWorkflows.length > 0} onChange={toggleSelectAll} />
            </th>
            <th style={{ padding: '10px 8px', width: '24px' }}></th>
            <th style={{ padding: '10px 8px', textAlign: 'left' }}>名称</th>
            <th style={{ padding: '10px 8px', textAlign: 'left', color: '#666' }}>描述</th>
            <th style={{ padding: '10px 8px', width: '140px', textAlign: 'left', color: '#666' }}>更新</th>
            <th style={{ padding: '10px 8px', width: '200px', textAlign: 'left', color: '#666' }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {/* Root folder header */}
          <tr style={{ background: '#fafafa', cursor: 'pointer' }}
            onDragOver={(e) => {
              e.preventDefault()
              if (dragSourceId) setDragOverId('__root__')
            }}
            onDragLeave={() => setDragOverId(null)}
            onDrop={(e) => {
              e.preventDefault()
              if (dragSourceId) {
                const wfId = parseInt(dragSourceId)
                const wf = workflows.find(w => w.id === wfId)
                if (wf && wf.folder !== '') {
                  updateWorkflowMutation.mutate({ id: wfId, data: { ...wf, folder: '' } })
                }
              }
              setDragOverId(null)
              setDragSourceId(null)
            }}
            onContextMenu={(e) => {
              e.preventDefault()
              setContextMenu({ x: e.clientX, y: e.clientY, node: { path: '', name: '根目录' } })
            }}
          >
            <td style={{ padding: '8px', width: '24px' }}></td>
            <td style={{ padding: '8px' }}>📁</td>
            <td colSpan={4} style={{ padding: '8px' }}>
              <span style={{ fontWeight: 500 }}>根目录</span>
              <span style={{ marginLeft: '12px', color: '#999', fontSize: '12px' }}>({rootWorkflows.length} 个工作流)</span>
            </td>
          </tr>
          {/* Root workflows */}
          {filteredRootWorkflows.map(wf => (
            <tr
              key={wf.id}
              draggable
              onDragStart={(e) => {
                setDragSourceId(String(wf.id))
                e.dataTransfer.setData('text/plain', String(wf.id))
              }}
              style={{ transition: 'background 0.15s' }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f5'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#fff'}
            >
              <td style={{ padding: '8px 8px 8px 32px', width: '24px' }}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(wf.id)}
                  onChange={(e) => {
                    const newSet = new Set(selectedIds)
                    e.target.checked ? newSet.add(wf.id) : newSet.delete(wf.id)
                    setSelectedIds(newSet)
                  }}
                />
              </td>
              <td style={{ padding: '8px' }}>📄</td>
              <td style={{ padding: '8px 0' }}>{wf.name}</td>
              <td style={{ color: '#999', fontSize: '13px' }}>{wf.description || '-'}</td>
              <td style={{ color: '#999', fontSize: '12px' }}>{new Date(wf.updated_at).toLocaleDateString()}</td>
              <td>
                <button className="btn btn-primary" onClick={() => executeMutation.mutate(wf.id)} style={{ padding: '2px 8px', fontSize: '11px', marginRight: '4px' }}>执行</button>
                <button className="btn btn-secondary" onClick={() => handleEdit(wf)} style={{ padding: '2px 8px', fontSize: '11px', marginRight: '4px' }}>编辑</button>
                <button className="btn btn-danger" onClick={() => { if (confirm(`删除 "${wf.name}"？`)) deleteWorkflowMutation.mutate(wf.id) }} style={{ padding: '2px 8px', fontSize: '11px' }}>删除</button>
              </td>
            </tr>
          ))}
          {/* Folder tree */}
          {folderTree.map(folder => renderTree([folder], 0))}
        </tbody>
      </table>

      {/* Context Menu */}
      {contextMenu && (
        <>
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 999, background: 'transparent' }} onClick={() => setContextMenu(null)} />
          <div style={{
            position: 'fixed',
            top: `${contextMenu.y}px`,
            left: `${contextMenu.x}px`,
            background: 'white',
            borderRadius: '6px',
            boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
            padding: '4px 0',
            minWidth: '160px',
            zIndex: 1000
          }}>
            {contextMenu.node.path === '' && (
              <div style={{ padding: '8px 16px', cursor: 'pointer', fontSize: '13px' }}
                onClick={() => {
                  setContextMenu(null)
                  setNewFolderName('')
                  setShowNewFolderModal(true)
                }}>
                📁 新建文件夹
              </div>
            )}
            {contextMenu.node.path !== '' && (
              <>
                <div style={{ padding: '8px 16px', cursor: 'pointer', fontSize: '13px' }}
                  onClick={() => {
                    setRenameFolderPath(contextMenu.node.path)
                    setRenameFolderName(contextMenu.node.name)
                    setShowRenameFolderModal(true)
                    setContextMenu(null)
                  }}>
                  ✏️ 重命名
                </div>
                <div style={{ padding: '8px 16px', cursor: 'pointer', fontSize: '13px', color: '#dc3545' }}
                  onClick={() => {
                    const info = getFolderDeleteInfo(contextMenu.node)
                    setDeleteFolderInfo({ ...contextMenu.node, ...info })
                    setShowDeleteFolderConfirm(true)
                    setContextMenu(null)
                  }}>
                  🗑️ 删除
                </div>
              </>
            )}
          </div>
        </>
      )}

      {/* Rename Folder Modal */}
      {showRenameFolderModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: '8px', padding: '24px', minWidth: '360px' }}>
            <h3 style={{ marginBottom: '16px' }}>重命名文件夹</h3>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', color: '#666', fontSize: '13px' }}>新名称</label>
              <input
                type="text"
                value={renameFolderName}
                onChange={(e) => setRenameFolderName(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && renameFolderName.trim()) {
                    renameFolderMutation.mutate({ path: renameFolderPath, newName: renameFolderName.trim() })
                  }
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => { setShowRenameFolderModal(false); setRenameFolderPath(''); setRenameFolderName('') }}>取消</button>
              <button className="btn btn-primary" onClick={() => {
                if (!renameFolderName.trim()) return
                renameFolderMutation.mutate({ path: renameFolderPath, newName: renameFolderName.trim() })
              }}>重命名</button>
            </div>
          </div>
        </div>
      )}

      {/* New Folder Modal */}
      {showNewFolderModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: '8px', padding: '24px', minWidth: '360px' }}>
            <h3 style={{ marginBottom: '16px' }}>新建文件夹</h3>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', color: '#666', fontSize: '13px' }}>文件夹名称</label>
              <input
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="请输入名称"
                style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newFolderName.trim()) {
                    createFolderMutation.mutate(newFolderName.trim())
                  }
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => { setShowNewFolderModal(false); setNewFolderName('') }}>取消</button>
              <button type="button" className="btn btn-primary" onClick={() => {
                const name = newFolderName.trim()
                if (!name) return
                createFolderMutation.mutate(name)
              }}>创建</button>
            </div>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExportConfirm && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: '8px', padding: '24px', minWidth: '360px' }}>
            <h3 style={{ marginBottom: '16px' }}>导出 {selectedIds.size} 个工作流</h3>
            <div style={{ marginBottom: '16px', maxHeight: '200px', overflow: 'auto' }}>
              {workflows.filter(w => selectedIds.has(w.id)).map(wf => (
                <div key={wf.id} style={{ padding: '4px 0', color: '#666' }}>{wf.name}</div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowExportConfirm(false)}>取消</button>
              <button className="btn btn-primary" onClick={confirmExport}>导出</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteConfirm && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: '8px', padding: '24px', minWidth: '360px' }}>
            <h3 style={{ marginBottom: '16px', color: '#dc3545' }}>确认删除 {selectedIds.size} 个工作流</h3>
            <p style={{ marginBottom: '16px', color: '#666' }}>删除后不可恢复，确定要删除吗？</p>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowDeleteConfirm(false)}>取消</button>
              <button className="btn btn-danger" onClick={confirmDelete}>删除</button>
            </div>
          </div>
        </div>
      )}

      {/* Move Modal */}
      {showMoveModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: '8px', padding: '24px', minWidth: '360px' }}>
            <h3 style={{ marginBottom: '16px' }}>移动到文件夹</h3>
            <select value={moveTargetFolder} onChange={(e) => setMoveTargetFolder(e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px', marginBottom: '16px' }}>
              <option value="">根目录</option>
              {allFolderPaths.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowMoveModal(false)}>取消</button>
              <button className="btn btn-primary" onClick={confirmMove}>移动</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Folder Confirm Modal */}
      {showDeleteFolderConfirm && deleteFolderInfo && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: '8px', padding: '24px', minWidth: '400px' }}>
            <h3 style={{ marginBottom: '16px', color: '#dc3545' }}>确认删除文件夹</h3>
            <div style={{ marginBottom: '16px' }}>
              <p style={{ marginBottom: '8px' }}>确定要删除文件夹 <strong>"{deleteFolderInfo.name}"</strong> 吗？</p>
              {deleteFolderInfo.subFolderCount > 0 && (
                <p style={{ color: '#666', fontSize: '13px' }}>包含 {deleteFolderInfo.subFolderCount} 个子文件夹</p>
              )}
              {deleteFolderInfo.workflowCount > 0 && (
                <p style={{ color: '#666', fontSize: '13px' }}>包含 {deleteFolderInfo.workflowCount} 个工作流</p>
              )}
              <p style={{ marginTop: '12px', color: '#dc3545', fontSize: '13px' }}>删除后，所有子文件夹和工作流都将被删除！</p>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => { setShowDeleteFolderConfirm(false); setDeleteFolderInfo(null) }}>取消</button>
              <button className="btn btn-danger" onClick={() => {
                // Delete all workflows in this folder and subfolders
                const deleteWorkflowsInFolder = (node) => {
                  const wfs = workflowsByFolder[node.path] || []
                  wfs.forEach(wf => deleteWorkflowMutation.mutate(wf.id))
                  node.children.forEach(child => deleteWorkflowsInFolder(child))
                }
                deleteWorkflowsInFolder(deleteFolderInfo)
                // Delete all subfolders
                const deleteSubFolders = (node) => {
                  node.children.forEach(child => {
                    deleteFolderMutation.mutate(child.path)
                    deleteSubFolders(child)
                  })
                }
                deleteSubFolders(deleteFolderInfo)
                // Delete the folder itself
                deleteFolderMutation.mutate(deleteFolderInfo.path)
                setShowDeleteFolderConfirm(false)
                setDeleteFolderInfo(null)
              }}>删除</button>
            </div>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImportConfirm && importFiles && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: '8px', padding: '24px', minWidth: '360px' }}>
            <h3 style={{ marginBottom: '16px' }}>导入 {importFiles.length} 个文件</h3>
            <div style={{ marginBottom: '16px', maxHeight: '200px', overflow: 'auto' }}>
              {Array.from(importFiles).map((f, i) => <div key={i} style={{ padding: '4px 0', color: '#666' }}>{f.name}</div>)}
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => { setShowImportConfirm(false); setImportFiles(null); if (fileInputRef.current) fileInputRef.current.value = '' }}>取消</button>
              <button className="btn btn-primary" onClick={handleImport}>导入</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default WorkflowListView
