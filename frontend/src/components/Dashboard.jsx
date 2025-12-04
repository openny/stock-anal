// src/components/Dashboard.jsx
import React, { useState, useEffect } from "react";
import { startAnalysis, getStatus } from "../api";
import RadarChartViz from "./RadarChart";
import StockDetail from "./StockDetail";

const Dashboard = () => {
  const [topN, setTopN] = useState(5);
  const [status, setStatus] = useState("IDLE");
  const [progress, setProgress] = useState(0);
  const [stocks, setStocks] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);

  useEffect(() => {
    let interval;
    if (status === "RUNNING") {
      interval = setInterval(async () => {
        try {
          const data = await getStatus();
          setStatus(data.status);
          setProgress(data.progress);

          if (data.status === "COMPLETED" && Array.isArray(data.top_stocks)) {
            setStocks(data.top_stocks);
            if (data.top_stocks.length > 0) {
              setSelectedStock(data.top_stocks[0]);
            }
          }
        } catch (e) {
          console.error(e);
          setStatus("IDLE");
          setProgress(0);
        }
      }, 2000);
    }
    return () => interval && clearInterval(interval);
  }, [status]);

  const handleRun = async () => {
    try {
      const n = Number(topN) || 0;
      await startAnalysis(n);
      setStatus("RUNNING");
      setProgress(0);
      setStocks([]);
      setSelectedStock(null);
    } catch (e) {
      console.error(e);
      alert("분석 시작 중 오류가 발생했습니다.");
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      {/* 헤더 */}
      <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-blue-400">
            📊 Stock Radar Dashboard
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Macro · Fundamental · Quant · Timing · AI Forecast
          </p>
        </div>

        <div className="flex items-end gap-4">
          <div className="flex flex-col">
            <label className="text-xs text-gray-400 mb-1">
              Top N Candidates
            </label>
            <input
              type="number"
              min={1}
              max={100}
              value={topN}
              onChange={(e) => {
                const v = Number(e.target.value);
                setTopN(isNaN(v) ? "" : v);
              }}
              className="bg-gray-900 border border-gray-700 rounded px-3 py-1 w-24 text-center text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={handleRun}
            disabled={status === "RUNNING"}
            className={`px-6 py-2 rounded-lg text-sm font-semibold transition-all duration-200
              ${
                status === "RUNNING"
                  ? "bg-gray-700 text-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-500 text-white"
              }`}
          >
            {status === "RUNNING"
              ? `Analyzing... ${progress}%`
              : "Start Analysis"}
          </button>
        </div>
      </header>

      {/* 진행 바 */}
      {status === "RUNNING" && (
        <div className="w-full bg-gray-800 rounded-full h-2 mb-6 overflow-hidden">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* 본문 레이아웃 */}
      <div className="grid grid-cols-12 gap-6">
        {/* 왼쪽: 후보 리스트 */}
        <aside className="col-span-12 md:col-span-4 bg-gray-900 border border-gray-800 rounded-xl p-4 h-[70vh] overflow-y-auto">
          <h2 className="text-lg font-semibold mb-4">Top Candidates</h2>

          {stocks.length === 0 && status !== "RUNNING" && (
            <p className="text-gray-500 text-sm mt-10 text-center">
              Run analysis to see results
            </p>
          )}

          {stocks.map((stock) => {
            const active = selectedStock?.ticker === stock.ticker;
            const price =
              typeof stock.current_price === "number"
                ? stock.current_price.toFixed(2)
                : "-";

            return (
              <div
                key={stock.ticker}
                onClick={() => setSelectedStock(stock)}
                className={`p-4 mb-3 rounded-xl cursor-pointer border transition-all duration-150
                  ${
                    active
                      ? "border-blue-500 bg-gray-800"
                      : "border-gray-700 hover:bg-gray-800"
                  }`}
              >
                <div className="flex justify-between items-center">
                  <span className="text-xl font-bold">{stock.ticker}</span>
                  <span className="text-green-400 font-mono">${price}</span>
                </div>
                <p className="text-sm text-gray-400">
                  {stock.company_name}
                </p>
                <div className="mt-2 flex justify-between text-xs">
                  <span className="bg-blue-900 text-blue-200 px-2 py-1 rounded">
                    Score: {stock.fusion_score ?? "-"}
                  </span>
                  <span className="text-gray-300">{stock.sector}</span>
                </div>
              </div>
            );
          })}
        </aside>

        {/* 오른쪽: 상세 + 레이더 */}
        <section className="col-span-12 md:col-span-8 flex flex-col gap-6">
          {selectedStock ? (
            <>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 h-[360px]">
                <h3 className="text-lg font-semibold mb-3">
                  100-Day AI Price Forecast
                </h3>
                <StockDetail ticker={selectedStock.ticker} />
              </div>

              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 h-[320px]">
                <h3 className="text-lg font-semibold mb-3">
                  4D Score Profile
                </h3>
                <RadarChartViz data={selectedStock} />
              </div>
            </>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col items-center justify-center text-gray-500 h-[70vh] text-center">
              <p className="text-xl mb-2">📡 Select a stock to view details</p>
              <p className="text-sm">
                Choose one from the left panel to view analysis
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default Dashboard;