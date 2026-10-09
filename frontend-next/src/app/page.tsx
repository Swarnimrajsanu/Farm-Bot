"use client"

import { useEffect, useMemo } from "react"
import { useStore } from "@/store/useStore"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatDistanceToNow } from "date-fns"
import { motion } from "framer-motion"
import { ShieldCheck, Bug, Activity, Loader2, ThermometerSun } from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"

export default function Dashboard() {
  const { history, loading, error, fetchHistory } = useStore()

  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 10000)
    return () => clearInterval(interval)
  }, [fetchHistory])

  const { latest, totalScans, diseasedCount, avgConfidence } = useMemo(() => {
    const totalScans = history.length
    const diseasedCount = history.filter(d => d.disease && !d.disease.toLowerCase().includes("healthy")).length
    
    const confSum = history.reduce((acc, curr) => acc + curr.confidence, 0)
    const avgConfidence = totalScans > 0 ? (confSum / totalScans) * 100 : 0
    
    return {
      latest: history[0] || null,
      totalScans,
      diseasedCount,
      avgConfidence
    }
  }, [history])

  if (loading && history.length === 0) {
    return <div className="h-full flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
  }

  const isLatestHealthy = latest?.disease?.toLowerCase().includes("healthy")

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Overview of your plant health diagnostics.</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalScans}</div>
          </CardContent>
        </Card>
        <Link href="/history?filter=diseased" className="block transition-transform hover:scale-[1.02]">
          <Card className="h-full border-destructive/20 bg-destructive/5 hover:bg-destructive/10 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Diseases Found</CardTitle>
              <Bug className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-destructive">{diseasedCount}</div>
            </CardContent>
          </Card>
        </Link>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
            <ThermometerSun className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgConfidence.toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Status</CardTitle>
            <ShieldCheck className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-primary">Connected</div>
          </CardContent>
        </Card>
      </div>

      {/* Latest Detection Focus */}
      {latest && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <h2 className="text-xl font-semibold mb-4">Latest Scan</h2>
          <Card className="overflow-hidden border-2 border-primary/20 bg-gradient-to-br from-card to-muted/20">
            <div className="flex flex-col md:flex-row">
              <div className="md:w-1/3 bg-muted">
                <img 
                  src={`${process.env.NEXT_PUBLIC_API_URL}/uploads/${latest.image_file}`} 
                  alt="Recent plant" 
                  className="w-full h-64 md:h-full object-cover"
                />
              </div>
              <div className="p-6 md:w-2/3 flex flex-col justify-center">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <Badge variant={isLatestHealthy ? "success" : "destructive"} className="px-3 py-1 text-sm">
                    {isLatestHealthy ? "Healthy" : "Attention Needed"}
                  </Badge>
                  {latest.is_batch && (
                    <Badge variant="outline" className="px-3 py-1 text-sm bg-primary/5 text-primary border-primary/20">
                      📸 Multi-Shot ({latest.num_photos} photos)
                    </Badge>
                  )}
                  <span className="text-sm text-muted-foreground font-medium ml-auto">
                    {formatDistanceToNow(new Date(latest.timestamp), { addSuffix: true })}
                  </span>
                </div>

                {latest.is_batch && latest.batch_images && (
                  <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
                    {latest.batch_images.map((img, i) => (
                      <img 
                        key={i}
                        src={`${process.env.NEXT_PUBLIC_API_URL}/uploads/${img}`}
                        className="h-16 w-16 rounded-lg object-cover border-2 border-background shadow-sm hover:border-primary transition-colors cursor-zoom-in"
                        alt={`Shot ${i+1}`}
                      />
                    ))}
                  </div>
                )}
                <h3 className="text-3xl font-bold mt-2 mb-4">{latest.disease}</h3>
                
                <div className="mb-6">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-muted-foreground">AI Confidence</span>
                    <span className="font-bold">{(latest.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2.5 w-full bg-secondary rounded-full overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }} 
                      animate={{ width: `${latest.confidence * 100}%` }}
                      transition={{ duration: 1, ease: "easeOut" }}
                      className={cn("h-full", isLatestHealthy ? "bg-primary" : "bg-destructive")} 
                    />
                  </div>
                </div>

                <div className="bg-background rounded-xl p-4 border shadow-sm">
                  <span className="text-sm font-semibold text-muted-foreground block mb-1">Recommended Action</span>
                  <p className="text-foreground">{latest.solution}</p>
                </div>
              </div>
            </div>
          </Card>
        </motion.div>
      )}
    </div>
  )
}
