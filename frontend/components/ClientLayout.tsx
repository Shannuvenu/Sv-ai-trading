"use client";
import { useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, BarChart3, Star, Briefcase, LineChart, CandlestickChart, Bell, LogOut, Menu, X } from "lucide-react";
import { useState } from "react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/markets", label: "Markets", icon: BarChart3 },
  { href: "/watchlists", label: "Watchlists", icon: Star },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/analysis", label: "Analysis", icon: CandlestickChart },
  { href: "/backtest", label: "Backtest", icon: LineChart },
  { href: "/alerts", label: "Alerts", icon: Bell },
];

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, loadUser, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const didLoad = useRef(false);

  useEffect(() => {
    if (!didLoad.current) { didLoad.current = true; loadUser(); }
  }, [loadUser]);

  const isAuthPage = pathname === "/login" || pathname === "/register";

  if (isLoading) {
    return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  }

  if (!user && !isAuthPage) {
    router.replace("/login");
    return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" /></div>;
  }

  if (isAuthPage) return <>{children}</>;

  const handleLogout = () => { logout(); router.replace("/login"); };

  return (
    <div className="h-screen flex overflow-hidden bg-background">
      {sidebarOpen && <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setSidebarOpen(false)} />}
      <aside className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-surface border-r border-border transform transition-transform lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="h-16 flex items-center justify-between px-6 border-b border-border">
          <Link href="/dashboard" className="text-lg font-bold text-primary">SV Trading</Link>
          <button className="lg:hidden" onClick={() => setSidebarOpen(false)}><X size={20} /></button>
        </div>
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link key={item.href} href={item.href} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${isActive ? "bg-primary/20 text-primary" : "text-muted hover:text-foreground hover:bg-surface-hover"}`}><Icon size={18} />{item.label}</Link>
            );
          })}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted truncate">{user?.username}</span>
            <button onClick={handleLogout} className="text-muted hover:text-danger transition-colors"><LogOut size={16} /></button>
          </div>
        </div>
      </aside>
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-16 flex items-center px-6 border-b border-border lg:hidden">
          <button onClick={() => setSidebarOpen(true)}><Menu size={20} /></button>
          <span className="ml-3 font-bold text-primary">SV Trading</span>
        </header>
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </main>
    </div>
  );
}
