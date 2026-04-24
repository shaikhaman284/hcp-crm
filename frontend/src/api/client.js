import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Network error'
    return Promise.reject(new Error(msg))
  }
)

// Interactions
export const getInteractions = (params) => api.get('/api/interactions', { params })
export const getInteraction = (id) => api.get(`/api/interactions/${id}`)
export const createInteraction = (data) => api.post('/api/interactions', data)
export const updateInteraction = (id, data) => api.put(`/api/interactions/${id}`, data)
export const deleteInteraction = (id) => api.delete(`/api/interactions/${id}`)

// HCPs
export const getHCPs = (search) => api.get('/api/hcps', { params: search ? { search } : {} })

// Agent
export const sendChatMessage = (message, sessionId) =>
  api.post('/api/agent/chat', { message, session_id: sessionId })

export const getChatHistory = (sessionId) =>
  api.get(`/api/agent/history/${sessionId}`)

export const suggestFollowup = (interactionId) =>
  api.post(`/api/agent/suggest-followup/${interactionId}`)
