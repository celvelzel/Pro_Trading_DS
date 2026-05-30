'use client';

import { useEffect, useState } from 'react';
import { useStrategyStore, Strategy, StrategyVersion } from '@/stores/strategyStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Save, RotateCcw, Clock } from 'lucide-react';

interface VersionHistoryModalProps {
  strategy: Strategy | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function VersionHistoryModal({ strategy, open, onOpenChange }: VersionHistoryModalProps) {
  const { versions, versionsLoading, fetchVersions, saveVersion, restoreVersion } = useStrategyStore();
  const [versionName, setVersionName] = useState('');

  useEffect(() => {
    if (open && strategy) {
      fetchVersions(strategy.id);
      setVersionName('');
    }
  }, [open, strategy, fetchVersions]);

  const handleSave = async () => {
    if (!strategy || !versionName.trim()) return;
    await saveVersion(strategy.id, versionName.trim());
    setVersionName('');
  };

  const handleRestore = async (versionId: string) => {
    if (!strategy) return;
    await restoreVersion(strategy.id, versionId);
    onOpenChange(false);
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Version History</DialogTitle>
          <DialogDescription>
            {strategy ? `Manage versions for "${strategy.name}"` : 'Strategy versions'}
          </DialogDescription>
        </DialogHeader>

        {strategy && (
          <div className="space-y-4">
            {/* Save new version */}
            <div className="flex gap-2">
              <Input
                placeholder="Version name (e.g. v1.0, Aggressive)"
                value={versionName}
                onChange={(e) => setVersionName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSave()}
              />
              <Button onClick={handleSave} disabled={!versionName.trim()}>
                <Save className="h-4 w-4 mr-1" />
                Save
              </Button>
            </div>

            {/* Version list */}
            {versionsLoading ? (
              <div className="text-center py-4 text-muted-foreground">Loading versions...</div>
            ) : versions.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No versions saved yet</p>
                <p className="text-sm">Save the current parameters as a version above</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {versions.map((version) => (
                  <VersionItem
                    key={version.id}
                    version={version}
                    onRestore={handleRestore}
                    formatDate={formatDate}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function VersionItem({
  version,
  onRestore,
  formatDate,
}: {
  version: StrategyVersion;
  onRestore: (id: string) => void;
  formatDate: (date: string) => string;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border rounded-lg p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium">{version.name}</p>
          <p className="text-xs text-muted-foreground">{formatDate(version.date)}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? 'Hide' : 'Details'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onRestore(version.id)}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            Restore
          </Button>
        </div>
      </div>
      {expanded && (
        <div className="mt-2 pt-2 border-t grid grid-cols-2 gap-1 text-xs">
          <div><span className="text-muted-foreground">Holding:</span> {version.params.holdingDays}d</div>
          <div><span className="text-muted-foreground">Min Score:</span> {version.params.minScore}</div>
          <div><span className="text-muted-foreground">Position:</span> {(version.params.positionSize * 100).toFixed(0)}%</div>
          <div><span className="text-muted-foreground">Max Pos:</span> {version.params.maxPositions}</div>
          <div><span className="text-muted-foreground">Slippage:</span> {(version.params.slippagePct * 100).toFixed(2)}%</div>
          <div><span className="text-muted-foreground">Commission:</span> {(version.params.commissionPct * 100).toFixed(2)}%</div>
        </div>
      )}
    </div>
  );
}
