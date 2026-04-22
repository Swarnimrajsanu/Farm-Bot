"use client"

import { useEffect, useState } from "react"
import { useStore } from "@/store/useStore"
import { motion, AnimatePresence } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { formatDistanceToNow } from "date-fns"

export default function LiveFeedPage() {
  const { history, fetchHistory } = useStore()
  const [previousLatest, setPreviousLatest] = useState<string | null>(null)
  
  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 5000) // Auto-refresh every 5 seconds
    return () => clearInterval(interval)
  }, [fetchHistory])

  // Simple unoptimized approach for highlighting new feeds
  useEffect(() => {
    if (history.length > 0) {
      if (previousLatest !== null && history[0].image_file !== previousLatest) {
        // Flash animation trigger could be added here
      }
      setPreviousLatest(history[0].image_file)
    }
  }, [history, previousLatest])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            Live Feed
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            </span>
          </h1>
          <p className="text-muted-foreground mt-1">Real-time plant detections from your ESP32-CAM stream.</p>
        </div>
      </div>

      <div className="grid gap-6">
        <AnimatePresence>
          {history.map((item, idx) => {
            const isLatest = idx === 0
            const isHealthy = item.disease.toLowerCase().includes("healthy")
            
            return (
              <motion.div
                key={item.image_file}
                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                layout
                transition={{ type: "spring", stiffness: 300, damping: 24 }}
              >
                <Card className={`overflow-hidden transition-all duration-500 ${isLatest ? 'ring-2 ring-primary shadow-lg shadow-primary/20 scale-[1.02]' : 'opacity-80'}`}>
                  <div className="flex flex-col md:flex-row">
                    <div className="md:w-64 shrink-0 relative bg-muted">
                      <img 
                        src={`http://127.0.0.1:8000/uploads/${item.image_file}`} 
                        className="w-full h-full object-cover aspect-video md:aspect-square" 
                        alt="Live scan"
                      />
                      {isLatest && (
                        <div className="absolute top-2 left-2 bg-red-500 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded shadow-sm">
                          Latest Scan
                        </div>
                      )}
                    </div>
                    <div className="p-6 flex-1 flex flex-col justify-center">
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="text-2xl font-bold">{item.disease}</h3>
                        <Badge variant={isHealthy ? "success" : "destructive"}>
                          {isHealthy ? "Healthy" : "Attention"}
                        </Badge>
                      </div>
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between text-sm font-medium mb-1">
                            <span>Confidence</span>
                            <span>{(item.confidence * 100).toFixed(1)}%</span>
                          </div>
                          <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                            <div className={`h-full ${isHealthy ? 'bg-primary' : 'bg-destructive'}`} style={{ width: `${item.confidence * 100}%` }} />
                          </div>
                        </div>
                        <div className="bg-muted/50 p-3 rounded-lg border text-sm">
                          <strong className="text-foreground block mb-1">Recommendation:</strong>
                          <span className="text-muted-foreground">{item.solution}</span>
                        </div>
                        <div className="text-xs text-muted-foreground font-medium">
                          Captured {formatDistanceToNow(new Date(item.timestamp), { addSuffix: true })}
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
