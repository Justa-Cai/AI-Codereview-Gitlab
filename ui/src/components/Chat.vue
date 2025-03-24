<template>
  <div class="chat-container">
    <div class="header">
      <h2>AI 助手</h2>
      <div class="header-buttons">
        <button class="context-button" @click="toggleContext" :class="{ 'active': useContext }">
          <span class="context-icon">💬</span>
          {{ useContext ? '启用上下文' : '禁用上下文' }}
        </button>
        <button class="config-button" @click="showPromptConfig = true">
          <span class="config-icon">⚙️</span>
          提示词配置
        </button>
        <button class="back-button" @click="goBack">
          <span class="back-icon">←</span>
          返回
        </button>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-for="(message, index) in messages" :key="index" 
           :class="['message', message.role === 'user' ? 'user-message' : 'assistant-message']">
        <div class="message-content">
          <div v-if="message.role === 'assistant'" class="avatar">🤖</div>
          <div v-else class="avatar">👤</div>
          <div class="text" v-html="renderMarkdown(message.content)"></div>
          <div v-if="message.role === 'assistant'" class="message-actions">
            <el-dropdown trigger="click" @command="handleCommand($event, message)">
              <span class="el-dropdown-link">
                <span class="dots">...</span>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy-markdown">复制 Markdown</el-dropdown-item>
                  <el-dropdown-item command="copy-rendered">复制渲染内容</el-dropdown-item>
                  <el-dropdown-item command="download">下载原文</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>

    <div class="input-container">
      <textarea 
        v-model="userInput" 
        @keydown.enter.prevent="sendMessage"
        placeholder="输入您的问题..."
        :disabled="isLoading"
      ></textarea>
      <button 
        @click="sendMessage" 
        :disabled="isLoading || !userInput.trim()"
        class="send-button"
      >
        {{ isLoading ? '发送中...' : '发送' }}
      </button>
    </div>

    <!-- 提示词配置对话框 -->
    <el-dialog
      v-model="showPromptConfig"
      title="提示词配置"
      width="50%"
    >
      <el-form :model="promptConfig" label-width="120px">
        <el-form-item label="System Message">
          <el-input
            type="textarea"
            v-model="promptConfig.system_message"
            :rows="4"
            placeholder="输入系统提示词，用于设定AI助手的角色和行为"
          />
        </el-form-item>
        <el-form-item label="User Message">
          <el-input
            type="textarea"
            v-model="promptConfig.user_message"
            :rows="4"
            placeholder="输入用户提示词模板，使用 {message} 作为用户输入的占位符"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showPromptConfig = false">取消</el-button>
          <el-button type="primary" @click="savePromptConfig">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置marked选项
marked.setOptions({
  breaks: true,           // 启用换行支持
  gfm: true,             // 启用GitHub风格的markdown
  headerIds: false,       // 禁用标题ID
  mangle: false,         // 禁用标题ID转义
  sanitize: false,       // 允许HTML标签
  smartLists: true,      // 使用更智能的列表行为
  langPrefix: 'language-',// 设置代码块的语言前缀
  pedantic: false,       // 尽可能地兼容 markdown.pl
  smartypants: false,    // 使用更智能的标点符号
})

