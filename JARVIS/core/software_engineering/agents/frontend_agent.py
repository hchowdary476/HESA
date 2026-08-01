"""
JARVIS Frontend Agent — SE Layer.

Generates responsive, modern frontend code based on ArchitectureSpec:
  - React + Vite + Tailwind CSS applications
  - Next.js TypeScript applications
  - Vanilla HTML/CSS/JavaScript

All generated files are written to workspace/{project}/frontend/
"""

from __future__ import annotations

import os
from typing import Any

from JARVIS.core.system.utils.jarvis_logging import get_logger
from JARVIS.core.software_engineering.agents.architect_agent import ArchitectureSpec

logger = get_logger("frontend_agent")


class FrontendAgent:
    """Generates frontend source code from an ArchitectureSpec."""

    def generate(self, spec: ArchitectureSpec) -> dict[str, Any]:
        if not spec.frontend_stack:
            return {"success": True, "files": [], "message": "No frontend stack required."}

        logger.info("FrontendAgent generating %s frontend for %s", spec.frontend_stack, spec.project_name)
        frontend_dir = os.path.join(spec.workspace_path, "frontend")
        files_written: list[str] = []
        stack = spec.frontend_stack.lower()

        if "react" in stack:
            files_written += self._generate_react(spec, frontend_dir)
        elif "next" in stack:
            files_written += self._generate_nextjs(spec, frontend_dir)
        else:
            files_written += self._generate_vanilla(spec, frontend_dir)

        return {
            "success": True,
            "files": files_written,
            "frontend_stack": spec.frontend_stack,
            "message": f"Generated {len(files_written)} frontend files using {spec.frontend_stack}.",
        }

    # ── React + Vite + Tailwind ───────────────────────────────────────────────

    def _generate_react(self, spec: ArchitectureSpec, out_dir: str) -> list[str]:
        written: list[str] = []
        src = os.path.join(out_dir, "src")
        has_auth = "auth" in spec.features
        title = spec.project_name.replace("_", " ").title()

        written.append(self._write(out_dir, "package.json", self._react_package_json(spec)))
        written.append(self._write(out_dir, "index.html", self._react_index_html(title)))
        written.append(self._write(out_dir, "vite.config.js", self._vite_config()))
        written.append(self._write(out_dir, "tailwind.config.js", self._tailwind_config()))
        written.append(self._write(out_dir, ".env.example", "VITE_API_URL=http://localhost:8000"))

        written.append(self._write(src, "main.jsx", self._react_main()))
        written.append(self._write(src, "App.jsx", self._react_app(has_auth)))
        written.append(self._write(os.path.join(src, "styles"), "index.css", self._tailwind_css()))
        written.append(self._write(os.path.join(src, "services"), "api.js", self._react_api_service(spec)))
        written.append(self._write(os.path.join(src, "components"), "Navbar.jsx", self._react_navbar(title)))
        written.append(self._write(os.path.join(src, "components"), "ItemCard.jsx", self._react_item_card()))
        written.append(self._write(os.path.join(src, "components"), "ItemForm.jsx", self._react_item_form()))
        written.append(self._write(os.path.join(src, "pages"), "HomePage.jsx", self._react_home_page(title)))
        written.append(self._write(os.path.join(src, "pages"), "ItemsPage.jsx", self._react_items_page()))
        if has_auth:
            written.append(self._write(os.path.join(src, "pages"), "LoginPage.jsx", self._react_login_page()))
        written.append(self._write(out_dir, "README.md", self._frontend_readme(spec)))
        return written

    def _react_package_json(self, spec: ArchitectureSpec) -> str:
        return f'''{{"name": "{spec.project_name}-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "vite": "^5.0.0"
  }}
}}
'''

    def _react_index_html(self, title: str) -> str:
        return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="{title} — Built with JARVIS SE Platform" />
    <title>{title}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
'''

    def _vite_config(self) -> str:
        return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true }
    }
  }
})
'''

    def _tailwind_config(self) -> str:
        return '''/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: { 50: '#eff6ff', 500: '#3b82f6', 700: '#1d4ed8', 900: '#1e3a8a' }
      }
    }
  },
  plugins: []
}
'''

    def _tailwind_css(self) -> str:
        return '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body { @apply bg-gray-50 text-gray-900 font-sans; }
}

@layer components {
  .btn-primary { @apply bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200; }
  .btn-danger  { @apply bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200; }
  .card { @apply bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200; }
  .input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500; }
}
'''

    def _react_main(self) -> str:
        return '''import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
