'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useSyncWatchlist } from '@/stores/watchlistStore'
import { Plus, X, FolderOpen, Trash2 } from 'lucide-react'

interface ManageGroupsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ManageGroupsDialog({
  open,
  onOpenChange,
}: ManageGroupsDialogProps) {
  const { groups, symbols, createGroup, deleteGroup, addToGroup, removeFromGroup } =
    useSyncWatchlist()
  const [newGroupName, setNewGroupName] = useState('')
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)

  const groupNames = Object.keys(groups).sort()

  const handleCreateGroup = () => {
    const name = newGroupName.trim()
    if (!name) return
    createGroup(name)
    setNewGroupName('')
    setSelectedGroup(name)
  }

  const handleAddToGroup = (symbol: string) => {
    if (!selectedGroup) return
    addToGroup(selectedGroup, symbol)
  }

  const handleRemoveFromGroup = (symbol: string) => {
    if (!selectedGroup) return
    removeFromGroup(selectedGroup, symbol)
  }

  const handleDeleteGroup = (name: string) => {
    deleteGroup(name)
    if (selectedGroup === name) {
      setSelectedGroup(null)
    }
  }

  const currentGroupSymbols = selectedGroup ? groups[selectedGroup] || [] : []
  const availableSymbols = selectedGroup
    ? symbols.filter((s) => !currentGroupSymbols.includes(s))
    : []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Manage Groups</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Create new group */}
          <div className="flex gap-2">
            <Input
              placeholder="New group name"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateGroup()
              }}
            />
            <Button
              onClick={handleCreateGroup}
              disabled={!newGroupName.trim()}
              size="sm"
            >
              <Plus />
              Create
            </Button>
          </div>

          {/* Group list */}
          {groupNames.length === 0 ? (
            <div className="py-6 text-center text-muted-foreground">
              <FolderOpen className="mx-auto mb-2 size-8 opacity-50" />
              <p className="text-sm">No groups yet. Create one above.</p>
            </div>
          ) : (
            <div className="flex gap-4">
              {/* Left: group names */}
              <div className="w-1/3 space-y-1 border-r border-border pr-3">
                {groupNames.map((name) => (
                  <div
                    key={name}
                    className={`flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 transition-colors ${
                      selectedGroup === name
                        ? 'bg-accent text-accent-foreground'
                        : 'hover:bg-muted'
                    }`}
                    onClick={() => setSelectedGroup(name)}
                  >
                    <span className="flex-1 truncate text-sm">
                      {name}
                      <span className="ml-1 font-mono text-xs tabular-nums text-muted-foreground">
                        ({(groups[name] || []).length})
                      </span>
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteGroup(name)
                      }}
                      className="ml-1 rounded p-0.5 text-muted-foreground transition-colors hover:bg-error/10 hover:text-error"
                      title="Delete group"
                    >
                      <Trash2 className="size-3" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Right: symbols in selected group */}
              <div className="flex-1 space-y-3">
                {selectedGroup ? (
                  <>
                    <div>
                      <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        Symbols in &ldquo;{selectedGroup}&rdquo;
                      </h4>
                      {currentGroupSymbols.length === 0 ? (
                        <p className="text-xs text-muted-foreground">
                          No symbols in this group yet.
                        </p>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {currentGroupSymbols.map((symbol) => (
                            <Badge
                              key={symbol}
                              variant="secondary"
                              className="flex items-center gap-1 font-mono text-xs"
                            >
                              {symbol}
                              <button
                                onClick={() => handleRemoveFromGroup(symbol)}
                                className="ml-0.5 rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-muted hover:text-error"
                              >
                                <X className="size-2.5" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>

                    {availableSymbols.length > 0 && (
                      <div>
                        <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          Add symbols
                        </h4>
                        <div className="flex flex-wrap gap-1">
                          {availableSymbols.map((symbol) => (
                            <Badge
                              key={symbol}
                              variant="outline"
                              className="cursor-pointer font-mono text-xs transition-colors hover:bg-accent hover:text-accent-foreground"
                              onClick={() => handleAddToGroup(symbol)}
                            >
                              <Plus className="size-2.5" />
                              {symbol}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="py-6 text-center text-muted-foreground">
                    <p className="text-sm">Select a group to manage its symbols.</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
