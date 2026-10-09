"use client"

import { useStore } from "@/store/useStore"
import { useParams, useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { format } from "date-fns"
import { ArrowLeft, Download, ShieldAlert, CheckCircle2, ChevronRight, Activity, Beaker } from "lucide-react"

export default function ReportDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { history, fetchHistory } = useStore()
  
  const id = params?.id as string
  const item = history.find(h => h.image_file === id)

  useEffect(() => {
    if (history.length === 0) {
      fetchHistory()
    }
  }, [history.length, fetchHistory])

  if (!item) {
    return <div className="p-8 text-center text-muted-foreground">Loading report...</div>
  }

  const isHealthy = item.disease.toLowerCase().includes("healthy")

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.back()}
            className="p-2 hover:bg-muted rounded-full transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-muted-foreground" />
          </button>
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <span>History</span>
              <ChevronRight className="w-3 h-3" />
              <span>Report Details</span>
            </div>
            <h1 className="text-2xl font-bold">Analysis Report</h1>
          </div>
        </div>
        <button 
          onClick={() => window.print()}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-sm"
        >
          <Download className="w-4 h-4" />
          <span>Export PDF</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Image & Quick Facts */}
        <div className="space-y-6 lg:col-span-1">
          <Card className="overflow-hidden">
            <img 
              src={`${process.env.NEXT_PUBLIC_API_URL}/uploads/${item.image_file}`} 
              alt="Analyzed Plant" 
              className="w-full h-auto aspect-square object-cover"
            />
          </Card>
          
          <Card>
            <CardContent className="p-5 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-muted-foreground mb-1">Date Scanned</h3>
                <p className="font-medium">{format(new Date(item.timestamp), "PPPP • p")}</p>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-muted-foreground mb-1">Image Reference ID</h3>
                <p className="font-mono text-xs bg-muted p-1.5 rounded text-foreground">{item.image_file}</p>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-muted-foreground mb-1">Model Version</h3>
                <p className="font-medium flex items-center gap-2">
                  <Beaker className="w-4 h-4 text-primary" />
                  AgriSense v1.0 (MobileNetV2)
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Details */}
        <div className="lg:col-span-2 space-y-6">
          <Card className={`border-l-4 ${isHealthy ? 'border-l-primary' : 'border-l-destructive'}`}>
            <CardContent className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <Badge variant={isHealthy ? "success" : "destructive"} className="mb-2">
                    {isHealthy ? "Healthy" : "Infection Detected"}
                  </Badge>
                  <h2 className="text-3xl font-bold">{item.disease}</h2>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium text-muted-foreground mb-1">Confidence Score</div>
                  <div className="text-2xl font-bold bg-muted px-3 py-1 rounded-lg">
                    {(item.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mt-6 pt-6 border-t">
                <div className="flex items-center gap-3">
                  <div className={`p-3 rounded-full ${isHealthy ? 'bg-primary/20 text-primary' : 'bg-destructive/20 text-destructive'}`}>
                    {isHealthy ? <CheckCircle2 className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground font-medium">Status Check</p>
                    <p className="font-bold">{isHealthy ? 'Optimal' : 'Needs Action'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-secondary rounded-full text-secondary-foreground">
                    <Activity className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground font-medium">Data Source</p>
                    <p className="font-bold">ESP32-CAM Node</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6 space-y-6">
              <div>
                <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
                  <span className="text-2xl">📋</span> Executive Summary
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  Based on the visual analysis performed by the AI model, the plant sample indicates characteristics consistent with <strong>{item.disease.toLowerCase()}</strong>. The model arrived at this conclusion with a <strong>{(item.confidence * 100).toFixed(1)}% degree of certainty</strong>.
                </p>
              </div>

              <div className="pt-4 border-t">
                <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
                  <span className="text-2xl">💊</span> Recommended Treatment Plan
                </h3>
                <div className="bg-muted p-5 rounded-xl border">
                  <p className="font-medium leading-relaxed">{item.solution}</p>
                </div>
              </div>

              {!isHealthy && (
                <div className="pt-4 border-t">
                  <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
                    <span className="text-2xl">🛡️</span> Prevention Tips
                  </h3>
                  <ul className="list-disc list-inside space-y-2 text-muted-foreground">
                    <li>Maintain adequate spacing between plants to ensure good airflow.</li>
                    <li>Water at the base of the plant avoiding contact with foliage.</li>
                    <li>Regularly sanitize pruning equipment between uses.</li>
                    <li>Remove and destroy fallen leaves and debris around the crop area.</li>
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
