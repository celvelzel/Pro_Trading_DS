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
              <Plus className="w-4 h-4 mr-1" />
              Create
            </Button>
          </div>

          {/* Group list */}
          {groupNames.length === 0 ? (
            <div className="text-center py-6 text-text-tertiary">
              <FolderOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No groups yet. Create one above.</p>
            </div>
          ) : (
            <div className="flex gap-4">
              {/* Left: group names */}
              <div className="w-1/3 space-y-1 border-r pr-3">
                {groupNames.map((name) => (
                  <div
                    key={name}
                    className={`flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer transition-colors ${
                      selectedGroup === name
                        ? 'bg-accent text-accent-foreground'
                        : 'hover:bg-muted'
                    }`}
                    onClick={() => setSelectedGroup(name)}
                  >
                    <span className="text-sm truncate flex-1">
                      {name}
                      <span className="ml-1 text-xs text-text-tertiary">
                        ({(groups[name] || []).length})
                      </span>
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteGroup(name)
                      }}
                      className="ml-1 p-0.5 rounded hover:bg-destructive/10 text-text-tertiary hover:text-destructive"
                      title="Delete group"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Right: symbols in selected group */}
              <div className="flex-1 space-y-3">
                {selectedGroup ? (
                  <>
                    <div>
                      <h4 className="text-sm font-medium mb-2">
                        Symbols in &ldquo;{selectedGroup}&rdquo;
                      </h4>
                      {currentGroupSymbols.length === 0 ? (
                        <p className="text-xs text-text-tertiary">
                          No symbols in this group yet.
                        </p>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {currentGroupSymbols.map((symbol) => (
                            <Badge
                              key={symbol}
                              variant="secondary"
                              className="flex items-center gap-1 text-xs"
                            >
                              {symbol}
                              <button
                                onClick={() => handleRemoveFromGroup(symbol)}
                                className="ml-0.5 rounded-full hover:bg-muted p-0.5"
                              >
                                <X className="w-2.5 h-2.5" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>

                    {availableSymbols.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-2">
                          Add symbols
                        </h4>
                        <div className="flex flex-wrap gap-1">
                          {availableSymbols.map((symbol) => (
                            <Badge
                              key={symbol}
                              variant="outline"
                              className="cursor-pointer hover:bg-accent text-xs"
                              onClick={() => handleAddToGroup(symbol)}
                            >
                              <Plus className="w-2.5 h-2.5 mr-0.5" />
                              {symbol}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-6 text-text-tertiary">
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
