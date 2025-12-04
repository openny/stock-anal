import React, { useEffect, useState } from "react";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { getForecast } from "../api";

const StockDetail = ({ ticker }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // 티커 없으면 초기화
    if (!ticker) {
      setData(null);
      setError(null);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await getForecast(ticker);

        // 방어 코드: 필드 없을 때
        if (
          !res ||
          !Array.isArray(res.historical) ||
          !Array.isArray(res.forecast) ||
          !Array.isArray(res.dates) ||
          !Array.isArray(res.lower_bound) ||
          !Array.isArray(res.upper_bound)
        ) {
          throw new Error("Invalid forecast response format");
        }

        // 1) 과거 데이터
        const histData = res.historical.map((val, idx) => ({
          date: `Hist-${idx}`,
          price: val,
          type: "Historical",
        }));

        const lastPrice = res.historical[res.historical.length - 1];

        // 2) 예측 데이터
        const forecastData = res.forecast.map((val, idx) => ({
          date: res.dates[idx],
          forecast: val,
          lower: res.lower_bound[idx],
          upper: res.upper_bound[idx],
          type: "Forecast",
        }));

        // 3) 히스토리 마지막 포인트를 예측 시작점과 브릿지로 연결
        const bridgePoint = {
          date: res.dates[0] ?? "Forecast-0",
          price: lastPrice,
          forecast: lastPrice,
          lower: lastPrice,
          upper: lastPrice,
          type: "Bridge",
        };

        setData([...histData, bridgePoint, ...forecastData]);
      } catch (e) {
        console.error(e);
        setError(e.message ?? "Failed to load forecast");
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [ticker]);

  if (!ticker) {
    return (
      <div className="flex justify-center items-center h-full text-gray-400 text-sm">
        종목을 선택하면 AI 예측 차트가 표시됩니다.
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="flex justify-center items-center h-full text-gray-400 text-sm">
        Loading AI Model...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-full text-red-400 text-sm">
        {error}
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data}>
        <defs>
          <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#82ca9d" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid stroke="#374151" strokeDasharray="3 3" />
        <XAxis dataKey="date" hide />
        <YAxis domain={["auto", "auto"]} stroke="#9CA3AF" />

        <Tooltip
          contentStyle={{
            backgroundColor: "#1F2937",
            border: "1px solid #4B5563",
            borderRadius: "0.5rem",
            color: "#E5E7EB",
          }}
          formatter={(value, name) => {
            if (value == null || isNaN(Number(value))) {
              return ["-", name];
            }
            return [`$${Number(value).toFixed(2)}`, name];
          }}
        />

        <Legend />

        {/* 실제 과거 가격 라인 */}
        <Line
          type="monotone"
          dataKey="price"
          stroke="#3B82F6"
          strokeWidth={2}
          dot={false}
          name="Historical"
        />

        {/* 예측 라인 */}
        <Line
          type="monotone"
          dataKey="forecast"
          stroke="#10B981"
          strokeWidth={2}
          dot={false}
          strokeDasharray="5 5"
          name="Forecast"
        />

        {/* 예측 구간(상/하한 밴드) */}
        <Area
          type="monotone"
          dataKey="upper"
          stroke="none"
          fill="url(#colorForecast)"
          name="Upper Bound"
        />
        <Area
          type="monotone"
          dataKey="lower"
          stroke="none"
          fill="url(#colorForecast)"
          name="Lower Bound"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
};

export default StockDetail;