'''

    def _react_app(self, has_auth: bool) -> str:
        login_route = "      <Route path=\"/login\" element={<LoginPage />} />" if has_auth else ""
        login_import = "import LoginPage from './pages/LoginPage'" if has_auth else ""
        return f'''import {{ Routes, Route }} from 'react-router-dom'
import Navbar from './components/Navbar'
import HomePage from './pages/HomePage'
import ItemsPage from './pages/ItemsPage'
{login_import}

export default function App() {{
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={{<HomePage />}} />
          <Route path="/items" element={{<ItemsPage />}} />
{login_route}
        </Routes>
      </main>
    </div>
  )
}}
'''

    def _react_api_service(self, spec: ArchitectureSpec) -> str:
        return '''import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000,
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const itemsApi = {
  getAll: (skip = 0, limit = 100) => api.get(`/api/items?skip=${skip}&limit=${limit}`),
  getById: id => api.get(`/api/items/${id}`),
  create: data => api.post('/api/items', data),
  update: (id, data) => api.put(`/api/items/${id}`, data),
  delete: id => api.delete(`/api/items/${id}`),
}

export const authApi = {
  login: (username, password) => api.post('/api/auth/login', new URLSearchParams({ username, password })),
  register: data => api.post('/api/auth/register', data),
  me: () => api.get('/api/auth/me'),
}

export default api
'''

    def _react_navbar(self, title: str) -> str:
        return f'''import {{ Link }} from 'react-router-dom'

