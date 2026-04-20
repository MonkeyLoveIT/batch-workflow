import React, { useState, useCallback, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  Handle,
  Position,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useQueryClient } from '@tanstack/react-query'
import { createWorkflow, updateWorkflow, listWorkflows, listFolders, getPluginTypes, getToolSchema } from '../api'

function TaskNode({ data, selected }) {
  const label = data.label || data.id
  const plugin = data.plugin || ''

  return (
    <div style={{
      padding: '8px 12px',
      background: selected ? '#4a4a8e' : '#333',
      color: 'white',
      borderRadius: '6px',
      textAlign: 'center',
      border: selected ? '2px solid #6a6aae' : '2px solid transparent',
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      whiteSpace: 'nowrap',
      maxWidth: '300px',
    }}>
      <Handle type="target" position={Position.Top} style={{ background: '#4a4a8e', width: 8, height: 8 }} />
      <span style={{ fontWeight: 'bold', fontSize: '0.9rem' }}>{label}</span>
      <span style={{ fontSize: '0.75rem', opacity: 0.7, overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {plugin}
      </span>
      <Handle type="source" position={Position.Bottom} style={{ background: '#4a4a8e', width: 8, height: 8 }} />
    </div>
  )
}

const nodeTypes = { taskNode: TaskNode }

function WorkflowEditorContent({ workflow, onBack }) {
  const queryClient = useQueryClient()
  const reactFlowRef = useRef(null)

  // Build initial nodes from workflow config with auto-layout
  const getInitialNodes = () => {
    if (workflow?.config?.tasks) {
      const tasks = workflow.config.tasks
      const NODE_WIDTH = 180
      const NODE_HEIGHT = 80
      const LEVEL_GAP = 120
      const NODE_GAP = 50

      // Calculate in-degree for each node
      const inDegree = {}
      const dependents = {} // node -> nodes that depend on it

      tasks.forEach(task => {
        inDegree[task.id] = 0
        dependents[task.id] = []
      })

      tasks.forEach(task => {
        (task.depends_on || []).forEach(dep => {
          inDegree[task.id]++
          if (dependents[dep]) {
            dependents[dep].push(task.id)
          }
        })
      })

      // Find root nodes (no dependencies)
      const levels = {} // node -> level index
      const queue = tasks.filter(t => inDegree[t.id] === 0).map(t => t.id)

      // BFS to assign levels
      while (queue.length > 0) {
        const nodeId = queue.shift()
        const task = tasks.find(t => t.id === nodeId)
        const level = Object.values(levels).filter(v => v === levels[nodeId]).length > 0 ? levels[nodeId] : 0

        // Find max level of dependencies
        let maxDepLevel = -1
        ;(task.depends_on || []).forEach(dep => {
          if (levels[dep] !== undefined && levels[dep] > maxDepLevel) {
            maxDepLevel = levels[dep]
          }
        })
        levels[nodeId] = maxDepLevel + 1

        // Add dependents to queue
        ;(dependents[nodeId] || []).forEach(depId => {
          if (!levels[depId]) {
            queue.push(depId)
          }
        })
      }

      // Assign level to nodes without dependencies
      let maxLevel = 0
      tasks.forEach(task => {
        if (levels[task.id] === undefined) {
          // Nodes without explicit dependencies go to level 0 or lower
          levels[task.id] = 0
        }
        maxLevel = Math.max(maxLevel, levels[task.id])
      })

      // Group nodes by level
      const levelGroups = {}
      tasks.forEach(task => {
        const level = levels[task.id] || 0
        if (!levelGroups[level]) levelGroups[level] = []
        levelGroups[level].push(task.id)
      })

      // Assign positions
      return tasks.map((task, index) => {
        const level = levels[task.id] || 0
        const nodesInLevel = levelGroups[level] || []
        const indexInLevel = nodesInLevel.indexOf(task.id)
        const totalWidthInLevel = nodesInLevel.length * NODE_WIDTH + (nodesInLevel.length - 1) * NODE_GAP
        const startX = (800 - totalWidthInLevel) / 2 // Center in 800px canvas

        return {
          id: task.id,
          type: 'taskNode',
          data: {
            label: task.name || task.id,
            plugin: task.plugin || 'command',
            config: task.config || {},
            depends_on: task.depends_on || [],
          },
          position: {
            x: startX + indexInLevel * (NODE_WIDTH + NODE_GAP),
            y: level * LEVEL_GAP,
          },
        }
      })
    }
    return []
  }

  // Build initial edges from workflow config
  const getInitialEdges = () => {
    if (workflow?.config?.tasks) {
      const edges = []
      workflow.config.tasks.forEach((task) => {
        (task.depends_on || []).forEach((dep) => {
          edges.push({
            id: `${dep}-${task.id}`,
            source: dep,
            target: task.id,
            animated: true,
            style: { stroke: '#4a4a8e' },
          })
        })
      })
      return edges
    }
    return []
  }

  const [name, setName] = useState(workflow?.name || '新工作流')
  const [description, setDescription] = useState(workflow?.description || '')
  const [folder, setFolder] = useState(workflow?.folder || '')
  const [newFolderName, setNewFolderName] = useState('')
  const [selectedNode, setSelectedNode] = useState(null)
  const [currentToolSchema, setCurrentToolSchema] = useState(null)
  const [isSaving, setIsSaving] = useState(false)
  const [nodes, setNodes, onNodesChange] = useNodesState(getInitialNodes())
  const [edges, setEdges, onEdgesChange] = useEdgesState(getInitialEdges())
  const [contextMenu, setContextMenu] = useState(null)
  const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 })

  // Get existing folders for dropdown
  const { data: existingFolders = [] } = useQuery({
    queryKey: ['folders'],
    queryFn: listFolders,
    staleTime: Infinity,
  })

  // Get plugin types from API
  const { data: pluginTypesData } = useQuery({
    queryKey: ['pluginTypes'],
    queryFn: getPluginTypes,
    staleTime: Infinity,
  })

  const pluginOptions = pluginTypesData?.task || []

  // Flatten folders for select options
  const flattenFolders = (folders, prefix = '') => {
    const result = []
    for (const f of folders) {
      const path = prefix ? `${prefix}/${f.name}` : f.name
      result.push(path)
      if (f.children) {
        result.push(...flattenFolders(f.children, path))
      }
    }
    return result
  }

  const folderOptions = flattenFolders(existingFolders)

  // Update nodes when workflow changes
  useEffect(() => {
    setNodes(getInitialNodes())
    setEdges(getInitialEdges())
  }, [workflow])

  // Close context menu on Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && contextMenu) {
        setContextMenu(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [contextMenu])

  // Check if adding edge would create a cycle
  // Edge: source -> target means source must run before target
  // A cycle exists if there's already a path from target to source
  const wouldCreateCycle = (edges, source, target) => {
    // Build adjacency list: children[X] = nodes that depend on X (X must run before these)
    const children = {}
    edges.forEach(e => {
      if (!children[e.source]) children[e.source] = []
      children[e.source].push(e.target)
    })

    // Check if there's already a path from target to source
    const visited = new Set()
    const stack = [target]
    while (stack.length > 0) {
      const node = stack.pop()
      if (node === source) return true  // Found path back to source = cycle
      if (visited.has(node)) continue
      visited.add(node)
      const kids = children[node] || []
      stack.push(...kids)
    }
    return false
  }

  const onConnect = useCallback((params) => {
    const { source, target } = params
    if (wouldCreateCycle(edges, source, target)) {
      alert('不能创建循环依赖！')
      return
    }
    setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#4a4a8e' } }, eds))
  }, [edges])

  const onNodeContextMenu = useCallback((event, node) => {
    event.preventDefault()
    setContextMenu({ x: event.clientX, y: event.clientY, type: 'node', node })
  }, [])

  const onEdgeContextMenu = useCallback((event, edge) => {
    event.preventDefault()
    setContextMenu({ x: event.clientX, y: event.clientY, type: 'edge', edge })
  }, [])

  const onPaneContextMenu = useCallback((event) => {
    event.preventDefault()
    const position = reactFlowRef.current?.screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    })
    setContextMenu({ x: event.clientX, y: event.clientY, type: 'pane' })
    setContextMenuPosition(position || { x: event.clientX, y: event.clientY })
  }, [])

  const handleDeleteNode = useCallback((nodeId) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId))
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId))
    setSelectedNode(null)
    setContextMenu(null)
  }, [])

  const handleDeleteEdge = useCallback((edgeId) => {
    setEdges((eds) => eds.filter((e) => e.id !== edgeId))
    setContextMenu(null)
  }, [])

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node)
  }, [])

  const handleAddTask = (plugin, position) => {
    // Generate unique ID
    let id = `task_${Date.now()}`
    while (nodes.some(n => n.id === id)) {
      id = `task_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`
    }

    const newNode = {
      id,
      type: 'taskNode',
      data: {
        label: `新任务`,
        plugin,
        config: {},
        depends_on: [],
      },
      position: position || { x: Math.random() * 300 + 100, y: Math.random() * 200 + 100 },
    }
    setNodes((nds) => [...nds, newNode])
    setContextMenu(null)
    // Fit view after adding node
    setTimeout(() => {
      reactFlowRef.current?.fitView({ padding: 0.2, duration: 300 })
    }, 50)
  }

  // Fit view on initial load
  useEffect(() => {
    setTimeout(() => {
      reactFlowRef.current?.fitView({ padding: 0.2, duration: 300 })
    }, 100)
  }, [])

  const handleUpdateNode = (field, value) => {
    if (!selectedNode) return

    // If plugin changes, fetch tool schema if it's a tool type
    if (field === 'plugin' && value.startsWith('tool:')) {
      const toolName = value.replace('tool:', '')
      getToolSchema(toolName).then(schema => {
        setCurrentToolSchema(schema)
      }).catch(err => {
        console.error('Failed to load tool schema:', err)
        setCurrentToolSchema(null)
      })
    } else if (field === 'plugin' && !value.startsWith('tool:')) {
      setCurrentToolSchema(null)
    }

    setNodes((nds) =>
      nds.map((node) =>
        node.id === selectedNode.id
          ? { ...node, data: { ...node.data, [field]: value } }
          : node
      )
    )
    setSelectedNode((n) => ({ ...n, data: { ...n.data, [field]: value } }))
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      // Validation: check for empty workflow name
      if (!name.trim()) {
        alert('工作流名称不能为空')
        setIsSaving(false)
        return
      }

      // Validation: check for empty task names
      for (const node of nodes) {
        if (!node.data.label.trim()) {
          alert('任务名称不能为空')
          setIsSaving(false)
          return
        }
      }

      // Validation: check for duplicate task IDs
      const taskIds = nodes.map(n => n.id)
      const uniqueIds = new Set(taskIds)
      if (taskIds.length !== uniqueIds.size) {
        alert('任务ID不能重复')
        setIsSaving(false)
        return
      }

      // Validation: check for duplicate task names (display names)
      const taskNames = nodes.map(n => n.data.label.trim())
      const uniqueNames = new Set(taskNames)
      if (taskNames.length !== uniqueNames.size) {
        alert('任务名称不能重复')
        setIsSaving(false)
        return
      }

      // Validation: check for duplicate workflow name
      const existingWorkflows = await listWorkflows()
      const isDuplicate = existingWorkflows.some(w =>
        w.name.trim() === name.trim() && w.id !== workflow?.id
      )
      if (isDuplicate) {
        alert('工作流名称不能重复')
        setIsSaving(false)
        return
      }

      // Validation: check for circular dependency (cycle in DAG)
      const edgesToDepends = {}
      edges.forEach((edge) => {
        if (!edgesToDepends[edge.target]) {
          edgesToDepends[edge.target] = []
        }
        edgesToDepends[edge.target].push(edge.source)
      })

      // DFS to detect cycle starting from each node
      const visited = new Set()
      const recStack = new Set()

      const hasCycle = (nodeId, path = []) => {
        visited.add(nodeId)
        recStack.add(nodeId)
        path.push(nodeId)

        const deps = edgesToDepends[nodeId] || []
        for (const dep of deps) {
          if (!visited.has(dep)) {
            if (hasCycle(dep, [...path])) {
              return true
            }
          } else if (recStack.has(dep)) {
            const cycleStart = path.indexOf(dep)
            const cycleNodes = path.slice(cycleStart).concat(dep)
            alert(`存在循环依赖: ${cycleNodes.join(' -> ')}`)
            return true
          }
        }

        recStack.delete(nodeId)
        return false
      }

      for (const node of nodes) {
        if (!visited.has(node.id)) {
          if (hasCycle(node.id, [])) {
            setIsSaving(false)
            return
          }
        }
      }

      // Build edges into depends_on (already built for cycle detection above)
      const tasks = nodes.map((node) => ({
        id: node.id,
        name: node.data.label,
        plugin: node.data.plugin,
        config: node.data.config || {},
        depends_on: edgesToDepends[node.id] || [],
      }))

      const config = { name, tasks }

      if (workflow?.id) {
        await updateWorkflow(workflow.id, { name, description, folder, config })
      } else {
        await createWorkflow({ name, description, folder, config })
      }

      queryClient.invalidateQueries(['workflows'])
      queryClient.invalidateQueries(['folders'])
      onBack()
    } catch (err) {
      alert('保存失败: ' + err.message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="workflow-editor">
      <div className="editor-toolbar">
        <button className="btn btn-secondary" onClick={onBack}>
          返回
        </button>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="工作流名称"
            style={{ padding: '0.5rem', fontSize: '1rem' }}
          />
          <select
            value={folder}
            onChange={(e) => setFolder(e.target.value)}
            style={{ padding: '0.5rem', fontSize: '1rem', width: '160px' }}
          >
            <option value="">根目录</option>
            {folderOptions.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
            {isSaving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>

      <div className="editor-content">
        <div className="task-palette">
          <h4>任务类型</h4>
          <p style={{ fontSize: '0.8rem', color: '#666', marginBottom: '1rem' }}>
            点击添加任务节点
          </p>
          {pluginOptions.map((opt) => (
            <div
              key={opt.value}
              className="palette-item"
              onClick={() => handleAddTask(opt.value)}
            >
              {opt.label}
            </div>
          ))}
        </div>

        <div className="dag-canvas" style={{ height: '500px' }}>
          <ReactFlow
            ref={reactFlowRef}
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onNodeContextMenu={onNodeContextMenu}
            onEdgeContextMenu={onEdgeContextMenu}
            onPaneContextMenu={onPaneContextMenu}
            nodeTypes={nodeTypes}
            defaultEdgeOptions={{ type: 'default', animated: true, style: { stroke: '#4a4a8e' } }}
            fitView
            onInit={(instance) => {
              reactFlowRef.current = instance
              instance.fitView({ padding: 0.2 })
            }}
          >
            <Controls />
            <MiniMap />
            <Background />
          </ReactFlow>
        </div>

        <div className="task-properties">
          <h4>任务属性 {selectedNode ? `- ${selectedNode.id}` : ''}</h4>
          {selectedNode ? (
            <>
              <div className="form-group">
                <label>任务名称</label>
                <input
                  value={selectedNode.data.label}
                  onChange={(e) => handleUpdateNode('label', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>插件</label>
                <select
                  value={selectedNode.data.plugin}
                  onChange={(e) => handleUpdateNode('plugin', e.target.value)}
                >
                  {pluginOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              {/* Tool parameters form */}
              {currentToolSchema && currentToolSchema.parameters && currentToolSchema.parameters.length > 0 && (
                <div className="form-group">
                  <label>参数配置</label>
                  {currentToolSchema.parameters.map((param) => (
                    <div key={param.name} style={{ marginBottom: '8px' }}>
                      <label style={{ fontSize: '0.85rem', color: '#666' }}>
                        {param.description || param.name}
                        {param.required && <span style={{ color: 'red' }}> *</span>}
                      </label>
                      {param.type === 'bool' ? (
                        <input
                          type="checkbox"
                          checked={selectedNode.data.config?.[param.name] || false}
                          onChange={(e) => {
                            const newConfig = { ...selectedNode.data.config, [param.name]: e.target.checked }
                            handleUpdateNode('config', newConfig)
                          }}
                        />
                      ) : param.type === 'int' ? (
                        <input
                          type="number"
                          value={selectedNode.data.config?.[param.name] ?? param.default ?? ''}
                          onChange={(e) => {
                            const newConfig = { ...selectedNode.data.config, [param.name]: e.target.value }
                            handleUpdateNode('config', newConfig)
                          }}
                          placeholder={param.default?.toString() || ''}
                        />
                      ) : (
                        <input
                          type="text"
                          value={selectedNode.data.config?.[param.name] ?? param.default ?? ''}
                          onChange={(e) => {
                            const newConfig = { ...selectedNode.data.config, [param.name]: e.target.value }
                            handleUpdateNode('config', newConfig)
                          }}
                          placeholder={param.default?.toString() || ''}
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
              <div className="form-group">
                <label>依赖任务</label>
                <div style={{ fontSize: '0.9rem', color: '#666' }}>
                  {(selectedNode.data.depends_on || []).join(', ') || '无'}
                </div>
                <div style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#888' }}>
                  从一个节点拖动到另一个节点来创建依赖
                </div>
              </div>
              <button className="btn btn-danger" onClick={() => handleDeleteNode(selectedNode.id)}>
                删除任务
              </button>
            </>
          ) : (
            <p style={{ color: '#666' }}>点击任务节点查看属性</p>
          )}
        </div>

        {/* Context Menu */}
        {contextMenu && (
          <>
            <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 999 }} onClick={() => setContextMenu(null)} />
            <div style={{
              position: 'fixed',
              top: `${contextMenu.y}px`,
              left: `${contextMenu.x}px`,
              background: 'white',
              borderRadius: '6px',
              boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
              padding: '4px 0',
              minWidth: '120px',
              zIndex: 1000
            }}>
              {contextMenu.type === 'node' && (
                <div style={{ padding: '8px 16px', cursor: 'pointer', fontSize: '13px', color: '#dc3545' }}
                  onClick={() => handleDeleteNode(contextMenu.node.id)}>
                  🗑️ 删除节点
                </div>
              )}
              {contextMenu.type === 'edge' && (
                <div style={{ padding: '8px 16px', cursor: 'pointer', fontSize: '13px', color: '#dc3545' }}
                  onClick={() => handleDeleteEdge(contextMenu.edge.id)}>
                  🗑️ 删除连接
                </div>
              )}
              {contextMenu.type === 'pane' && (
                <div style={{ padding: '8px 16px', cursor: 'pointer', fontSize: '13px' }}
                  onClick={() => handleAddTask('command', contextMenuPosition)}>
                  ➕ 新增节点
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function WorkflowEditor(props) {
  return (
    <ReactFlowProvider>
      <WorkflowEditorContent {...props} />
    </ReactFlowProvider>
  )
}

export default WorkflowEditor
