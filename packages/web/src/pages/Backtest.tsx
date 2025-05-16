import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Plot from "@/components/Plot";
import { runBacktest } from "@/api/client";
import type { BacktestRequest, BacktestResponse } from "@/api/types";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function Backtest() {
  const [tickers, setTickers] = useState("AAPL,MSFT,GOOGL");
  const [weightsStr, setWeightsStr] = useState("0.4,0.3,0.3");
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [capital, setCapital] = useState("100000");
  const [rebalanceFreq, setRebalanceFreq] = useState<BacktestRequest["rebalance_freq"]>("monthly");

  const mutation = useMutation({
    mutationFn: runBacktest,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const tickerList = tickers.split(",").map((t) => t.trim());
    const weightList = weightsStr.split(",").map((w) => parseFloat(w.trim()));
    const weights: Record<string, number> = {};
    tickerList.forEach((t, i) => {
      weights[t] = weightList[i] ?? 0;
    });

    mutation.mutate({
      tickers: tickerList,
      weights,
      start_date: startDate,
      end_date: endDate,
      initial_capital: parseFloat(capital),
      rebalance_freq: rebalanceFreq,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Backtesting</h1>
        <p className="text-muted-foreground">
          Run portfolio backtests with periodic rebalancing
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="tickers">Tickers</Label>
              <Input
                id="tickers"
                value={tickers}
                onChange={(e) => setTickers(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="weights">Weights (matching order)</Label>
              <Input
                id="weights"
                value={weightsStr}
                onChange={(e) => setWeightsStr(e.target.value)}
                placeholder="0.4,0.3,0.3"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="capital">Initial Capital</Label>
              <Input
                id="capital"
                type="number"
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
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
              <Label>Rebalance Frequency</Label>
              <Select value={rebalanceFreq} onValueChange={(v) => setRebalanceFreq(v as BacktestRequest["rebalance_freq"])}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-2 lg:col-span-3">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Running..." : "Run Backtest"}
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

      {mutation.data && <BacktestResults data={mutation.data} />}
    </div>
  );
}

function BacktestResults({ data }: { data: BacktestResponse }) {
  const dates = data.equity_curve.map((p) => p.date);
  const values = data.equity_curve.map((p) => p.value);
  const m = data.metrics;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Equity Curve</CardTitle>
        </CardHeader>
        <CardContent>
          <Plot
            data={[
              {
                x: dates,
                y: values,
                type: "scatter",
                mode: "lines",
                name: "Portfolio Value",
                line: { color: "#2563eb" },
              },
            ]}
            layout={{
              width: 900,
              height: 400,
              xaxis: { title: { text: "Date" } },
              yaxis: { title: { text: "Portfolio Value ($)" }, tickformat: ",.0f" },
              margin: { l: 80, r: 40, t: 20, b: 60 },
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Performance Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead className="text-right">Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell>Total Return</TableCell>
                <TableCell className="text-right">{(m.total_return * 100).toFixed(2)}%</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>CAGR</TableCell>
                <TableCell className="text-right">{(m.cagr * 100).toFixed(2)}%</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Sharpe Ratio</TableCell>
                <TableCell className="text-right">{m.sharpe.toFixed(4)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Max Drawdown</TableCell>
                <TableCell className="text-right">{(m.max_drawdown * 100).toFixed(2)}%</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Annualized Volatility</TableCell>
                <TableCell className="text-right">{(m.volatility * 100).toFixed(2)}%</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
