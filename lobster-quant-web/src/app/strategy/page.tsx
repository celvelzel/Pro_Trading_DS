'use client';

import { useEffect, useState } from 'react';
import { useStrategyStore, Strategy, StrategyParams } from '@/stores/strategyStore';
import { StrategyCard, StrategyForm } from '@/components/strategy';
import { Button } from '@/components/ui/button';
import { HelpTooltip } from '@/components/ui/help-tooltip';
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

  const handleCancel = () => {
    setShowForm(false);
    setEditingStrategy(undefined);
  };

  const presetStrategies = strategies.filter(s => s.isPreset);
  const customStrategies = strategies.filter(s => !s.isPreset);

  return (
    <div className="container mx-auto py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold">Strategy Management</h1>
            <HelpTooltip helpKey="strategy.title" />
          </div>
          <p className="text-muted-foreground mt-2">
            Create and manage your trading strategies
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Strategy
        </Button>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive p-4 rounded-lg mb-6">
          {error}
          <Button variant="ghost" size="sm" onClick={clearError} className="ml-2">
            Dismiss
          </Button>
        </div>
      )}

      {showForm && (
        <div className="mb-8">
          <StrategyForm
            strategy={editingStrategy}
            onSubmit={editingStrategy ? handleUpdate : handleCreate}
            onCancel={handleCancel}
          />
        </div>
      )}

      {loading && strategies.length === 0 ? (
        <div className="text-center py-12">Loading strategies...</div>
      ) : (
        <>
          {/* Preset Strategies */}
          <section className="mb-10">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-xl font-semibold">Preset Strategies</h2>
              <HelpTooltip helpKey="strategy.selector" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {presetStrategies.map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                />
              ))}
            </div>
          </section>

          {/* Custom Strategies */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-xl font-semibold">Custom Strategies</h2>
              <HelpTooltip helpKey="strategy.config" />
            </div>
            {customStrategies.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                No custom strategies yet. Create one to get started.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {customStrategies.map(strategy => (
                  <StrategyCard
                    key={strategy.id}
                    strategy={strategy}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
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
    </div>
  );
}
