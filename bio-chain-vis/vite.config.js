import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'dynamic-data-manifest',
      configureServer(server) {
        server.middlewares.use('/api/data-list', (req, res, next) => {
          try {
            const dataDir = path.resolve(__dirname, 'public/data');
            if (!fs.existsSync(dataDir)) {
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify([]));
              return;
            }
            const files = fs.readdirSync(dataDir).filter(file => file.endsWith('.json'));
            const fileList = files.map(file => ({
              name: file,
              label: file
            }));
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify(fileList));
          } catch (e) {
            console.error('Error reading data directory:', e);
            next(e);
          }
        });
      }
    }
  ],
  server: {
    // 自定义端口: 通过 VITE_PORT 环境变量设置，默认 3000
    port: parseInt(process.env.VITE_PORT) || 3000,
    // 允许局域网访问
    host: true,
    // 允许访问上级目录（用于加载output目录的JSON文件）
    fs: {
      allow: ['..'],
    },
  },
  resolve: {
    alias: {
      // 配置别名，支持从外部 output 目录加载数据
      '@data': path.resolve(__dirname, '../output'),
      '@': path.resolve(__dirname, './src'),
    }
  },
  // 配置静态资源目录
  publicDir: 'public',
})
