import React from 'react'
import { Card, CardContent } from '../../components/ui/card'
import { Construction } from 'lucide-react'

interface ModulePlaceholderProps {
  title: string
  phase: string
  description: string
}

export const ModulePlaceholderPage: React.FC<ModulePlaceholderProps> = ({
  title,
  phase,
  description,
}) => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-stone-900 font-serif">{title}</h1>
        <p className="text-sm text-stone-500 mt-1">{description}</p>
      </div>

      <Card className="border-dashed border-2 border-stone-300 bg-stone-50/60 p-12 text-center">
        <CardContent className="space-y-4">
          <div className="mx-auto w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center text-amber-700">
            <Construction className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-stone-900">{title} Module</h2>
            <p className="text-sm text-stone-500 max-w-md mx-auto mt-1">
              This module is scheduled for implementation in <strong>{phase}</strong>. Authentication and routing for this section are fully wired and secured.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
