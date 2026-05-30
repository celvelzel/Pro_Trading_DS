import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface WatchlistState {
  symbols: string[]
  selectedSymbols: string[]
  groups: Record<string, string[]>
  tags: Record<string, string[]>
  addSymbol: (symbol: string) => void
  removeSymbol: (symbol: string) => void
  clearWatchlist: () => void
  toggleSelect: (symbol: string) => void
  selectAll: () => void
  deselectAll: () => void
  removeSelected: () => void
  createGroup: (name: string) => void
  deleteGroup: (name: string) => void
  addToGroup: (group: string, symbol: string) => void
  removeFromGroup: (group: string, symbol: string) => void
  addTag: (symbol: string, tag: string) => void
  removeTag: (symbol: string, tag: string) => void
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set) => ({
      symbols: [],
      selectedSymbols: [],
      groups: {},
      tags: {},
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
      createGroup: (name) =>
        set((state) => ({
          groups: { ...state.groups, [name]: [] },
        })),
      deleteGroup: (name) =>
        set((state) => {
          const { [name]: _, ...rest } = state.groups
          return { groups: rest }
        }),
      addToGroup: (group, symbol) =>
        set((state) => ({
          groups: {
            ...state.groups,
            [group]: [...(state.groups[group] || []), symbol],
          },
        })),
      removeFromGroup: (group, symbol) =>
        set((state) => ({
          groups: {
            ...state.groups,
            [group]: (state.groups[group] || []).filter((s) => s !== symbol),
          },
        })),
      addTag: (symbol, tag) =>
        set((state) => ({
          tags: {
            ...state.tags,
            [symbol]: [...new Set([...(state.tags[symbol] || []), tag])],
          },
        })),
      removeTag: (symbol, tag) =>
        set((state) => ({
          tags: {
            ...state.tags,
            [symbol]: (state.tags[symbol] || []).filter((t) => t !== tag),
          },
        })),
    }),
    {
      name: 'watchlist-storage',
    }
  )
)
