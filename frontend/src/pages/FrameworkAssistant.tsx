import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { api } from '../services/api';

interface FrameworkRecommendation {
  framework_id: string;
  name: string;
  description: string;
  relevance_score: number;
  reasoning: string;
  when_to_use: string;
  example: string;
}

const FrameworkAssistant: React.FC = () => {
  const [context, setContext] = useState('');
  const [recommendations, setRecommendations] = useState<FrameworkRecommendation[]>([]);
  const [loading, setLoading] = useState(false);

  const handleGetRecommendations = async () => {
    if (!context.trim()) return;

    setLoading(true);
    try {
      const response = await api.post('/frameworks/recommend', null, {
        params: { context, top_k: 3 },
      });
      setRecommendations(response.data);
    } catch (error) {
      console.error('Failed to get recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Framework Assistant</h1>
        <p className="text-gray-600">
          Get strategic framework recommendations for your current decision or situation.
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Describe Your Situation</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="I'm trying to decide whether to pivot our product strategy. We've been working on this for 6 months..."
            rows={6}
            className="w-full mb-4"
          />
          <Button
            onClick={handleGetRecommendations}
            disabled={!context.trim() || loading}
            className="w-full"
          >
            {loading ? 'Finding Frameworks...' : 'Get Framework Recommendations'}
          </Button>
        </CardContent>
      </Card>

      {recommendations.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">Recommended Frameworks</h2>
          {recommendations.map((rec, idx) => (
            <Card key={rec.framework_id} className="border-l-4 border-blue-500">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">#{idx + 1}</span>
                      <CardTitle>{rec.name}</CardTitle>
                    </div>
                    <Badge variant="outline">
                      {(rec.relevance_score * 100).toFixed(0)}% relevant
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Why This Framework?</h4>
                  <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded">{rec.reasoning}</p>
                </div>

                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Description</h4>
                  <p className="text-sm text-gray-600">{rec.description}</p>
                </div>

                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">When to Use</h4>
                  <p className="text-sm text-gray-600">{rec.when_to_use}</p>
                </div>

                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Example</h4>
                  <p className="text-sm text-gray-600 italic">"{rec.example}"</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default FrameworkAssistant;