export default {
  name: 'ChatComponent',
  data() {
    return {
      messages: [],
      userInput: '',
      isLoading: false,
      showPromptConfig: false,
      useContext: false,
      promptConfig: {
        system_message: '',
        user_message: ''
      }
    }
  },
  methods: {
    goBack() {
      this.$router.push({
        path: '/',
        replace: true
      })
    },
    async sendMessage() {
      if (this.isLoading || !this.userInput.trim()) return

      const userMessage = this.userInput.trim()
      
      if (!this.useContext) {
        this.messages = []
      }
      
      this.messages.push({
        role: 'user',
        content: userMessage
      })
      this.userInput = ''
      this.isLoading = true

      try {
        // 构建历史消息
        const historyMessages = this.useContext ? 
          this.messages.slice(0, -1).map(msg => ({
            role: msg.role,
            content: msg.content
          })) : []

        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: userMessage,
            system_message: this.promptConfig.system_message,
            user_message: this.promptConfig.user_message,
            use_context: this.useContext,
            history_messages: historyMessages
          })
        })

        if (!response.ok) {
          throw new Error('Network response was not ok')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let assistantMessage = ''

        this.messages.push({
          role: 'assistant',
          content: ''
        })

        let done = false
        while (!done) {
          const { done: isDone, value } = await reader.read()
          done = isDone

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.content) {
                  assistantMessage += data.content
                  this.messages[this.messages.length - 1].content = assistantMessage
                  this.$nextTick(() => {
                    this.scrollToBottom()
                  })
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e)
              }
            }
          }
        }
      } catch (error) {
        console.error('Error:', error)
        this.messages.push({
          role: 'assistant',
          content: '抱歉，发生了一些错误，请稍后重试。'
        })
      } finally {
        this.isLoading = false
        this.saveChatHistory()
      }
    },
    scrollToBottom() {
      const container = this.$refs.messagesContainer
      container.scrollTop = container.scrollHeight
    },
    savePromptConfig() {
      localStorage.setItem('chat_prompt_config', JSON.stringify(this.promptConfig))
      this.showPromptConfig = false
      ElMessage.success('提示词配置已保存')
    },
    toggleContext() {
      this.useContext = !this.useContext
      if (!this.useContext) {
        this.messages = []
        localStorage.removeItem('chat_history')
      }
    },
    saveChatHistory() {
      localStorage.setItem('chat_history', JSON.stringify(this.messages))
    },
    renderMarkdown(content) {
      try {
        if (!content) return ''
        
        // 如果内容已经是markdown代码块，去掉外层的```markdown标记
        let processedContent = content
        if (content.startsWith('```markdown\n') && content.endsWith('```')) {
          processedContent = content.slice(11, -3)
        }
        
        // 预处理内容
        processedContent = processedContent
          // 确保代码块前后有空行，但不处理已经有空行的情况
          .replace(/([^\n])(```[^\n]*\n)/g, '$1\n$2')
          .replace(/(\n```[^\n]*)\n?([^\n])/g, '$1\n\n$2')
          // 确保标题前后有空行，但不处理已经有空行的情况
          .replace(/([^\n])(#{1,6}\s[^\n]*)/g, '$1\n\n$2')
          .replace(/(#{1,6}\s[^\n]*\n)([^\n])/g, '$1\n$2')
          // 确保列表项前有空行，但不处理已经有空行的情况
          .replace(/([^\n])(\n[*-]\s)/g, '$1\n$2')
        
        // 使用marked渲染markdown
        const rendered = marked(processedContent)
        
        // 记录渲染结果用于调试
        console.log('Original content:', content)
        console.log('Processed content:', processedContent)
        console.log('Rendered content:', rendered)
        
        return rendered
      } catch (e) {
        console.error('Markdown rendering error:', e)
        return content || ''
      }
    },
    handleCommand(command, message) {
      switch (command) {
        case 'copy-markdown':
          navigator.clipboard.writeText(message.content)
          ElMessage.success('已复制 Markdown 内容')
          break
        case 'copy-rendered':
          const renderedContent = this.renderMarkdown(message.content)
          navigator.clipboard.writeText(renderedContent)
          ElMessage.success('已复制渲染内容')
          break
        case 'download':
          const blob = new Blob([message.content], { type: 'text/markdown' })
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `message-${new Date().toISOString()}.md`
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
          ElMessage.success('已下载原文')
          break
      }
    }
  },
  mounted() {
    this.scrollToBottom()
    const savedConfig = localStorage.getItem('chat_prompt_config')
    if (savedConfig) {
      this.promptConfig = JSON.parse(savedConfig)
    }
    const savedHistory = localStorage.getItem('chat_history')
    if (savedHistory) {
      this.messages = JSON.parse(savedHistory)
    }
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px;
  background-color: #f5f5f5;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.context-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.context-button:hover {
  background-color: #1976D2;
}

.context-button.active {
  background-color: #1565C0;
}

.context-icon {
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

.back-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #666;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.back-button:hover {
  background-color: #555;
}

.back-icon {
  font-size: 16px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: white;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.message {
  margin-bottom: 20px;
}

.message-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 80%;
  position: relative;
}

.user-message .message-content {
  margin-left: auto;
  flex-direction: row-reverse;
}

.assistant-message .message-content {
  padding-bottom: 0;
}

.avatar {
  font-size: 24px;
  min-width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f0f0;
  border-radius: 50%;
}

.text {
  padding: 12px 16px;
  border-radius: 12px;
  background-color: #f0f0f0;
  word-wrap: break-word;
  line-height: 1.5;
  position: relative;
  display: inline-flex;
  align-items: flex-start;
}

.text :deep(p) {
  margin: 8px 0;
  white-space: pre-wrap;
}

.text :deep(h1),
.text :deep(h2),
.text :deep(h3),
.text :deep(h4),
.text :deep(h5),
.text :deep(h6) {
  margin: 16px 0 8px;
  font-weight: 600;
  line-height: 1.25;
}

.text :deep(pre) {
  background-color: #282c34;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 16px 0;
  position: relative;
}

.text :deep(pre code) {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #abb2bf;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  display: block;
  white-space: pre;
  tab-size: 2;
}

.text :deep(code) {
  background-color: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  font-size: 0.9em;
  color: inherit;
}

.text :deep(ul),
.text :deep(ol) {
  margin: 16px 0;
  padding-left: 2em;
}

.text :deep(li) {
  margin: 8px 0;
  line-height: 1.6;
}

.text :deep(blockquote) {
  margin: 16px 0;
  padding: 0 16px;
  color: #666;
  border-left: 4px solid #ddd;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 0 4px 4px 0;
}

.text :deep(blockquote p) {
  margin: 8px 0;
}

.text :deep(hr) {
  margin: 24px 0;
  border: none;
  border-top: 1px solid #ddd;
}

.user-message .text {
  background-color: #4CAF50;
  color: white;
}

.user-message .text :deep(pre) {
  background-color: rgba(0, 0, 0, 0.3);
}

.user-message .text :deep(pre code) {
  color: rgba(255, 255, 255, 0.9);
}

.user-message .text :deep(code) {
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
}

.user-message .text :deep(blockquote) {
  border-left-color: rgba(255, 255, 255, 0.5);
  color: rgba(255, 255, 255, 0.9);
}

.input-container {
  display: flex;
  gap: 12px;
  padding: 20px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: none;
  height: 60px;
  font-family: inherit;
}

.send-button {
  padding: 0 24px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.send-button:hover:not(:disabled) {
  background-color: #45a049;
}

.send-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.message-actions {
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
  align-self: flex-end;
}

.user-message .message-actions {
  display: none;
}

.dots {
  cursor: pointer;
  font-size: 16px;
  color: #666;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.3s;
  opacity: 0.7;
  line-height: 1;
}

.dots:hover {
  opacity: 1;
  background-color: rgba(0, 0, 0, 0.05);
}

.el-dropdown-link {
  cursor: pointer;
  color: #409EFF;
}

:deep(.el-dropdown-menu__item) {
  padding: 8px 16px;
  font-size: 14px;
}

:deep(.el-dropdown-menu__item:hover) {
  background-color: #f5f7fa;
}
</style>