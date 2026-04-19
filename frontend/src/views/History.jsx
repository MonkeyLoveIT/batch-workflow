import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { listExecutions, getStats } from '../api'
import ReactECharts from 'echarts-for-react'

function History() {
  const { data: executions = [], isLoading } = useQuery({
    queryKey: ['executions'],
    queryFn: () => listExecutions(),
  })

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
  })

  const chartOption = {
    title: { text: '近7天执行趋势' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['成功', '失败'] },
    xAxis: {
      type: 'category',
      data: stats?.daily_stats ? Object.keys(stats.daily_stats) : [],
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '成功',
        type: 'bar',
        data: stats?.daily_stats
          ? Object.values(stats.daily_stats).map((d) => d.success)
          : [],
        itemStyle: { color: '#28a745' },
      },
      {
        name: '失败',
        type: 'bar',
        data: stats?.daily_stats
          ? Object.values(stats.daily_stats).map((d) => d.failed)
          : [],
        itemStyle: { color: '#dc3545' },
      },
    ],
  }

  if (isLoading) return <div>加载中...</div>

  return (
    <div className="history">
      <div className="history-header">
        <h2>执行历史</h2>
      </div>

      <div className="stats-cards">
        <div className="stat-card">
          <div className="value">{stats?.total || 0}</div>
          <div className="label">总执行次数</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{ color: '#28a745' }}>{stats?.success || 0}</div>
          <div className="label">成功</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{ color: '#dc3545' }}>{stats?.failed || 0}</div>
          <div className="label">失败</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{ color: '#007bff' }}>{stats?.success_rate || 0}%</div>
          <div className="label">成功率</div>
        </div>
      </div>

      <div style={{ background: 'white', padding: '1rem', marginBottom: '2rem', borderRadius: '8px' }}>
        <ReactECharts option={chartOption} style={{ height: '300px' }} />
      </div>

      <div className="history-table">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>工作流</th>
              <th>状态</th>
              <th>开始时间</th>
              <th>耗时</th>
            </tr>
          </thead>
          <tbody>
            {executions.map((exec) => (
              <tr key={exec.id}>
                <td>{exec.id}</td>
                <td>{exec.workflow_name}</td>
                <td>
                  <span className={`status-badge status-${exec.status}`}>
                    {exec.status === 'success' ? '成功' : exec.status === 'failed' ? '失败' : '运行中'}
                  </span>
                </td>
                <td>{new Date(exec.started_at).toLocaleString()}</td>
                <td>{exec.duration ? `${exec.duration}秒` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default History
