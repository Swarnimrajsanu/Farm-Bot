import { create } from 'zustand'
import axios from 'axios'

export interface Detection {
  image_url: string
  image_file: string
  disease: string
  confidence: number
  solution: string
  timestamp: string
  is_batch?: boolean
  batch_images?: string[]
  num_photos?: number
}

interface AppState {
  history: Detection[]
  loading: boolean
  error: string | null
  fetchHistory: () => Promise<void>
  isDarkMode: boolean
  toggleDarkMode: () => void
}

export const useStore = create<AppState>((set) => ({
  history: [],
  loading: false,
  error: null,
  fetchHistory: async () => {
    set({ loading: true, error: null })
    try {
      const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/history`)
      set({ history: res.data.predictions, loading: false })
    } catch (err: any) {
      set({ error: err.message, loading: false })
    }
  },
  isDarkMode: false,
  toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
}))
