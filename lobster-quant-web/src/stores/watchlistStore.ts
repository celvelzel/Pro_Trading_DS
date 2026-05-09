import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface WatchlistState {
  symbols: string[]
  addSymbol: (symbol: string) => void
  removeSymbol: (symbol: string) => void
  clearWatchlist: () => void
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set) => ({
      symbols: [],
      addSymbol: (symbol) =>
        set((state) => {
          if (state.symbols.includes(symbol)) {
            return state
          }
          return { symbols: [...state.symbols, symbol] }
        }),
      removeSymbol: (symbol) =>
        set((state) => ({
          symbols: state.symbols.filter((s) => s !== symbol),
        })),
      clearWatchlist: () => set({ symbols: [] }),
    }),
    {
      name: 'watchlist-storage',
    }
  )
)
