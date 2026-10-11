"use client"

import { Suspense, useEffect, useState } from "react"
import { useStore } from "@/store/useStore"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { format } from "date-fns"
import { LayoutGrid, List } from "lucide-react"
import Link from "next/link"

import { useSearchParams } from "next/navigation"

function HistoryContent() {
  const { history, fetchHistory } = useStore()
  const [view, setView] = useState<"grid" | "table">("table")
  const searchParams = useSearchParams()
  const filter = searchParams.get("filter")

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const filteredHistory = filter === "diseased" 
    ? history.filter(item => !item.disease.toLowerCase().includes("healthy"))
    : history

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {filter === "diseased" ? "Diseased Scans" : "History Log"}
          </h1>
          <p className="text-muted-foreground mt-1">
            {filter === "diseased" 
              ? `Showing all ${filteredHistory.length} infections found.` 
              : "Review all past plant disease scans."}
          </p>
        </div>
        <div className="bg-card border rounded-lg flex p-1 shadow-sm">
          <button 
            onClick={() => setView("table")}
            className={`p-2 rounded-md transition-colors ${view === "table" ? "bg-muted" : "hover:bg-muted/50"}`}
          >
            <List className="w-4 h-4" />
          </button>
          <button 
            onClick={() => setView("grid")}
            className={`p-2 rounded-md transition-colors ${view === "grid" ? "bg-muted" : "hover:bg-muted/50"}`}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
        </div>
      </div>

      {view === "table" ? (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted/50 text-muted-foreground uppercase text-xs">
                <tr>
                  <th className="px-6 py-4 font-medium">Image</th>
                  <th className="px-6 py-4 font-medium">Disease Detected</th>
                  <th className="px-6 py-4 font-medium">Confidence</th>
                  <th className="px-6 py-4 font-medium">Date & Time</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredHistory.map((item, idx) => {
                  const isHealthy = item.disease.toLowerCase().includes("healthy")
                  return (
                    <Link href={`/reports/${item.image_file}`} key={idx} legacyBehavior>
                      <tr className="bg-card hover:bg-muted/30 transition-colors cursor-pointer">
                        <td className="px-6 py-3">
                          <img 
                            src={`${process.env.NEXT_PUBLIC_API_URL}/uploads/${item.image_file}`} 
                            className="h-12 w-12 rounded object-cover border shadow-sm" 
                            alt="Plant"
                          />
                        </td>
                        <td className="px-6 py-4 font-medium">
                          <div className="flex items-center gap-3">
                            <Badge variant={isHealthy ? "success" : "destructive"}>
                              {isHealthy ? "Healthy" : "Infected"}
                            </Badge>
                            {item.disease}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <span className="w-10 font-medium">{(item.confidence * 100).toFixed(0)}%</span>
                            <div className="w-20 h-1.5 bg-secondary rounded-full overflow-hidden">
                              <div 
                                className={`h-full ${isHealthy ? "bg-primary" : "bg-destructive"}`} 
                                style={{ width: `${item.confidence * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-muted-foreground">
                          {format(new Date(item.timestamp), "MMM d, yyyy • h:mm a")}
                        </td>
                      </tr>
                    </Link>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredHistory.map((item, idx) => {
            const isHealthy = item.disease.toLowerCase().includes("healthy")
            return (
              <Link href={`/reports/${item.image_file}`} key={idx}>
                <Card className="overflow-hidden hover:shadow-md transition-all flex flex-col cursor-pointer h-full border-transparent hover:border-border">
                  <img 
                    src={`${process.env.NEXT_PUBLIC_API_URL}/uploads/${item.image_file}`} 
                    className="w-full h-48 object-cover" 
                    alt="Plant"
                  />
                  <CardContent className="p-5 flex-1 flex flex-col">
                    <div className="flex justify-between items-start mb-3">
                      <Badge variant={isHealthy ? "success" : "destructive"}>
                        {isHealthy ? "Healthy" : "Infected"}
                      </Badge>
                      <span className="text-xs text-muted-foreground font-medium">
                        {format(new Date(item.timestamp), "MMM d • h:mm a")}
                      </span>
                    </div>
                    <h3 className="font-semibold text-lg line-clamp-1 mb-1">{item.disease}</h3>
                    <p className="text-sm text-muted-foreground mb-4 line-clamp-2 flex-1">
                      {item.solution}
                    </p>
                    <div className="mt-auto pt-4 border-t">
                      <div className="flex justify-between text-xs font-semibold text-muted-foreground mb-1.5">
                        <span>Confidence</span>
                        <span>{(item.confidence * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function HistoryPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-muted-foreground">Loading history...</div>}>
      <HistoryContent />
    </Suspense>
  )
}
