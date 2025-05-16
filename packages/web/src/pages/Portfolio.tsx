import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Plot from "@/components/Plot";
import { optimizePortfolio } from "@/api/client";
import type { PortfolioOptimizeRequest, PortfolioOptimizeResponse } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Portfolio() {
  const [tickers, setTickers] = useState("AAPL,MSFT,GOOGL,AMZN,META");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [objective, setObjective] = useState<PortfolioOptimizeRequest["objective"]>("max_sharpe");
  const [maxWeight, setMaxWeight] = useState("");

  const mutation = useMutation({
    mutationFn: optimizePortfolio,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      tickers: tickers.split(",").map((t) => t.trim()),
      start_date: startDate,
      end_date: endDate,
      objective,
      max_weight: maxWeight ? parseFloat(maxWeight) : null,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Portfolio Optimization</h1>
        <p className="text-muted-foreground">
          Optimize portfolio weights using mean-variance framework
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <div className="space-y-2">
              <Label htmlFor="tickers">Tickers</Label>
              <Input
                id="tickers"
                value={tickers}
                onChange={(e) => setTickers(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="start">Start Date</Label>
              <Input
                id="start"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end">End Date</Label>
              <Input
                id="end"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Objective</Label>
              <Select value={objective} onValueChange={(v) => setObjective(v as PortfolioOptimizeRequest["objective"])}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="max_sharpe">Max Sharpe</SelectItem>
                  <SelectItem value="min_variance">Min Variance</SelectItem>
                  <SelectItem value="risk_parity">Risk Parity</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="max-weight">Max Weight (optional)</Label>
              <Input
                id="max-weight"
                type="number"
                step="0.05"
                min="0"
                max="1"
                placeholder="e.g. 0.4"
                value={maxWeight}
                onChange={(e) => setMaxWeight(e.target.value)}
              />
            </div>
            <div className="md:col-span-2 lg:col-span-5">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Optimizing..." : "Optimize"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {mutation.error && (
        <Card className="border-destructive">
          <CardContent className="pt-6 text-destructive">
            {mutation.error.message}
          </CardContent>
        </Card>
      )}

      {mutation.data && <PortfolioResults data={mutation.data} />}
    </div>
  );
}

function PortfolioResults({ data }: { data: PortfolioOptimizeResponse }) {
  const tickers = Object.keys(data.weights);
  const weights = Object.values(data.weights);

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Optimal Weights</CardTitle>
        </CardHeader>
        <CardContent>
          <Plot
            data={[
              {
                labels: tickers,
                values: weights,
                type: "pie",
                textinfo: "label+percent",
                hoverinfo: "label+value+percent",
              },
            ]}
            layout={{
              width: 500,
              height: 400,
              margin: { l: 20, r: 20, t: 20, b: 20 },
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Portfolio Metrics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Expected Return</p>
              <p className="text-2xl font-bold">
                {(data.expected_return * 100).toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Expected Volatility</p>
              <p className="text-2xl font-bold">
                {(data.expected_volatility * 100).toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
              <p className="text-2xl font-bold">{data.sharpe.toFixed(4)}</p>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium">Weight Allocation</p>
            {tickers.map((ticker, i) => (
              <div key={ticker} className="flex items-center justify-between">
                <span className="text-sm">{ticker}</span>
                <div className="flex items-center gap-2">
                  <div className="h-2 bg-primary rounded" style={{ width: `${weights[i] * 200}px` }} />
                  <span className="text-sm text-muted-foreground w-16 text-right">
                    {(weights[i] * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
