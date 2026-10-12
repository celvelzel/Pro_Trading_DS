'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useStrategyStore, Strategy, StrategyParams } from '@/stores/strategyStore';
import { StrategyCard, StrategyForm } from '@/components/strategy';
import { VersionHistoryModal } from '@/components/strategy/VersionHistoryModal';
import { Button } from '@/components/ui/button';
import { HelpTooltip } from '@/components/ui/help-tooltip';
import { PageHeader } from '@/components/layout/PageHeader';
import { Plus } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

export default function StrategyPage() {
  const router = useRouter();
  const {
    strategies,
    loading,
    error,
    fetchStrategies,
    createStrategy,
    updateStrategy,
    deleteStrategy,
    clearError
  } = useStrategyStore();

  const [showForm, setShowForm] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<Strategy | undefined>();
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [historyStrategy, setHistoryStrategy] = useState<Strategy | null>(null);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const handleCreate = async (name: string, description: string, params: StrategyParams) => {
    await createStrategy(name, description, params);
    setShowForm(false);
  };

  const handleUpdate = async (name: string, description: string, params: StrategyParams) => {
    if (editingStrategy) {
      await updateStrategy(editingStrategy.id, { name, description, params });
      setEditingStrategy(undefined);
      setShowForm(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleteTarget(id);
  };

  const confirmDelete = async () => {
    if (deleteTarget) {
      await deleteStrategy(deleteTarget);
      setDeleteTarget(null);
    }
  };

  const handleEdit = (strategy: Strategy) => {
    setEditingStrategy(strategy);
    setShowForm(true);
  };

  const handleViewHistory = (strategy: Strategy) => {
    setHistoryStrategy(strategy);
  };

  const handleViewDetails = (strategy: Strategy) => {
    router.push(`/strategy/${strategy.id}`);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingStrategy(undefined);
  };

  const presetStrategies = strategies.filter(s => s.isPreset);
  const customStrategies = strategies.filter(s => !s.isPreset);

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6 p-4 md:p-6">
      <PageHeader
        title="Strategy Management"
        description="Create and manage your trading strategies"
        actions={
          <>
            <HelpTooltip helpKey="strategy.title" />
            <Button onClick={() => setShowForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Strategy
            </Button>
          </>
        }
      />

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={clearError}>
            Dismiss
          </Button>
        </div>
      )}

      {showForm && (
        <StrategyForm
          strategy={editingStrategy}
          onSubmit={editingStrategy ? handleUpdate : handleCreate}
          onCancel={handleCancel}
        />
      )}

      {loading && strategies.length === 0 ? (
        <div className="py-12 text-center text-sm text-muted-foreground">Loading strategies...</div>
      ) : (
        <>
          {/* Preset Strategies */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold tracking-tight text-foreground">Preset Strategies</h2>
              <HelpTooltip helpKey="strategy.selector" />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {presetStrategies.map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          </section>

          {/* Custom Strategies */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold tracking-tight text-foreground">Custom Strategies</h2>
              <HelpTooltip helpKey="strategy.config" />
            </div>
            {customStrategies.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
                No custom strategies yet. Create one to get started.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {customStrategies.map(strategy => (
                  <StrategyCard
                    key={strategy.id}
                    strategy={strategy}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onViewHistory={handleViewHistory}
                    onViewDetails={handleViewDetails}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Strategy</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the strategy.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Version History Modal */}
      <VersionHistoryModal
        strategy={historyStrategy}
        open={!!historyStrategy}
        onOpenChange={(open) => { if (!open) setHistoryStrategy(null); }}
      />
    </div>
  );
}
