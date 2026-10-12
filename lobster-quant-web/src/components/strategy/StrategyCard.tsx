'use client';

import { Strategy } from '@/stores/strategyStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Pencil, Trash2, Clock, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StrategyCardProps {
  strategy: Strategy;
  onEdit?: (strategy: Strategy) => void;
  onDelete?: (id: string) => void;
  onViewHistory?: (strategy: Strategy) => void;
  onViewDetails?: (strategy: Strategy) => void;
  onSelect?: (strategy: Strategy) => void;
  isSelected?: boolean;
}

export function StrategyCard({ strategy, onEdit, onDelete, onViewHistory, onViewDetails, onSelect, isSelected }: StrategyCardProps) {
  return (
    <Card
      className={cn(
        'cursor-pointer transition-colors hover:border-primary/40',
        isSelected && 'border-primary ring-1 ring-primary'
      )}
      onClick={() => onSelect?.(strategy)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
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

        <div className="grid grid-cols-2 gap-2 rounded-lg border border-border bg-background p-3 text-sm">
          <div>
            <span className="text-muted-foreground">Holding:</span>{' '}
            <span className="font-mono font-medium">{strategy.params.holdingDays} days</span>
          </div>
          <div>
            <span className="text-muted-foreground">Min Score:</span>{' '}
            <span className="font-mono font-medium">{strategy.params.minScore}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Position:</span>{' '}
            <span className="font-mono font-medium">{(strategy.params.positionSize * 100).toFixed(0)}%</span>
          </div>
          <div>
            <span className="text-muted-foreground">Max Positions:</span>{' '}
            <span className="font-mono font-medium">{strategy.params.maxPositions}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onViewDetails?.(strategy);
            }}
          >
            <Eye className="h-3 w-3 mr-1" />
            Details
          </Button>
          {!strategy.isPreset && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onViewHistory?.(strategy);
                }}
              >
                <Clock className="h-3 w-3 mr-1" />
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
                <Pencil className="h-3 w-3 mr-1" />
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
                <Trash2 className="h-3 w-3 mr-1" />
                Delete
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
