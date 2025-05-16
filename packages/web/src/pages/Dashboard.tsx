import { useQuery } from "@tanstack/react-query";
import { healthCheck } from "@/api/client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Link } from "react-router";

export default function Dashboard() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: healthCheck,
    refetchInterval: 10_000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">TMT Markets</h1>
        <p className="text-muted-foreground">
          Quantitative analysis and portfolio management
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div
                className={`h-3 w-3 rounded-full ${
                  health.data?.status === "ok"
                    ? "bg-green-500"
                    : health.isLoading
                    ? "bg-yellow-500"
                    : "bg-red-500"
                }`}
              />
              <span className="text-2xl font-bold">
                {health.data?.status === "ok"
                  ? "Online"
                  : health.isLoading
                  ? "Checking..."
                  : "Offline"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Link to="/covariance" className="no-underline">
          <Card className="hover:border-primary transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle>Covariance Matrix</CardTitle>
              <CardDescription>
                Estimate covariance matrices using sample, Ledoit-Wolf, or
                shrinkage methods
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link to="/portfolio" className="no-underline">
          <Card className="hover:border-primary transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle>Portfolio Optimization</CardTitle>
              <CardDescription>
                Optimize portfolio weights using mean-variance, max Sharpe, or
                risk parity
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link to="/backtest" className="no-underline">
          <Card className="hover:border-primary transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle>Backtesting</CardTitle>
              <CardDescription>
                Run backtests with periodic rebalancing and view equity curves
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}
