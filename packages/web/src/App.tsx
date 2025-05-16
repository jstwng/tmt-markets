import { Routes, Route, Link, useLocation } from "react-router";
import Chat from "@/pages/Chat";
import Dashboard from "@/pages/Dashboard";
import Covariance from "@/pages/Covariance";
import Portfolio from "@/pages/Portfolio";
import Backtest from "@/pages/Backtest";
import { cn } from "@/lib/utils";

const navItems = [
  { path: "/", label: "Chat" },
  { path: "/dashboard", label: "Dashboard" },
  { path: "/covariance", label: "Covariance" },
  { path: "/portfolio", label: "Portfolio" },
  { path: "/backtest", label: "Backtest" },
];

function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-6xl mx-auto flex h-14 items-center px-6">
          <Link to="/" className="font-bold text-base mr-8 no-underline text-foreground tracking-tight">
            TMT Markets
          </Link>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "text-sm transition-colors no-underline px-3 py-1.5 rounded-md",
                  location.pathname === item.path
                    ? "bg-muted text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/covariance" element={<Covariance />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/backtest" element={<Backtest />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
