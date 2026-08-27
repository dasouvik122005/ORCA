import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import type { HistoricalReport } from '../types';

interface HistoricalDashboardProps {
  historicalReport: HistoricalReport;
}

export function HistoricalDashboard({ historicalReport }: HistoricalDashboardProps) {
  const data = historicalReport.trend_data.map(d => ({
    name: d.year.toString(),
    SST: d.sst_c,
    Catch: d.catch_index
  }));

  return (
    <div className="h-full p-4 flex gap-6 animate-fade-in text-slate-200">
      {/* Summary Section */}
      <div className="flex-1 flex flex-col max-w-[30%] min-w-[250px]">
        <h3 className="text-lg font-bold text-ocean-100 mb-2">Historical Analysis</h3>
        <p className="text-sm text-ocean-300 mb-4 flex-1 overflow-y-auto custom-scrollbar pr-2 leading-relaxed">
          {historicalReport.historical_analysis_summary}
        </p>
        {historicalReport.sst_trend_c != null && (
          <div className="bg-ocean-800/40 rounded-xl px-4 py-3 border border-ocean-600/20">
            <p className="text-xs text-ocean-400 mb-1">10-Year SST Trend</p>
            <p className="text-2xl font-bold font-mono text-[#e74c3c]">
              +{historicalReport.sst_trend_c}°C
            </p>
          </div>
        )}
      </div>

      {/* Chart Section */}
      <div className="flex-1 min-w-[400px]">
        <p className="text-xs text-ocean-400 font-medium mb-2">Productivity vs Sea Surface Temperature (Decadal)</p>
        <ResponsiveContainer width="100%" height="90%">
          <ComposedChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#252d55" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="left" orientation="left" tick={{ fill: '#2ecc71', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} tick={{ fill: '#e74c3c', fontSize: 10 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f1535', border: '1px solid #4a5a8a', borderRadius: '8px', fontSize: '12px' }}
              itemStyle={{ color: '#e2e8f0' }}
            />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
            <Bar yAxisId="left" dataKey="Catch" fill="#2ecc71" name="Relative Fish Catch (Index)" radius={[4, 4, 0, 0]} barSize={20} />
            <Line yAxisId="right" type="monotone" dataKey="SST" stroke="#e74c3c" strokeWidth={3} name="Sea Surface Temp (°C)" dot={{ r: 4, fill: '#e74c3c', strokeWidth: 2, stroke: '#0f1535' }} activeDot={{ r: 6 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
