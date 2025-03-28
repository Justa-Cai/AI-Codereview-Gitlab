<template>
  <div class="config-manager">
    <div class="header">
      <h2>环境变量配置管理</h2>
      <div class="header-buttons">
        <el-button type="primary" @click="handleReload">重新加载配置</el-button>
        <el-button @click="handleBack">返回</el-button>
      </div>
    </div>
    
    <el-card class="box-card">
      <el-table :data="configList" style="width: 100%">
        <el-table-column prop="key" label="配置项" width="180">
          <template #default="{ row }">
            <el-input v-model="row.key" placeholder="请输入配置项"></el-input>
          </template>
        </el-table-column>
        <el-table-column prop="value" label="配置值">
          <template #default="{ row }">
            <el-input v-model="row.value" placeholder="请输入配置值"></el-input>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ $index }">
            <el-button type="danger" size="mini" @click="handleDelete($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="button-container">
        <el-button type="primary" @click="handleAdd">添加配置项</el-button>
        <el-button v-if="deletedItems.length > 0" type="warning" @click="handleUndoDelete">撤销删除</el-button>
        <el-button type="success" @click="handleSave">保存配置</el-button>
      </div>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

export default {
  name: 'ConfigManager',
  data() {
    return {
      configList: [],
      isAuthenticated: false,
      pendingDeletes: [],
      deletedItems: []
    }
  },
  created() {
    this.checkAuth()
  },
  methods: {
    checkAuth() {
      const token = localStorage.getItem('authToken')
      if (!token) {
        this.$emit('login-required')
        return
      }
      this.isAuthenticated = true
      this.fetchConfig()
    },
    async fetchConfig() {
      try {
        const response = await axios.get('/api/config')
        const { config, order } = response.data
        // 按照order数组的顺序创建配置列表
        this.configList = order.map(key => ({
          key: key || '',
          value: config[key] || ''
        }))
      } catch (error) {
        if (error.response && error.response.status === 401) {
          this.$emit('login-required')
        } else {
          ElMessage.error('获取配置失败')
          console.error('获取配置失败:', error)
        }
        this.configList = []
      }
    },
    handleAdd() {
      this.configList.push({
        key: '',
        value: ''
      })
    },
    handleDelete(index) {
      const keyToDelete = this.configList[index].key
      if (!keyToDelete) {
        ElMessage.warning('无法删除空的配置项')
        return
      }
      this.pendingDeletes.push(keyToDelete)
      this.deletedItems.push({
        key: keyToDelete,
        value: this.configList[index].value,
        index: index
      })
      this.configList.splice(index, 1)
    },
    handleUndoDelete() {
      if (this.deletedItems.length === 0) return
      
      const lastDeleted = this.deletedItems.pop()
      this.pendingDeletes = this.pendingDeletes.filter(key => key !== lastDeleted.key)
      
      this.configList.splice(lastDeleted.index, 0, {
        key: lastDeleted.key,
        value: lastDeleted.value
      })
    },
    async handleSave() {
      try {
        for (const key of this.pendingDeletes) {
          try {
            await axios.post('/api/delete-config', { key: key })
          } catch (error) {
            console.error(`Error deleting config item ${key}:`, error)
            if (error.response && error.response.status === 404) {
              ElMessage.error(`配置项 ${key} 不存在`)
            } else {
              ElMessage.error(`删除配置项 ${key} 失败`)
            }
            return
          }
        }
        
        this.pendingDeletes = []
        
        const config = this.configList.reduce((acc, curr) => {
          if (curr.key && curr.value) {
            acc[curr.key] = curr.value
          }
          return acc
        }, {})
        
        console.log('准备保存的配置数据:', config)
        
        const response = await axios.post('/api/save-config', config)
        console.log('保存配置的响应:', response.data)
        
        ElMessage({
          message: '配置保存成功！配置项已更新，请重新加载配置以使更改生效。',
          type: 'success',
          duration: 5000,
          showClose: true
        })
        await this.fetchConfig()
      } catch (error) {
        console.error('保存配置失败，详细错误:', error)
        if (error.response) {
          console.error('错误响应数据:', error.response.data)
        }
        if (error.response && error.response.status === 401) {
          this.$emit('login-required')
        } else {
          ElMessage({
            message: '配置保存失败，请检查网络连接或联系管理员。',
            type: 'error',
            duration: 5000,
            showClose: true
          })
        }
      }
    },
    async handleReload() {
      try {
        await axios.post('/api/reload-config')
        ElMessage.success('配置重新加载成功')
        this.fetchConfig()
      } catch (error) {
        if (error.response && error.response.status === 401) {
          this.$emit('login-required')
        } else {
          ElMessage.error('配置重新加载失败')
          console.error('重新加载配置失败:', error)
        }
      }
    },
    handleBack() {
      router.push('/')
    }
  }
}
</script>

<style scoped>
.config-manager {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.box-card {
  margin-bottom: 20px;
}

:deep(.el-card__body) {
  padding: 20px;
}

:deep(.el-table) {
  margin-bottom: 20px;
}

:deep(.el-table__body-wrapper) {
  overflow-y: auto;
}

.button-container {
  margin-top: 20px;
  text-align: right;
  padding: 10px 0;
}

@media screen and (max-width: 768px) {
  .config-manager {
    padding: 10px;
  }
  
  .header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
  
  .header-buttons {
    width: 100%;
    justify-content: flex-end;
  }
  
  :deep(.el-table) {
    font-size: 14px;
  }
  
  .button-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  
  .button-container .el-button {
    width: 100%;
  }
}
</style> 