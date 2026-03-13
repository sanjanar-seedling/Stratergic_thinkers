import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { api } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';

interface Pattern {
  id: string;
  pattern_type: string;
  name: string;
  description: string;
  confidence: number;
  frequency: number;
  first_detected: string;
  last_seen: string;
  metadata: any;
}

interface TimeDrift {
  category: string;
  stated_priority: number;
  actual_time: number;
  drift_percentage: number;
  severity: string;
  recommendation: string;
}

interface JudgmentMetrics {
  total_decisions: number;
  decisions_with_outcomes: number;
  accuracy_rate: number;
  average_confidence: number;
  calibration_score: number;
  improvement_trend: string;
}

const InsightsPage: React.FC = () => {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [biases, setBiases] = useState<Pattern[]>([]);
  const [timeDrift, setTimeDrift] = useState<TimeDrift[]>([]);
  const [judgmentMetrics, setJudgmentMetrics] = useState<JudgmentMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInsights();
  }, []);

  const fetchInsights = async () => {
    setLoading(true);
    try {
      const [patternsRes, biasesRes, driftRes, metricsRes] = await Promise.all([
        api.get('/insights/patterns'),
        api.get('/insights/biases'),
        api.get('/insights/drift'),
        api.get('/judgment/metrics'),
      ]);

      setPatterns(patternsRes.data);
      setBiases(biasesRes.data);
      setTimeDrift(driftRes.data);
      setJudgmentMetrics(metricsRes.data);
    } catch (error) {
      console.error('Failed to fetch insights:', error);
    } finally {
      setLoading(false);
    }
  };

  const severityColors = {
    high: 'bg-red-100 text-red-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
  };

  const trendColors = {
    improving: 'text-green-600',
    stable: 'text-blue-600',
    declining: 'text-red-600',
    insufficient_data: 'text-gray-600',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Insights Dashboard</h1>
        <p className="text-gray-600">Your thinking patterns, biases, and judgment quality over time.</p>
      </div>

      {/* Judgment Quality Metrics */}
      {judgmentMetrics && (
        <Card>
          <CardHeader>
            <CardTitle>Judgment Quality</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div>
                <p className="text-sm text-gray-600 mb-1">Accuracy Rate</p>
                <p className="text-3xl font-bold text-gray-900">
                  {(judgmentMetrics.accuracy_rate * 100).toFixed(0)}%
                </p>
                <Progress value={judgmentMetrics.accuracy_rate * 100} className="mt-2" />
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Calibration Score</p>
                <p className="text-3xl font-bold text-gray-900">
                  {(judgmentMetrics.calibration_score * 100).toFixed(0)}%
                </p>
                <Progress value={judgmentMetrics.calibration_score * 100} className="mt-2" />
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Avg Confidence</p>
                <p className="text-3xl font-bold text-gray-900">
                  {(judgmentMetrics.average_confidence * 100).toFixed(0)}%
                </p>
                <Progress value={judgmentMetrics.average_confidence * 100} className="mt-2" />
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Trend</p>
                <p
                  className={`text-2xl font-bold capitalize ${
                    trendColors[judgmentMetrics.improvement_trend as keyof typeof trendColors]
                  }`}
                >
                  {judgmentMetrics.improvement_trend.replace('_', ' ')}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {judgmentMetrics.decisions_with_outcomes} / {judgmentMetrics.total_decisions} tracked
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cognitive Biases */}
      {biases.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Detected Cognitive Biases</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {biases.map((bias) => (
                <div key={bias.id} className="border-l-4 border-red-500 pl-4 py-2">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">{bias.name}</h3>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">Frequency: {bias.frequency}</Badge>
                      <Badge className="bg-red-100 text-red-800">
                        {(bias.confidence * 100).toFixed(0)}% confidence
                      </Badge>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">{bias.description}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    Last seen: {new Date(bias.last_seen).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Time Allocation Drift */}
      {timeDrift.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Time Allocation Drift</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {timeDrift.map((drift, idx) => (
                <div key={idx} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-900 capitalize">{drift.category}</h3>
                    <Badge className={severityColors[drift.severity as keyof typeof severityColors]}>
                      {drift.severity} drift
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <p className="text-xs text-gray-600">Stated Priority</p>
                      <p className="text-lg font-semibold">{(drift.stated_priority * 100).toFixed(0)}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600">Actual Time</p>
                      <p className="text-lg font-semibold">{(drift.actual_time * 100).toFixed(0)}%</p>
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <p className="text-sm text-gray-700">{drift.recommendation}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Decision Patterns */}
      {patterns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Decision Patterns</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {patterns.map((pattern) => (
                <div key={pattern.id} className="border-l-4 border-blue-500 pl-4 py-2">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">{pattern.name}</h3>
                    <Badge variant="outline">{pattern.pattern_type.replace('_', ' ')}</Badge>
                  </div>
                  <p className="text-sm text-gray-600">{pattern.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span>Confidence: {(pattern.confidence * 100).toFixed(0)}%</span>
                    <span>Frequency: {pattern.frequency}</span>
                    <span>Since: {new Date(pattern.first_detected).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default InsightsPage;
