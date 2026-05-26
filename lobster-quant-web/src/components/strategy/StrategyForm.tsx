'use client';

import { useState } from 'react';
import { Strategy, StrategyParams } from '@/stores/strategyStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface StrategyFormProps {
  strategy?: Strategy;
  onSubmit: (name: string, description: string, params: StrategyParams) => Promise<void>;
  onCancel: () => void;
}

export function StrategyForm({ strategy, onSubmit, onCancel }: StrategyFormProps) {
  const [name, setName] = useState(strategy?.name || '');
  const [description, setDescription] = useState(strategy?.description || '');
  const [loading, setLoading] = useState(false);
  
  const [params, setParams] = useState<StrategyParams>(
    strategy?.params || {
      holdingDays: 20,
      minScore: 60,
      slippagePct: 0.001,
      commissionPct: 0.001,
      positionSizing: 'fixed',
      positionSize: 0.1,
      initialCapital: 100000,
      maxPositions: 5
    }
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit(name, description, params);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{strategy ? 'Edit Strategy' : 'Create Strategy'}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="holdingDays">Holding Days</Label>
              <Input
                id="holdingDays"
                type="number"
                min={5}
                max={100}
                value={params.holdingDays}
                onChange={(e) => setParams({ ...params, holdingDays: parseInt(e.target.value) })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="minScore">Min Score</Label>
              <Input
                id="minScore"
                type="number"
                min={0}
                max={100}
                value={params.minScore}
                onChange={(e) => setParams({ ...params, minScore: parseInt(e.target.value) })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="positionSize">Position Size (%)</Label>
              <Input
                id="positionSize"
                type="number"
                min={1}
                max={100}
                value={params.positionSize * 100}
                onChange={(e) => setParams({ ...params, positionSize: parseInt(e.target.value) / 100 })}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="maxPositions">Max Positions</Label>
              <Input
                id="maxPositions"
                type="number"
                min={1}
                max={20}
                value={params.maxPositions}
                onChange={(e) => setParams({ ...params, maxPositions: parseInt(e.target.value) })}
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>Position Sizing</Label>
            <Select
              value={params.positionSizing}
              onValueChange={(value: 'fixed' | 'dynamic') => 
                setParams({ ...params, positionSizing: value })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fixed">Fixed</SelectItem>
                <SelectItem value="dynamic">Dynamic</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : strategy ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
