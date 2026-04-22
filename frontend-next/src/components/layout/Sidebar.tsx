"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Activity, History, FileText, Leaf, Moon, Sun } from "lucide-react"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"
import { useEffect } from "react"

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Live Feed", href: "/live", icon: Activity },
  { name: "History", href: "/history", icon: History },
  { name: "Reports", href: "/history", icon: FileText },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { isDarkMode, toggleDarkMode } = useStore()

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark")
    } else {
      document.documentElement.classList.remove("dark")
    }
  }, [isDarkMode])

  return (
    <aside className="w-64 border-r bg-card flex flex-col">
      <div className="h-16 flex items-center px-6 border-b">
        <Leaf className="w-6 h-6 text-primary mr-2" />
        <span className="font-bold text-lg tracking-tight">AgriSense</span>
      </div>
      
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive 
                  ? "bg-primary/10 text-primary" 
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              )}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.name}</span>
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t">
        <button 
          onClick={toggleDarkMode}
          className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
        >
          {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          <span>{isDarkMode ? "Light Mode" : "Dark Mode"}</span>
        </button>
      </div>
    </aside>
  )
}
