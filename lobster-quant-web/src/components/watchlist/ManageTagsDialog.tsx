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
import { useWatchlistStore } from '@/stores/watchlistStore'
import { Plus, X, Tag } from 'lucide-react'

interface ManageTagsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  symbol: string
}

export function ManageTagsDialog({
  open,
  onOpenChange,
  symbol,
}: ManageTagsDialogProps) {
  const { tags, addTag, removeTag } = useWatchlistStore()
  const [newTag, setNewTag] = useState('')

  const symbolTags = tags[symbol] || []

  const handleAddTag = () => {
    const tag = newTag.trim().toLowerCase()
    if (!tag) return
    addTag(symbol, tag)
    setNewTag('')
  }

  const handleRemoveTag = (tag: string) => {
    removeTag(symbol, tag)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Tag className="w-4 h-4" />
            Tags for {symbol}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Add new tag */}
          <div className="flex gap-2">
            <Input
              placeholder="Add a tag (e.g., tech, growth)"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAddTag()
              }}
              autoFocus
            />
            <Button
              onClick={handleAddTag}
              disabled={!newTag.trim()}
              size="sm"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add
            </Button>
          </div>

          {/* Current tags */}
          <div>
            <h4 className="text-sm font-medium mb-2">Current Tags</h4>
            {symbolTags.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No tags yet. Add one above.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {symbolTags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="flex items-center gap-1 text-xs"
                  >
                    {tag}
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      className="ml-0.5 rounded-full hover:bg-muted p-0.5"
                      aria-label={`Remove tag ${tag}`}
                    >
                      <X className="w-2.5 h-2.5" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>
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
