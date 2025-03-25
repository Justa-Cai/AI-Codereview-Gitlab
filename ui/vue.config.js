const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  outputDir: 'dist',
  publicPath: '/',
  lintOnSave: false,
  devServer: {
    proxy: {
      '/api': {
        target: process.env.VITE_APP_API_URL || 'http://localhost:5001',
        changeOrigin: true,
        pathRewrite: {
          '^/api': '/api'
        }
      },
      '/login': {
        target: process.env.VITE_APP_API_URL || 'http://localhost:5001',
        changeOrigin: true
      },
      '/logout': {
        target: process.env.VITE_APP_API_URL || 'http://localhost:5001',
        changeOrigin: true
      },
      '/static': {
        target: process.env.VITE_APP_API_URL || 'http://localhost:5001',
        changeOrigin: true,
        pathRewrite: {
          '^/static': '/static'
        }
      },
      '/js': {
        target: process.env.VITE_APP_API_URL || 'http://localhost:5001',
        changeOrigin: true,
        pathRewrite: {
          '^/js': '/js'
        }
      },
      '/css': {
        target: process.env.VITE_APP_API_URL || 'http://localhost:5001',
        changeOrigin: true,
        pathRewrite: {
          '^/css': '/css'
        }
      }
    }
  }
}) 