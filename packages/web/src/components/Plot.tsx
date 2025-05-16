// react-plotly.js is CJS — handle default export interop
import PlotlyModule from "react-plotly.js";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Plot = (PlotlyModule as any).default ?? PlotlyModule;
export default Plot;
