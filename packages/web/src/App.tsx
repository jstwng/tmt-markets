import { Routes, Route, Link, useLocation } from "react-router";
import Dashboard from "@/pages/Dashboard";
import Covariance from "@/pages/Covariance";
import Portfolio from "@/pages/Portfolio";
import Backtest from "@/pages/Backtest";
import { cn } from "@/lib/utils";

const navItems = [
  { path: "/", label: "Dashboard" },
  { path: "/covariance", label: "Covariance" },
  { path: "/portfolio", label: "Portfolio" },
  { path: "/backtest", label: "Backtest" },
];

function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto flex h-14 items-center px-6">
          <Link to="/" className="font-bold text-lg mr-8 no-underline text-foreground">
            TMT Markets
          </Link>
          <nav className="flex gap-4">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "text-sm transition-colors no-underline",
                  location.pathname === item.path
                    ? "text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="container mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/covariance" element={<Covariance />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/backtest" element={<Backtest />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
