import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend,
} from 'recharts';

type RiskDistributionEntry = {
  name: string;
  value: number;
  color: string;
};

type PollutantDistributionEntry = {
  name: string;
  count: number;
  fill: string;
};

type PortfolioChartsProps = {
  riskData: RiskDistributionEntry[];
  pollutantData: PollutantDistributionEntry[];
  t: (key: string) => string;
};

export function PortfolioCharts({ riskData, pollutantData, t }: PortfolioChartsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{t('portfolio.risk_distribution')}</h2>
        {riskData.some((d) => d.value > 0) ? (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={riskData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={4}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
              >
                {riskData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500 dark:text-slate-400 text-sm">
            {t('portfolio.empty')}
          </div>
        )}
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {t('portfolio.pollutant_prevalence')}
        </h2>
        {pollutantData.some((d) => d.count > 0) ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={pollutantData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {pollutantData.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500 dark:text-slate-400 text-sm">
            {t('portfolio.empty')}
          </div>
        )}
      </div>
    </div>
  );
}
