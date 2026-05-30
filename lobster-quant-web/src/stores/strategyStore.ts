import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Types
export interface StrategyParams {
  holdingDays: number;
  minScore: number;
  slippagePct: number;
  commissionPct: number;
  positionSizing: 'fixed' | 'dynamic';
  positionSize: number;
  initialCapital: number;
  maxPositions: number;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  params: StrategyParams;
  logic: string;
  isPreset: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface StrategyVersion {
  id: string;
  name: string;
  date: string;
  params: StrategyParams;
}

export interface BacktestMetrics {
  totalReturn: number;
  annualizedReturn: number;
  volatility: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  profitLossRatio: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgHoldingDays: number;
  avgWin: number;
  avgLoss: number;
}

export interface StrategyComparison {
  strategies: Array<{
    id: string;
    name: string;
    metrics: BacktestMetrics | null;
    equityCurve: Array<{ date: string; equity: number }>;
  }>;
  bestReturn?: string;
  bestSharpe?: string;
  lowestDrawdown?: string;
}

interface StrategyState {
  // State
  strategies: Strategy[];
  selectedStrategy: Strategy | null;
  comparison: StrategyComparison | null;
  loading: boolean;
  error: string | null;
  versions: StrategyVersion[];
  versionsLoading: boolean;
  
  // Actions
  fetchStrategies: () => Promise<void>;
  fetchStrategy: (id: string) => Promise<void>;
  createStrategy: (name: string, description: string, params: StrategyParams) => Promise<Strategy>;
  updateStrategy: (id: string, updates: Partial<Strategy>) => Promise<void>;
  deleteStrategy: (id: string) => Promise<void>;
  compareStrategies: (ids: string[], symbol: string, startDate: string, endDate: string) => Promise<void>;
  setSelectedStrategy: (strategy: Strategy | null) => void;
  clearError: () => void;
  fetchVersions: (strategyId: string) => Promise<void>;
  saveVersion: (strategyId: string, name: string) => Promise<void>;
  restoreVersion: (strategyId: string, versionId: string) => Promise<void>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export const useStrategyStore = create<StrategyState>()(
  devtools(
    (set) => ({
      // Initial state
      strategies: [],
      selectedStrategy: null,
      comparison: null,
      loading: false,
      error: null,
      versions: [],
      versionsLoading: false,
      
      // Fetch all strategies
      fetchStrategies: async () => {
        set({ loading: true, error: null });
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies`);
          if (!response.ok) throw new Error('Failed to fetch strategies');
          const data = await response.json();
          set({ strategies: data, loading: false });
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
        }
      },
      
      // Fetch single strategy
      fetchStrategy: async (id: string) => {
        set({ loading: true, error: null });
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies/${id}`);
          if (!response.ok) throw new Error('Failed to fetch strategy');
          const data = await response.json();
          set({ selectedStrategy: data, loading: false });
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
        }
      },
      
      // Create strategy
      createStrategy: async (name, description, params) => {
        set({ loading: true, error: null });
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, params })
          });
          if (!response.ok) throw new Error('Failed to create strategy');
          const data = await response.json();
          set(state => ({ 
            strategies: [...state.strategies, data],
            loading: false 
          }));
          return data;
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
          throw error;
        }
      },
      
      // Update strategy
      updateStrategy: async (id, updates) => {
        set({ loading: true, error: null });
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
          });
          if (!response.ok) throw new Error('Failed to update strategy');
          const data = await response.json();
          set(state => ({
            strategies: state.strategies.map(s => s.id === id ? data : s),
            selectedStrategy: state.selectedStrategy?.id === id ? data : state.selectedStrategy,
            loading: false
          }));
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
        }
      },
      
      // Delete strategy
      deleteStrategy: async (id) => {
        set({ loading: true, error: null });
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies/${id}`, {
            method: 'DELETE'
          });
          if (!response.ok) throw new Error('Failed to delete strategy');
          set(state => ({
            strategies: state.strategies.filter(s => s.id !== id),
            selectedStrategy: state.selectedStrategy?.id === id ? null : state.selectedStrategy,
            loading: false
          }));
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
        }
      },
      
      // Compare strategies
      compareStrategies: async (ids, symbol, startDate, endDate) => {
        set({ loading: true, error: null });
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ strategyIds: ids, symbol, startDate, endDate })
          });
          if (!response.ok) throw new Error('Failed to compare strategies');
          const data = await response.json();
          set({ comparison: data, loading: false });
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
        }
      },
      
      // Set selected strategy
      setSelectedStrategy: (strategy) => set({ selectedStrategy: strategy }),
      
      // Clear error
      clearError: () => set({ error: null }),
      
      // Fetch versions for a strategy
      fetchVersions: async (strategyId: string) => {
        set({ versionsLoading: true });
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies/${strategyId}/versions`);
          if (!response.ok) throw new Error('Failed to fetch versions');
          const data = await response.json();
          set({ versions: data, versionsLoading: false });
        } catch (error) {
          set({ error: (error as Error).message, versionsLoading: false });
        }
      },
      
      // Save current strategy as a new version
      saveVersion: async (strategyId: string, name: string) => {
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies/${strategyId}/version`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
          });
          if (!response.ok) throw new Error('Failed to save version');
          // Refresh versions list
          const versionsResponse = await fetch(`${API_BASE}/strategy/strategies/${strategyId}/versions`);
          if (versionsResponse.ok) {
            const data = await versionsResponse.json();
            set({ versions: data });
          }
        } catch (error) {
          set({ error: (error as Error).message });
        }
      },
      
      // Restore a specific version
      restoreVersion: async (strategyId: string, versionId: string) => {
        try {
          const response = await fetch(`${API_BASE}/strategy/strategies/${strategyId}/versions/${versionId}/restore`, {
            method: 'POST'
          });
          if (!response.ok) throw new Error('Failed to restore version');
          // Refresh strategy data
          const strategyResponse = await fetch(`${API_BASE}/strategy/strategies/${strategyId}`);
          if (strategyResponse.ok) {
            const data = await strategyResponse.json();
            set({ selectedStrategy: data });
          }
        } catch (error) {
          set({ error: (error as Error).message });
        }
      }
    }),
    { name: 'strategy-store' }
  )
);
