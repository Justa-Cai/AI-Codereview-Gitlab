<template>
  <div class="dashboard">
    <div class="header">
      <h2>审查日志</h2>
      <div class="header-buttons">
        <button class="chat-button" @click="goToChat">
          <span class="chat-icon">💬</span>
          CHAT
        </button>
        <button class="prompt-button" @click="goToPrompt">
          <span class="prompt-icon">📜</span>
          提示词
        </button>
        <button class="config-button" @click="goToConfig">
          <span class="config-icon">⚙️</span>
          环境配置
        </button>
      </div>
    </div>
    
    <!-- 标签页 -->
    <div class="tabs">
      <button 
        :class="['tab-button', { active: activeTab === 'mr' }]"
        @click="activeTab = 'mr'"
      >
        Merge Request
      </button>
      <button 
        :class="['tab-button', { active: activeTab === 'push' }]"
        @click="activeTab = 'push'"
      >
        Push
      </button>
    </div>

    <!-- 筛选器 -->
    <div class="filters">
      <div class="filter-group">
        <label>开始日期：</label>
        <input type="date" v-model="startDate" />
      </div>
      <div class="filter-group">
        <label>结束日期：</label>
        <input type="date" v-model="endDate" />
      </div>
      <div class="filter-group">
        <label>用户名：</label>
        <select v-model="selectedAuthors" multiple>
          <option v-for="author in uniqueAuthors" :key="author" :value="author">
            {{ author }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>项目名：</label>
        <select v-model="selectedProjects" multiple>
          <option v-for="project in uniqueProjects" :key="project" :value="project">
            {{ project }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>每页显示：</label>
        <select v-model="pageSize">
          <option v-for="size in pageSizeOptions" :key="size" :value="size">
            {{ size }}条
          </option>
        </select>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in filteredData" :key="index">
            <td v-for="column in columns" :key="column.key">
              <template v-if="column.key === 'score'">
                <div class="progress-bar" @click="showDetail(row)">
                  <div 
                    class="progress" 
                    :style="{ width: `${row[column.key]}%` }"
                  >
                    <span class="score-text">{{ row[column.key] }}</span>
                  </div>
                </div>
              </template>
              <template v-else-if="column.key === 'url'">
                <a :href="row[column.key]" target="_blank">查看</a>
              </template>
              <template v-else>
                {{ row[column.key] }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页控件 -->
    <div class="pagination">
      <button 
        :disabled="currentPage === 1"
        @click="changePage(currentPage - 1)"
        class="page-button"
      >
        上一页
      </button>
      <span class="page-info">
        第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
      </span>
      <button 
        :disabled="currentPage === totalPages"
        @click="changePage(currentPage + 1)"
        class="page-button"
      >
        下一页
      </button>
    </div>

    <!-- 统计信息 -->
    <div class="stats">
      <p>总记录数: {{ totalRecords }}</p>
      <p>平均分: {{ averageScore.toFixed(2) }}</p>
    </div>

    <!-- 图表区域 -->
    <div class="charts">
      <div class="chart-container">
        <h3>项目提交次数</h3>
        <canvas ref="projectCountChart"></canvas>
      </div>
      <div class="chart-container">
        <h3>项目平均分数</h3>
        <canvas ref="projectScoreChart"></canvas>
      </div>
      <div class="chart-container">
        <h3>人员提交次数</h3>
        <canvas ref="authorCountChart"></canvas>
      </div>
      <div class="chart-container">
        <h3>人员平均分数</h3>
        <canvas ref="authorScoreChart"></canvas>
      </div>
    </div>

    <!-- 详情模态框 -->
    <DetailModal 
      v-if="showModal"
      :mrData="selectedData"
      @close="closeModal"
    />
  </div>
</template>

<script>
import Chart from 'chart.js/auto'
import DetailModal from './DetailModal.vue'

export default {
  name: 'DashboardComponent',
  components: {
    DetailModal
  },
  data() {
    return {
      activeTab: 'push',
      startDate: this.getDefaultStartDate(),
      endDate: new Date().toISOString().split('T')[0],
      selectedAuthors: [],
      selectedProjects: [],
      data: [],
      uniqueAuthors: [],
      uniqueProjects: [],
      charts: {
        projectCount: null,
        projectScore: null,
        authorCount: null,
        authorScore: null
      },
      showModal: false,
      selectedData: null,
      currentPage: 1,
      pageSize: 10,
      pageSizeOptions: [5, 10, 20, 50, 100, 1000],
      totalCount: 0,
      isLoading: false,
      updateChartsTimeout: null
    }
  },
  computed: {
    columns() {
      return this.activeTab === 'mr' 
        ? [
            { key: 'project_name', label: '项目名' },
            { key: 'author', label: '作者' },
            { key: 'source_branch', label: '源分支' },
            { key: 'target_branch', label: '目标分支' },
            { key: 'updated_at', label: '更新时间' },
            { key: 'commit_messages', label: '提交信息' },
            { key: 'score', label: '分数' },
            { key: 'url', label: '链接' }
          ]
        : [
            { key: 'project_name', label: '项目名' },
            { key: 'author', label: '作者' },
            { key: 'branch', label: '分支' },
            { key: 'updated_at', label: '更新时间' },
            { key: 'commit_messages', label: '提交信息' },
            { key: 'score', label: '分数' }
          ]
    },
    filteredData() {
      return this.data
    },
    totalRecords() {
      return this.totalCount
    },
    averageScore() {
      if (this.filteredData.length === 0) return 0
      return this.filteredData.reduce((sum, row) => sum + row.score, 0) / this.filteredData.length
    },
    totalPages() {
      return Math.ceil(this.totalCount / this.pageSize)
    }
  },
  methods: {
    goToChat() {
      this.$router.push({
        path: '/chat',
        replace: true
      })
    },
    goToConfig() {
      this.$router.push({
        path: '/config',
        replace: true
      })
    },
    goToPrompt() {
      this.$router.push({
        path: '/prompt',
        replace: true
      })
    },
    getDefaultStartDate() {
      const date = new Date()
      date.setDate(date.getDate() - 7)
      return date.toISOString().split('T')[0]
    },
    async fetchData() {
      if (this.isLoading) return;
      
      try {
        this.isLoading = true;
        const endpoint = this.activeTab === 'mr' ? '/api/mr-logs' : '/api/push-logs'
        const params = new URLSearchParams({
          start_date: this.startDate,
          end_date: this.endDate,
          page: this.currentPage,
          page_size: this.pageSize
        })
        
        if (this.selectedAuthors.length > 0) {
          this.selectedAuthors.forEach(author => {
            params.append('authors[]', author)
          })
        }
        
        if (this.selectedProjects.length > 0) {
          this.selectedProjects.forEach(project => {
            params.append('projects[]', project)
          })
        }
        
        const response = await fetch(`${endpoint}?${params.toString()}`)
        if (response.ok) {
          const result = await response.json()
          // 处理时间戳和格式化数据
          this.data = result.data.map(item => ({
            ...item,
            updated_at: new Date(item.updated_at * 1000).toLocaleString(),
            score: parseFloat(item.score) || 0,
            commit_messages: item.commit_messages || '',
            branch: item.branch || item.target_branch || '',
            source_branch: item.source_branch || '',
            target_branch: item.target_branch || '',
            url: item.url || ''
          }))
          this.totalCount = result.total
          this.updateUniqueValues()
          // 使用防抖处理更新图表
          if (this.updateChartsTimeout) {
            clearTimeout(this.updateChartsTimeout)
          }
          this.updateChartsTimeout = setTimeout(() => {
            this.updateCharts()
          }, 300)
        } else {
          console.error('获取数据失败:', await response.text())
        }
      } catch (error) {
        console.error('获取数据失败:', error)
      } finally {
        this.isLoading = false
      }
    },
    updateUniqueValues() {
      this.uniqueAuthors = [...new Set(this.data.map(row => row.author))]
      this.uniqueProjects = [...new Set(this.data.map(row => row.project_name))]
    },
    getLabels(chartKey) {
      switch (chartKey) {
        case 'projectCount':
        case 'projectScore':
          return this.getProjectCounts().labels;
        case 'authorCount':
        case 'authorScore':
          return this.getAuthorCounts().labels;
        default:
          return [];
      }
    },
    getData(chartKey) {
      switch (chartKey) {
        case 'projectCount':
          return this.getProjectCounts().values;
        case 'projectScore':
          return this.getProjectScores().values;
        case 'authorCount':
          return this.getAuthorCounts().values;
        case 'authorScore':
          return this.getAuthorScores().values;
        default:
          return [];
      }
    },
    updateCharts() {
      if (!this.$refs) return;
      
      this.$nextTick(() => {
        const chartTypes = ['projectCount', 'projectScore', 'authorCount', 'authorScore'];
        
        chartTypes.forEach(chartKey => {
          const canvas = this.$refs[`${chartKey}Chart`];
          if (!canvas) {
            console.error(`无法获取 ${chartKey} 的 canvas 元素`);
            return;
          }

          const ctx = canvas.getContext('2d');
          if (!ctx) {
            console.error(`无法获取 ${chartKey} 的 canvas 上下文`);
            return;
          }

          // 如果已存在图表实例，先销毁
          if (this.charts[chartKey]) {
            try {
              this.charts[chartKey].destroy();
            } catch (error) {
              console.error(`销毁 ${chartKey} 图表时出错:`, error);
            }
            this.charts[chartKey] = null;
          }

          try {
            const labels = this.getLabels(chartKey);
            const data = this.getData(chartKey);
            
            this.charts[chartKey] = new Chart(ctx, {
              type: 'bar',
              data: {
                labels: labels,
                datasets: [{
                  label: this.getChartLabel(chartKey),
                  data: data,
                  backgroundColor: this.generateColors(labels.length, chartKey)
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  y: {
                    beginAtZero: true
                  }
                },
                plugins: {
                  legend: {
                    display: false
                  }
                },
                animation: {
                  duration: 300 // 减少动画时间
                }
              }
            });
          } catch (error) {
            console.error(`创建 ${chartKey} 图表时出错:`, error);
          }
        });
      });
    },
    getChartLabel(chartKey) {
      const labels = {
        projectCount: '项目提交次数',
        projectScore: '项目平均分数',
        authorCount: '人员提交次数',
        authorScore: '人员平均分数'
      };
      return labels[chartKey] || chartKey;
    },
    generateColors(count, chartKey) {
      // 为不同类型的图表设置不同的颜色方案
      const colorSchemes = {
        projectCount: [
          '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD',
          '#D4A5A5', '#9B59B6', '#3498DB', '#E67E22', '#2ECC71'
        ],
        projectScore: [
          '#2ECC71', '#E74C3C', '#F1C40F', '#9B59B6', '#3498DB',
          '#1ABC9C', '#E67E22', '#34495E', '#7F8C8D', '#16A085'
        ],
        authorCount: [
          '#3498DB', '#E74C3C', '#2ECC71', '#F1C40F', '#9B59B6',
          '#1ABC9C', '#E67E22', '#34495E', '#7F8C8D', '#16A085'
        ],
        authorScore: [
          '#9B59B6', '#3498DB', '#E74C3C', '#2ECC71', '#F1C40F',
          '#1ABC9C', '#E67E22', '#34495E', '#7F8C8D', '#16A085'
        ]
      }

      // 使用图表键直接获取颜色方案
      const colors = colorSchemes[chartKey] || Array(count).fill().map((_, i) => 
        `hsl(${(i * 360) / count}, 70%, 50%)`
      )

      // 如果数据点数量超过预定义的颜色数量，循环使用颜色
      return Array(count).fill().map((_, i) => colors[i % colors.length])
    },
    getProjectCounts() {
      const counts = {}
      this.data.forEach(row => {
        if (row.project_name) {
          counts[row.project_name] = (counts[row.project_name] || 0) + 1
        }
      })
      return {
        labels: Object.keys(counts),
        values: Object.values(counts)
      }
    },
    getProjectScores() {
      const scores = {}
      const counts = {}
      this.data.forEach(row => {
        if (row.project_name && row.score) {
          scores[row.project_name] = (scores[row.project_name] || 0) + parseFloat(row.score)
          counts[row.project_name] = (counts[row.project_name] || 0) + 1
        }
      })
      return {
        labels: Object.keys(scores),
        values: Object.keys(scores).map(key => scores[key] / counts[key])
      }
    },
    getAuthorCounts() {
      const counts = {}
      this.data.forEach(row => {
        if (row.author) {
          counts[row.author] = (counts[row.author] || 0) + 1
        }
      })
      return {
        labels: Object.keys(counts),
        values: Object.values(counts)
      }
    },
    getAuthorScores() {
      const scores = {}
      const counts = {}
      this.data.forEach(row => {
        if (row.author && row.score) {
          scores[row.author] = (scores[row.author] || 0) + parseFloat(row.score)
          counts[row.author] = (counts[row.author] || 0) + 1
        }
      })
      return {
        labels: Object.keys(scores),
        values: Object.keys(scores).map(key => scores[key] / counts[key])
      }
    },
    showDetail(row) {
      this.selectedData = row
      this.showModal = true
    },
    closeModal() {
      this.showModal = false
      this.selectedData = null
    },
    changePage(page) {
      if (this.isLoading) return;
      this.currentPage = page;
      this.fetchData();
    }
  },
  watch: {
    activeTab() {
      this.currentPage = 1
      this.fetchData()
    },
    startDate() {
      this.currentPage = 1
      this.fetchData()
    },
    endDate() {
      this.currentPage = 1
      this.fetchData()
    },
    selectedAuthors() {
      this.currentPage = 1
      this.fetchData()
    },
    selectedProjects() {
      this.currentPage = 1
      this.fetchData()
    },
    pageSize() {
      this.currentPage = 1
      this.fetchData()
    }
  },
  mounted() {
    this.fetchData();
  },
  beforeUnmount() {
    // 清理所有图表实例
    Object.keys(this.charts).forEach(chartKey => {
      if (this.charts[chartKey]) {
        try {
          this.charts[chartKey].destroy();
        } catch (error) {
          console.error(`销毁 ${chartKey} 图表时出错:`, error);
        }
        this.charts[chartKey] = null;
      }
    });
    
    // 清理防抖定时器
    if (this.updateChartsTimeout) {
      clearTimeout(this.updateChartsTimeout);
    }
  }
}
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.chat-button:hover {
  background-color: #45a049;
}

.chat-icon {
  font-size: 16px;
}

.config-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.config-button:hover {
  background-color: #45a049;
}

.config-icon {
  font-size: 16px;
}

.tabs {
  margin-bottom: 20px;
}

.tab-button {
  padding: 10px 20px;
  margin-right: 10px;
  border: none;
  background: #f0f0f0;
  cursor: pointer;
  border-radius: 4px;
}

.tab-button.active {
  background: #4CAF50;
  color: white;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.filter-group label {
  font-weight: bold;
}

.filter-group input,
.filter-group select {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.table-container {
  overflow-x: auto;
  margin-bottom: 20px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
}

.progress {
  height: 100%;
  background-color: #4CAF50;
  transition: width 0.3s ease;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress:hover {
  background-color: #45a049;
}

.score-text {
  color: white;
  font-size: 12px;
  font-weight: bold;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
}

.stats {
  margin: 20px 0;
  font-weight: bold;
}

.charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.chart-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  height: 300px; /* 固定高度 */
  display: flex;
  flex-direction: column;
}

.chart-container h3 {
  margin: 0 0 15px 0;
  text-align: center;
  font-size: 16px;
}

.chart-container canvas {
  flex: 1;
  width: 100% !important;
  height: 100% !important;
}

.prompt-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.prompt-button:hover {
  background-color: #45a049;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin: 20px 0;
}

.page-button {
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.page-button:hover:not(:disabled) {
  background-color: #45a049;
}

.page-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: #666;
}
</style>