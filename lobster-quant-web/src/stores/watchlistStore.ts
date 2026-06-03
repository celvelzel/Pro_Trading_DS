import { create } from 'zustand'
import { 
  useWatchlistQuery, 
  useAddWatchlistSymbol, 
  useBulkAddWatchlistSymbols,
  useRemoveWatchlistSymbol, 
  useUpdateWatchlistGroups, 
  useUpdateWatchlistTags, 
  useClearWatchlist 
} from '@/hooks/useWatchlist'

interface WatchlistState {
  symbols: string[]
  selectedSymbols: string[]
  groups: Record<string, string[]>
  tags: Record<string, string[]>
  setSelectedSymbols: (symbols: string[]) => void
}

export const useWatchlistStore = create<WatchlistState>()((set) => ({
  symbols: [],
  selectedSymbols: [],
  groups: {},
  tags: {},
  setSelectedSymbols: (symbols) => set({ selectedSymbols: symbols }),
}))

/**
 * Hook to sync watchlist store with backend API.
 * This hook fetches the watchlist from backend and keeps the store in sync.
 */
export function useSyncWatchlist() {
  const { data, isLoading, error } = useWatchlistQuery()
  const addMutation = useAddWatchlistSymbol()
  const bulkAddMutation = useBulkAddWatchlistSymbols()
  const removeMutation = useRemoveWatchlistSymbol()
  const updateGroupsMutation = useUpdateWatchlistGroups()
  const updateTagsMutation = useUpdateWatchlistTags()
  const clearMutation = useClearWatchlist()

  // Sync store with backend data
  if (data) {
    const store = useWatchlistStore.getState()
    const needsUpdate = 
      JSON.stringify(store.symbols) !== JSON.stringify(data.symbols) ||
      JSON.stringify(store.groups) !== JSON.stringify(data.groups) ||
      JSON.stringify(store.tags) !== JSON.stringify(data.tags)
    
    if (needsUpdate) {
      useWatchlistStore.setState({
        symbols: data.symbols,
        groups: data.groups,
        tags: data.tags,
      })
    }
  }

  return {
    isLoading,
    error,
    symbols: useWatchlistStore.getState().symbols,
    selectedSymbols: useWatchlistStore.getState().selectedSymbols,
    groups: useWatchlistStore.getState().groups,
    tags: useWatchlistStore.getState().tags,
    addSymbol: (symbol: string) => addMutation.mutate(symbol),
    bulkAddSymbols: (symbols: string[], group?: string) => 
      bulkAddMutation.mutate({ symbols, group }),
    removeSymbol: (symbol: string) => removeMutation.mutate(symbol),
    updateGroups: (groups: Record<string, string[]>) => updateGroupsMutation.mutate(groups),
    updateTags: (tags: Record<string, string[]>) => updateTagsMutation.mutate(tags),
    clearWatchlist: () => clearMutation.mutate(),
    toggleSelect: (symbol: string) => {
      const store = useWatchlistStore.getState()
      const newSelected = store.selectedSymbols.includes(symbol)
        ? store.selectedSymbols.filter((s) => s !== symbol)
        : [...store.selectedSymbols, symbol]
      useWatchlistStore.setState({ selectedSymbols: newSelected })
    },
    selectAll: () => {
      const store = useWatchlistStore.getState()
      useWatchlistStore.setState({ selectedSymbols: [...store.symbols] })
    },
    deselectAll: () => {
      useWatchlistStore.setState({ selectedSymbols: [] })
    },
    removeSelected: () => {
      const store = useWatchlistStore.getState()
      store.selectedSymbols.forEach((symbol) => {
        removeMutation.mutate(symbol)
      })
      useWatchlistStore.setState({ selectedSymbols: [] })
    },
    createGroup: (name: string) => {
      const store = useWatchlistStore.getState()
      const newGroups = { ...store.groups, [name]: [] }
      updateGroupsMutation.mutate(newGroups)
    },
    deleteGroup: (name: string) => {
      const store = useWatchlistStore.getState()
      const { [name]: _, ...rest } = store.groups
      updateGroupsMutation.mutate(rest)
    },
    addToGroup: (group: string, symbol: string) => {
      const store = useWatchlistStore.getState()
      const newGroups = {
        ...store.groups,
        [group]: [...(store.groups[group] || []), symbol],
      }
      updateGroupsMutation.mutate(newGroups)
    },
    removeFromGroup: (group: string, symbol: string) => {
      const store = useWatchlistStore.getState()
      const newGroups = {
        ...store.groups,
        [group]: (store.groups[group] || []).filter((s) => s !== symbol),
      }
      updateGroupsMutation.mutate(newGroups)
    },
    addTag: (symbol: string, tag: string) => {
      const store = useWatchlistStore.getState()
      const newTags = {
        ...store.tags,
        [symbol]: [...(store.tags[symbol] || []), tag],
      }
      updateTagsMutation.mutate(newTags)
    },
    removeTag: (symbol: string, tag: string) => {
      const store = useWatchlistStore.getState()
      const newTags = {
        ...store.tags,
        [symbol]: (store.tags[symbol] || []).filter((t) => t !== tag),
      }
      updateTagsMutation.mutate(newTags)
    },
  }
}
