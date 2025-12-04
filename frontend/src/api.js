// src/api.js
const BASE_URL = "http://localhost:8000"; // 백엔드 주소

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error: ${res.status} ${text}`);
  }

  return res.json();
}

// 분석 시작
export async function startAnalysis(topN = 5) {
  return request(`/api/analyze?top_n=${topN}`, {
    method: "POST",
  });
}

// 상태 조회
export async function getStatus() {
  return request(`/api/status`);
}

// 특정 종목 예측
export async function getForecast(ticker) {
  if (!ticker) throw new Error("ticker is required");
  return request(`/api/forecast/${encodeURIComponent(ticker)}`);
}

export async function analyzeSingle(ticker) {
  const res = await fetch(`${BASE_URL}/api/analyze_single/${ticker}`);
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "Single ticker analysis failed");
  }
  return res.json();
}