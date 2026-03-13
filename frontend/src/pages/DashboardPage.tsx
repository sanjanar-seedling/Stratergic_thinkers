import { useState, useEffect } from "react";
import { getDashboardStats, getBiasDetections, getGrowthTrajectory } from "@/services/api";
import { BarChart3, TrendingUp, Brain, Target, AlertTriangle } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
} from "recharts";

const radarData = [
  { subject: "Strategic Clarity", A: 85, B: 70 },
  { subject: "Bias Awareness", A: 72, B: 55 },
  { subject: "Decision Speed", A: 78, B: 82 },
  { subject: "Reflection Depth", A: 90, B: 60 },
  { subject: "Confidence Calibration", A: 68, B: 50 },
  { subject: "Alternative Mapping", A: 65, B: 45 },
];

export function DashboardPage() {
  const [stats, setStats] = useState({ total_decisions: 0, avg_accuracy: 0, biases_caught: 0, open_decisions: 0 });
  const [growthData, setGrowthData] = useState<{ month: string; confidence: number; accuracy: number; reflection_count: number }[]>([]);
  const [biasData, setBiasData] = useState<{ bias_type: string; count: number }[]>([]);

  useEffect(() => {
    getDashboardStats().then(r => setStats(r.data)).catch(console.error);
    getGrowthTrajectory().then(r => setGrowthData(r.data)).catch(console.error);
    getBiasDetections().then(r => {
      const counts: Record<string, number> = {};
      for (const b of r.data) counts[b.bias_type] = (counts[b.bias_type] || 0) + 1;
      setBiasData(Object.entries(counts).map(([bias_type, count]) => ({ bias_type, count })));
    }).catch(console.error);
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-primary" />
          Judgment Scorecard
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Track the ROI of your reflection practice. Watch your judgment quality
          improve over time.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { title: "Decisions Tracked", value: String(stats.total_decisions), change: "logged decisions", icon: Target, color: "text-primary" },
          { title: "Avg Accuracy", value: `${stats.avg_accuracy}%`, change: "confidence vs outcome", icon: TrendingUp, color: "text-emerald-500" },
          { title: "Biases Caught", value: String(stats.biases_caught), change: "detected patterns", icon: Brain, color: "text-violet-500" },
          { title: "Open Decisions", value: String(stats.open_decisions), change: "pending outcomes", icon: AlertTriangle, color: "text-amber-500" },
        ].map((kpi, i) => (
          <Card key={i} className="glass-card">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {kpi.title}
                </span>
              </div>
              <p className="text-2xl font-bold">{kpi.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {kpi.change}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-2 gap-4">
        {/* Growth Trajectory */}
        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Growth Trajectory</CardTitle>
            <CardDescription>
              Confidence calibration vs. actual accuracy over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={growthData}>
                <defs>
                  <linearGradient
                    id="colorAccuracy"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="5%"
                      stopColor="hsl(142, 71%, 45%)"
                      stopOpacity={0.3}
                    />
                    <stop
                      offset="95%"
                      stopColor="hsl(142, 71%, 45%)"
                      stopOpacity={0}
                    />
                  </linearGradient>
                  <linearGradient
                    id="colorConfidence"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="5%"
                      stopColor="hsl(173, 58%, 39%)"
                      stopOpacity={0.3}
                    />
                    <stop
                      offset="95%"
                      stopColor="hsl(173, 58%, 39%)"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(240, 3.7%, 15.9%)"
                />
                <XAxis
                  dataKey="month"
                  stroke="hsl(240, 5%, 64.9%)"
                  fontSize={12}
                />
                <YAxis stroke="hsl(240, 5%, 64.9%)" fontSize={12} />
                <RechartsTooltip
                  contentStyle={{
                    background: "hsl(240, 10%, 5.5%)",
                    border: "1px solid hsl(240, 3.7%, 15.9%)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="accuracy"
                  stroke="hsl(142, 71%, 45%)"
                  fillOpacity={1}
                  fill="url(#colorAccuracy)"
                  strokeWidth={2}
                  name="Accuracy"
                />
                <Area
                  type="monotone"
                  dataKey="confidence"
                  stroke="hsl(173, 58%, 39%)"
                  fillOpacity={1}
                  fill="url(#colorConfidence)"
                  strokeWidth={2}
                  name="Confidence"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Cognitive Bias Frequency */}
        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              Cognitive Bias Frequency
            </CardTitle>
            <CardDescription>
              Detected biases over the last 30 days
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={biasData} layout="vertical">
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(240, 3.7%, 15.9%)"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  stroke="hsl(240, 5%, 64.9%)"
                  fontSize={12}
                />
                <YAxis
                  dataKey="bias_type"
                  type="category"
                  stroke="hsl(240, 5%, 64.9%)"
                  fontSize={11}
                  width={100}
                />
                <RechartsTooltip
                  contentStyle={{
                    background: "hsl(240, 10%, 5.5%)",
                    border: "1px solid hsl(240, 3.7%, 15.9%)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar
                  dataKey="count"
                  fill="hsl(142, 71%, 45%)"
                  radius={[0, 4, 4, 0]}
                  name="Detections"
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-3 gap-4">
        {/* Thinking Radar */}
        <Card className="glass-card col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Thinking Profile</CardTitle>
            <CardDescription>Current month vs. baseline</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="hsl(240, 3.7%, 15.9%)" />
                <PolarAngleAxis
                  dataKey="subject"
                  stroke="hsl(240, 5%, 64.9%)"
                  fontSize={9}
                />
                <PolarRadiusAxis
                  stroke="hsl(240, 3.7%, 15.9%)"
                  fontSize={10}
                />
                <Radar
                  name="Current"
                  dataKey="A"
                  stroke="hsl(142, 71%, 45%)"
                  fill="hsl(142, 71%, 45%)"
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
                <Radar
                  name="Baseline"
                  dataKey="B"
                  stroke="hsl(240, 5%, 64.9%)"
                  fill="hsl(240, 5%, 64.9%)"
                  fillOpacity={0.05}
                  strokeWidth={1}
                  strokeDasharray="4 4"
                />
                <Legend
                  wrapperStyle={{ fontSize: "11px" }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Recent Insights */}
        <Card className="glass-card col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              Recent Pattern Insights
            </CardTitle>
            <CardDescription>
              AI-detected patterns from your latest reflections
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              {
                type: "Avoidance Detected",
                icon: "🔴",
                text: "You've mentioned 'co-founder equity discussion' in 4 entries over 2 weeks without taking action. This matches avoidance behavior patterns.",
                action: "Address this",
              },
              {
                type: "Confirmation Bias",
                icon: "🟡",
                text: "Your mid-market pivot research cites 5 supporting data points but zero counterarguments. Consider seeking disconfirming evidence.",
                action: "Start sparring",
              },
              {
                type: "Growth Signal",
                icon: "🟢",
                text: "Your decision accuracy has improved 13% since onboarding. You're spending 2.3x more time mapping alternatives before committing.",
                action: "View details",
              },
              {
                type: "Inflection Point",
                icon: "🔵",
                text: "Q1 reflection patterns show a fundamental shift from execution-first to strategy-first thinking. This correlates with better Q2 outcomes.",
                action: "Deep dive",
              },
            ].map((insight, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-lg bg-muted/20 p-3 transition-smooth hover:bg-muted/30"
              >
                <span className="text-lg">{insight.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-0.5">
                    {insight.type}
                  </p>
                  <p className="text-sm leading-relaxed">{insight.text}</p>
                </div>
                <button className="text-xs text-primary hover:underline whitespace-nowrap mt-1">
                  {insight.action}
                </button>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Reflection Intensity */}
      <Card className="glass-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            Weekly Reflection Intensity
          </CardTitle>
          <CardDescription>
            Entries per week — consistency is more valuable than volume
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-1 h-16">
            {[3, 5, 2, 7, 4, 6, 8, 3, 5, 9, 4, 7, 6, 5, 8, 4, 6, 7, 5, 8].map(
              (val, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-sm bg-primary/20 transition-smooth hover:bg-primary/40"
                  style={{ height: `${(val / 9) * 100}%` }}
                  title={`Week ${i + 1}: ${val} entries`}
                />
              )
            )}
          </div>
          <div className="flex justify-between mt-2 text-[10px] text-muted-foreground">
            <span>20 weeks ago</span>
            <span>This week</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
