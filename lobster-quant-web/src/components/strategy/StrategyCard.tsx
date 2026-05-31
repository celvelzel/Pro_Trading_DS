'use client';

import { Strategy } from '@/stores/strategyStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Pencil, Trash2, Clock } from 'lucide-react';

interface StrategyCardProps {
  strategy: Strategy;
  onEdit?: (strategy: Strategy) => void;
  onDelete?: (id: string) => void;
  onViewHistory?: (strategy: Strategy) => void;
  onSelect?: (strategy: Strategy) => void;
  isSelected?: boolean;
}

export function StrategyCard({ strategy, onEdit, onDelete, onViewHistory, onSelect, isSelected }: StrategyCardProps) {
  return (
    <Card 
      className={`cursor-pointer transition-all hover:shadow-md ${isSelected ? 'ring-2 ring-primary' : ''}`}
      onClick={() => onSelect?.(strategy)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{strategy.name}</CardTitle>
          <div className="flex gap-1">
            {strategy.isPreset && (
              <Badge variant="secondary">Preset</Badge>
            )}
            <Badge variant="outline">{strategy.logic}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          {strategy.description || 'No description'}
        </p>
        
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-muted-foreground">Holding:</span>{' '}
            <span className="font-medium">{strategy.params.holdingDays} days</span>
          </div>
          <div>
            <span className="text-muted-foreground">Min Score:</span>{' '}
            <span className="font-medium">{strategy.params.minScore}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Position:</span>{' '}
            <span className="font-medium">{(strategy.params.positionSize * 100).toFixed(0)}%</span>
          </div>
          <div>
            <span className="text-muted-foreground">Max Positions:</span>{' '}
            <span className="font-medium">{strategy.params.maxPositions}</span>
          </div>
        </div>
        
        {!strategy.isPreset && (
          <div className="flex gap-2 mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onViewHistory?.(strategy);
              }}
            >
              <Clock className="h-4 w-4 mr-1" />
              History
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onEdit?.(strategy);
              }}
            >
              <Pencil className="h-4 w-4 mr-1" />
              Edit
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onDelete?.(strategy.id);
              }}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Delete
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
