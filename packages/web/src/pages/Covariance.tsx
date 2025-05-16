import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Plot from "@/components/Plot";
import { computeCovariance } from "@/api/client";
import type { CovarianceRequest, CovarianceResponse } from "@/api/types";
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

export default function Covariance() {
  const [tickers, setTickers] = useState("AAPL,MSFT,GOOGL,AMZN");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [method, setMethod] = useState<CovarianceRequest["method"]>("ledoit_wolf");

  const mutation = useMutation({
    mutationFn: computeCovariance,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      tickers: tickers.split(",").map((t) => t.trim()),
      start_date: startDate,
      end_date: endDate,
      method,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Covariance Matrix</h1>
        <p className="text-muted-foreground">
          Estimate asset return covariance matrices
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="tickers">Tickers (comma-separated)</Label>
              <Input
                id="tickers"
                value={tickers}
                onChange={(e) => setTickers(e.target.value)}
                placeholder="AAPL,MSFT,GOOGL"
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
              <Label>Method</Label>
              <Select value={method} onValueChange={(v) => setMethod(v as CovarianceRequest["method"])}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ledoit_wolf">Ledoit-Wolf</SelectItem>
                  <SelectItem value="sample">Sample</SelectItem>
                  <SelectItem value="shrunk">Shrunk</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-2 lg:col-span-4">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Computing..." : "Compute"}
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

      {mutation.data && <CovarianceHeatmap data={mutation.data} />}
    </div>
  );
}

function CovarianceHeatmap({ data }: { data: CovarianceResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Covariance Matrix ({data.method})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Plot
          data={[
            {
              z: data.matrix,
              x: data.tickers,
              y: data.tickers,
              type: "heatmap",
              colorscale: "RdBu",
              reversescale: true,
              zmin: -Math.max(...data.matrix.flat().map(Math.abs)),
              zmax: Math.max(...data.matrix.flat().map(Math.abs)),
            },
          ]}
          layout={{
            width: 700,
            height: 600,
            title: { text: "Annualized Covariance Matrix" },
            xaxis: { side: "bottom" },
            yaxis: { autorange: "reversed" },
            margin: { l: 80, r: 40, t: 60, b: 80 },
          }}
        />
      </CardContent>
    </Card>
  );
}
