import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import type { OceanReport, RiskScore, WeatherReport } from '../types';

interface RiskDashboardProps {
  riskScore: RiskScore | null;
  weatherReport: WeatherReport | null;
  oceanReport: OceanReport | null;
}

function RiskGauge({ score, color, label, emoji }: { score: number; color: string; label: string; emoji: string }) {
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-[120px] h-[120px]">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#1a2144" strokeWidth="8" />
          <circle
            cx="50" cy="50" r="45" fill="none"
            stroke={color}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1.5s ease-out', animation: 'gauge-fill 1.5s ease-out' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-black font-mono" style={{ color }}>{score}</span>
          <span className="text-[10px] text-ocean-400">/100</span>
        </div>
      </div>
      <div className="mt-2 text-center">
        <span className="text-sm font-semibold" style={{ color }}>{emoji} {label}</span>
      </div>
    </div>
  );
}

function DataCard({ icon, label, value, unit, color }: { icon: string; label: string; value: string | number | null | undefined; unit?: string; color?: string }) {
  if (value == null) return null;
  return (
    <div className="bg-ocean-800/40 rounded-xl px-3 py-2 border border-ocean-600/20">
      <div className="text-xs text-ocean-400 mb-0.5">{icon} {label}</div>
      <div className="text-lg font-bold font-mono" style={{ color: color || '#e2e8f0' }}>
        {value}<span className="text-xs font-normal text-ocean-400 ml-1">{unit}</span>
      </div>
    </div>
  );
}

function getBarColor(score: number): string {
  if (score >= 80) return '#e74c3c';
  if (score >= 60) return '#e67e22';
  if (score >= 30) return '#f1c40f';
  return '#2ecc71';
}

export function RiskDashboard({ riskScore, weatherReport, oceanReport }: RiskDashboardProps) {
  if (!riskScore && !weatherReport && !oceanReport) {
    return (
      <div className="h-full flex items-center justify-center text-ocean-500 text-sm">
        <div className="text-center">
          <span className="text-4xl block mb-2">🌊</span>
          <p>Ask ORCA a question to see marine intelligence here</p>
        </div>
      </div>
    );
  }

  const chartData = riskScore?.factor_scores.map(f => ({
    name: f.factor.replace(' ', '\n'),
    score: f.score,
    fill: getBarColor(f.score),
  })) || [];

  return (
    <div className="h-full p-3 flex gap-3 animate-fade-in">
      {/* Risk Gauge */}
      {riskScore && (
        <div className="flex flex-col items-center justify-center min-w-[150px]">
          <RiskGauge
            score={riskScore.final_score}
            color={riskScore.risk_color}
            label={riskScore.risk_label}
            emoji={riskScore.risk_emoji}
          />
          <p className="text-[10px] text-ocean-500 mt-1 text-center max-w-[140px]">
            Primary: {riskScore.primary_hazard}
          </p>
        </div>
      )}

      {/* Factor Breakdown Chart */}
      {chartData.length > 0 && (
        <div className="flex-1 min-w-[200px]">
          <p className="text-xs text-ocean-400 font-medium mb-1">Risk Factor Breakdown</p>
          <ResponsiveContainer width="100%" height={170}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 10, top: 0, bottom: 0 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#4a5a8a', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 9 }} width={80} axisLine={false} tickLine={false} />
              <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={14}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Live Data Cards */}
      <div className="grid grid-cols-2 gap-2 content-start min-w-[220px]">
        <DataCard icon="🌊" label="Waves" value={oceanReport?.wave_height_m} unit="m"
          color={oceanReport?.wave_height_m && oceanReport.wave_height_m > 2.5 ? '#e74c3c' : '#2ecc71'} />
        <DataCard icon="💨" label="Wind" value={weatherReport?.wind_speed_kmh} unit="km/h"
          color={weatherReport?.wind_speed_kmh && weatherReport.wind_speed_kmh > 35 ? '#e74c3c' : '#2ecc71'} />
        <DataCard icon="🌧" label="Rain" value={weatherReport?.rain_probability_pct != null ? `${weatherReport.rain_probability_pct}` : null} unit="%"
          color={weatherReport?.rain_probability_pct && weatherReport.rain_probability_pct > 70 ? '#e67e22' : '#3498db'} />
        <DataCard icon="⚡" label="Lightning" value={weatherReport?.lightning_risk}
          color={weatherReport?.lightning_risk === 'HIGH' ? '#e74c3c' : weatherReport?.lightning_risk === 'MODERATE' ? '#e67e22' : '#2ecc71'} />
        <DataCard icon="🌡" label="SST" value={oceanReport?.sst_c} unit="°C" color="#3498db" />
        <DataCard icon="🌊" label="Sea State" value={oceanReport?.sea_state_description} />
      </div>

      {/* Vessel Recommendation */}
      {riskScore?.vessel_recommendation && (
        <div className="min-w-[200px] max-w-[220px] flex flex-col justify-center">
          <p className="text-xs text-ocean-400 font-medium mb-2">Vessel Advisory</p>
          <div
            className="text-xs leading-relaxed p-3 rounded-xl border"
            style={{
              backgroundColor: riskScore.risk_color + '10',
              borderColor: riskScore.risk_color + '30',
              color: '#cbd5e1',
            }}
          >
            {riskScore.vessel_recommendation}
          </div>
        </div>
      )}
    </div>
  );
}
