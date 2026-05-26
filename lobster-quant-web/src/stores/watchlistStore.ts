import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface WatchlistState {
  symbols: string[]
  selectedSymbols: string[]
  addSymbol: (symbol: string) => void
  removeSymbol: (symbol: string) => void
  clearWatchlist: () => void
  toggleSelect: (symbol: string) => void
  selectAll: () => void
  deselectAll: () => void
  removeSelected: () => void
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set) => ({
      symbols: [],
      selectedSymbols: [],
      addSymbol: (symbol) =>
        set((state) => {
          const upperSymbol = symbol.toUpperCase()
          if (state.symbols.includes(upperSymbol)) {
            return state
          }
          return { symbols: [...state.symbols, upperSymbol] }
        }),
      removeSymbol: (symbol) =>
        set((state) => ({
          symbols: state.symbols.filter((s) => s !== symbol),
          selectedSymbols: state.selectedSymbols.filter((s) => s !== symbol),
        })),
      clearWatchlist: () => set({ symbols: [], selectedSymbols: [] }),
      toggleSelect: (symbol) =>
        set((state) => {
          if (state.selectedSymbols.includes(symbol)) {
            return {
              selectedSymbols: state.selectedSymbols.filter((s) => s !== symbol),
            }
          }
          return {
            selectedSymbols: [...state.selectedSymbols, symbol],
          }
        }),
      selectAll: () =>
        set((state) => ({
          selectedSymbols: [...state.symbols],
        })),
      deselectAll: () => set({ selectedSymbols: [] }),
      removeSelected: () =>
        set((state) => ({
          symbols: state.symbols.filter((s) => !state.selectedSymbols.includes(s)),
          selectedSymbols: [],
        })),
    }),
    {
      name: 'watchlist-storage',
    }
  )
)
