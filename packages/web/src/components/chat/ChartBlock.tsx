import type { ChartBlock as ChartBlockType } from "@/api/chat-types";
import type {
  PricesData,
  CovarianceData,
  FrontierData,
  RollingMetricsData,
} from "@/api/chat-types";
import PriceChart from "./charts/PriceChart";
import WeightBar from "./charts/WeightBar";
import EquityCurve from "./charts/EquityCurve";
import CovarianceHeatmap from "./charts/CovarianceHeatmap";
import EfficientFrontier from "./charts/EfficientFrontier";
import RollingChart from "./charts/RollingChart";

interface ChartBlockProps {
  block: ChartBlockType;
}

export default function ChartBlock({ block }: ChartBlockProps) {
  switch (block.chartType) {
    case "price":
      return <PriceChart data={block.data as PricesData} />;

    case "weight_bar":
      return <WeightBar data={block.data as Record<string, number>} />;

    case "equity_curve":
      return (
        <EquityCurve
          data={block.data as { date: string; value: number }[]}
        />
      );

    case "covariance_heatmap":
      return <CovarianceHeatmap data={block.data as CovarianceData} />;

    case "efficient_frontier":
      return <EfficientFrontier data={block.data as FrontierData} />;

    case "rolling":
      return <RollingChart data={block.data as RollingMetricsData} />;

    default:
      return null;
  }
}
