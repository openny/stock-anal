import React from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const RadarChartViz = ({ data }) => {
  // 아직 종목이 선택되지 않았을 때
  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        4D 점수를 보려면 종목을 선택하세요.
      </div>
    );
  }

  // 🔹 FusionEngine이 내려주는 필드와 매핑
  const metrics = [
    { key: "d1_macro", label: "Macro" },
    { key: "d2_fundamental", label: "Fundamental" },
    { key: "d3_quant", label: "Quant" },
    { key: "d4_timing", label: "Timing" },
  ];

  // Recharts용 데이터 형식으로 변환
  const chartData = metrics.map((m) => ({
    subject: m.label,
    score: Number(data[m.key] ?? 0), // 없는 값은 0
  }));

  // 점수 범위 (0~100 가정)
  const maxScore =
    Math.max(...chartData.map((d) => (isNaN(d.score) ? 0 : d.score)), 100);

  const allZero = chartData.every((d) => !d.score);

  if (allZero) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        이 종목의 4D 점수가 아직 계산되지 않았습니다.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chartData}>
        <PolarGrid stroke="#374151" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: "#9CA3AF", fontSize: 12 }}
        />
        <PolarRadiusAxis
          angle={30}
          domain={[0, maxScore]}
          tick={false}
          axisLine={false}
        />
        <Radar
          name={data.ticker}
          dataKey="score"       // ⭐ chartData의 필드명과 일치
          stroke="#3B82F6"
          strokeWidth={2}
          fill="#3B82F6"
          fillOpacity={0.35}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#111827",
            border: "1px solid #4B5563",
            borderRadius: "0.5rem",
            color: "#E5E7EB",
          }}
          formatter={(value) => [`${Number(value).toFixed(1)}`, "Score"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
};

export default RadarChartViz;