export default function Navbar() {{
  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold text-blue-600">{title}</Link>
        <div className="flex gap-4">
          <Link to="/" className="text-gray-600 hover:text-blue-600 transition-colors">Home</Link>
          <Link to="/items" className="text-gray-600 hover:text-blue-600 transition-colors">Items</Link>
          <Link to="/login" className="btn-primary text-sm">Login</Link>
        </div>
      </div>
    </nav>
  )
}}
'''

    def _react_item_card(self) -> str:
        return '''export default function ItemCard({ item, onToggle, onDelete }) {
  return (
    <div className={`card group ${item.is_completed ? 'opacity-60' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className={`font-semibold text-lg ${item.is_completed ? 'line-through text-gray-400' : 'text-gray-900'}`}>
            {item.title}
          </h3>
          {item.description && (
            <p className="text-gray-500 text-sm mt-1">{item.description}</p>
          )}
          <p className="text-xs text-gray-400 mt-2">
            Created: {new Date(item.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={() => onToggle(item)} className="text-blue-500 hover:text-blue-700 text-sm font-medium">
            {item.is_completed ? 'Undo' : 'Complete'}
          </button>
          <button onClick={() => onDelete(item.id)} className="text-red-500 hover:text-red-700 text-sm font-medium">
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
'''

    def _react_item_form(self) -> str:
        return '''import { useState } from 'react'

export default function ItemForm({ onSubmit }) {
  const [form, setForm] = useState({ title: '', description: '' })

  const handleSubmit = e => {
    e.preventDefault()
    if (!form.title.trim()) return
    onSubmit(form)
    setForm({ title: '', description: '' })
  }

  return (
    <form onSubmit={handleSubmit} className="card mb-6">
      <h2 className="text-lg font-semibold mb-4">Add New Item</h2>
      <div className="space-y-3">
        <input
          className="input" placeholder="Item title *" required
          value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
        />
        <textarea
          className="input resize-none" rows={2} placeholder="Description (optional)"
          value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
        />
        <button type="submit" className="btn-primary w-full">Add Item</button>
      </div>
    </form>
  )
}
'''

    def _react_home_page(self, title: str) -> str:
        return f'''import {{ Link }} from 'react-router-dom'

export default function HomePage() {{
  return (
    <div className="max-w-2xl mx-auto text-center py-16">
      <h1 className="text-5xl font-bold text-gray-900 mb-4">{title}</h1>
      <p className="text-xl text-gray-500 mb-8">
        A production-ready application built autonomously by JARVIS SE Platform
      </p>
      <div className="flex gap-4 justify-center">
        <Link to="/items" className="btn-primary text-lg px-8 py-3">Get Started</Link>
        <a href="/api/docs" target="_blank" className="border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium py-3 px-8 rounded-lg transition-colors">
          API Docs
        </a>
      </div>
      <div className="mt-16 grid grid-cols-3 gap-6">
        {{"features": ["Fast & Scalable", "Secure by Default", "Fully Documented"]}}.features.map(f => (
          <div key={{f}} className="card text-left">
            <div className="w-10 h-10 bg-blue-100 rounded-lg mb-3 flex items-center justify-center">
              <span className="text-blue-600 font-bold">✓</span>
            </div>
            <h3 className="font-semibold">{{f}}</h3>
          </div>
        ))}}
      </div>
    </div>
  )
}}
'''

    def _react_items_page(self) -> str:
        return '''import { useState, useEffect } from 'react'
import { itemsApi } from '../services/api'
import ItemCard from '../components/ItemCard'
import ItemForm from '../components/ItemForm'

export default function ItemsPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchItems()
  }, [])

  const fetchItems = async () => {
    try {
      setLoading(true)
      const { data } = await itemsApi.getAll()
      setItems(data)
    } catch (err) {
      setError('Failed to load items. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (formData) => {
    try {
      const { data } = await itemsApi.create(formData)
      setItems(prev => [data, ...prev])
    } catch (err) {
      setError('Failed to create item.')
    }
  }

  const handleToggle = async (item) => {
    try {
      const { data } = await itemsApi.update(item.id, { is_completed: !item.is_completed })
      setItems(prev => prev.map(i => i.id === item.id ? data : i))
    } catch (err) {
      setError('Failed to update item.')
    }
  }

  const handleDelete = async (id) => {
    try {
      await itemsApi.delete(id)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch (err) {
      setError('Failed to delete item.')
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Items</h1>
      <ItemForm onSubmit={handleCreate} />
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">{error}</div>
      )}
      {loading ? (
        <div className="text-center text-gray-400 py-16">Loading items...</div>
      ) : items.length === 0 ? (
        <div className="text-center text-gray-400 py-16">No items yet. Create your first one!</div>
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <ItemCard key={item.id} item={item} onToggle={handleToggle} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  )
}
'''

    def _react_login_page(self) -> str:
        return '''import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../services/api'

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { data } = await authApi.login(form.username, form.password)
      localStorage.setItem('access_token', data.access_token)
      navigate('/items')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto mt-20">
      <div className="card">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Sign In</h1>
        {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input className="input" placeholder="Username" required
            value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
          <input className="input" type="password" placeholder="Password" required
            value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
'''

    # ── Next.js ───────────────────────────────────────────────────────────────

    def _generate_nextjs(self, spec: ArchitectureSpec, out_dir: str) -> list[str]:
        written: list[str] = []
        title = spec.project_name.replace("_", " ").title()
        written.append(self._write(out_dir, "package.json", f'''{{"name": "{spec.project_name}",
  "version": "0.1.0",
  "scripts": {{"dev": "next dev", "build": "next build", "start": "next start"}},
  "dependencies": {{"next": "14.0.0", "react": "^18", "react-dom": "^18", "axios": "^1.6.0"}},
  "devDependencies": {{"typescript": "^5", "@types/react": "^18", "tailwindcss": "^3.4.0"}}
}}
'''))
        written.append(self._write(os.path.join(out_dir, "app"), "page.tsx", f'''export default function Home() {{
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <h1 className="text-5xl font-bold text-gray-900">{title}</h1>
      <p className="text-gray-500 mt-4">Built with JARVIS SE Platform using Next.js</p>
    </main>
  )
}}
'''))
        return written

    # ── Vanilla ───────────────────────────────────────────────────────────────

    def _generate_vanilla(self, spec: ArchitectureSpec, out_dir: str) -> list[str]:
        written: list[str] = []
        title = spec.project_name.replace("_", " ").title()
        written.append(self._write(out_dir, "index.html", f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <link rel="stylesheet" href="styles.css"/>
</head>
<body>
  <nav><a href="#" class="logo">{title}</a></nav>
  <main><h1>Welcome to {title}</h1></main>
  <script src="app.js"></script>
</body>
</html>
'''))
        written.append(self._write(out_dir, "styles.css", '''* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; background: #f9fafb; color: #111827; }
nav { background: white; padding: 1rem 2rem; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; }
.logo { font-size: 1.25rem; font-weight: 700; color: #2563eb; text-decoration: none; }
main { max-width: 800px; margin: 4rem auto; padding: 0 1rem; }
h1 { font-size: 2.5rem; color: #111827; }
'''))
        written.append(self._write(out_dir, "app.js", f'''// {title} — Generated by JARVIS SE Platform
const API_URL = 'http://localhost:8000';

async function fetchItems() {{
  const res = await fetch(`${{API_URL}}/api/items`);
  return res.json();
}}
'''))
        return written

    def _frontend_readme(self, spec: ArchitectureSpec) -> str:
        return f"""# {spec.project_name.replace("_", " ").title()} — Frontend

**Stack:** {spec.frontend_stack} | **API:** http://localhost:8000

## Quick Start

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173

## Generated by JARVIS Autonomous SE Platform
"""

    def _write(self, directory: str, filename: str, content: str) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            return path
        except Exception as e:
            logger.error("FrontendAgent write error for %s: %s", path, e)
            return path
