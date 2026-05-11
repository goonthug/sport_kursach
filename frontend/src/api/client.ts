import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // JWT в httpOnly cookie — не трогаем localStorage
  headers: { 'Content-Type': 'application/json' },
})

export default api
