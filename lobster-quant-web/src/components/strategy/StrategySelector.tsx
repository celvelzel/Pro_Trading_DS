'use client';

import { useEffect } from 'react';
import { useStrategyStore } from '@/stores/strategyStore';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface StrategySelectorProps {
  value?: string;
  onChange: (strategyId: string) => void;
  excludePresets?: boolean;
}

export function StrategySelector({ value, onChange, excludePresets = false }: StrategySelectorProps) {
  const { strategies, loading, fetchStrategies } = useStrategyStore();
  
  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);
  
  const filteredStrategies = excludePresets 
    ? strategies.filter(s => !s.isPreset)
    : strategies;

  return (
    <Select value={value} onValueChange={(value) => value && onChange(value)} disabled={loading}>
      <SelectTrigger>
        <SelectValue placeholder={loading ? 'Loading...' : 'Select strategy'} />
      </SelectTrigger>
      <SelectContent>
        {filteredStrategies.map(strategy => (
          <SelectItem key={strategy.id} value={strategy.id}>
            {strategy.name}
            {strategy.isPreset && ' (Preset)'}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
