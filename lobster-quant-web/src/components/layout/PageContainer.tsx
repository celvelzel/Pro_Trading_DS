import { cn } from '@/lib/utils'

interface PageContainerProps {
  children: React.ReactNode
  className?: string
}

export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <main className={cn('flex-1 p-4 md:p-6 lg:p-8', className)}>
      {children}
    </main>
  )
}
