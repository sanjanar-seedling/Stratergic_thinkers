import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { api } from '../services/api';

interface Intervention {
  id: string;
  trigger_type: string;
  prompt_type: string;
  question: string;
  context: string;
  priority: string;
  status: string;
  created_at: string;
  expires_at?: string;
}

const InterventionCard: React.FC<{ intervention: Intervention; onRespond: () => void }> = ({
  intervention,
  onRespond,
}) => {
  const [isResponding, setIsResponding] = useState(false);
  const [response, setResponse] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const priorityColors = {
    high: 'bg-red-100 text-red-800 border-red-300',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    low: 'bg-blue-100 text-blue-800 border-blue-300',
  };

  const promptTypeIcons = {
    clarifying: '🤔',
    challenging: '⚡',
    integrating: '🔗',
  };

  const handleRespond = async () => {
    if (!response.trim()) return;

    setIsSubmitting(true);
    try {
      await api.post(`/interventions/${intervention.id}/respond`, {
        response_text: response,
      });
      setResponse('');
      setIsResponding(false);
      onRespond();
    } catch (error) {
      console.error('Failed to respond:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDismiss = async () => {
    try {
      await api.post(`/interventions/${intervention.id}/dismiss`);
      onRespond();
    } catch (error) {
      console.error('Failed to dismiss:', error);
    }
  };

  return (
    <Card
      className={`mb-4 border-l-4 ${
        priorityColors[intervention.priority as keyof typeof priorityColors] || ''
      }`}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">
                {promptTypeIcons[intervention.prompt_type as keyof typeof promptTypeIcons] || '💭'}
              </span>
              <Badge variant="outline" className="capitalize">
                {intervention.prompt_type}
              </Badge>
              <Badge variant="secondary" className="capitalize">
                {intervention.trigger_type}
              </Badge>
            </div>
            <CardTitle className="text-lg font-semibold text-gray-900">
              {intervention.question}
            </CardTitle>
          </div>
          <Badge
            className={`ml-4 ${priorityColors[intervention.priority as keyof typeof priorityColors]}`}
          >
            {intervention.priority}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-600 mb-4">{intervention.context}</p>

        {!isResponding ? (
          <div className="flex gap-2">
            <Button onClick={() => setIsResponding(true)} className="flex-1">
              Reflect on This
            </Button>
            <Button onClick={handleDismiss} variant="outline">
              Dismiss
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <Textarea
              value={response}
              onChange={(e) => setResponse(e.target.value)}
              placeholder="Take a moment to reflect..."
              rows={4}
              className="w-full"
            />
            <div className="flex gap-2">
              <Button
                onClick={handleRespond}
                disabled={!response.trim() || isSubmitting}
                className="flex-1"
              >
                {isSubmitting ? 'Saving...' : 'Save Reflection'}
              </Button>
              <Button
                onClick={() => {
                  setIsResponding(false);
                  setResponse('');
                }}
                variant="outline"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {intervention.expires_at && (
          <p className="text-xs text-gray-500 mt-3">
            Expires: {new Date(intervention.expires_at).toLocaleDateString()}
          </p>
        )}
      </CardContent>
    </Card>
  );
};

const InterventionsPage: React.FC = () => {
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'sent'>('pending');

  const fetchInterventions = async () => {
    setLoading(true);
    try {
      const params = filter === 'all' ? {} : { status: filter };
      const response = await api.get('/interventions', { params });
      setInterventions(response.data);
    } catch (error) {
      console.error('Failed to fetch interventions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInterventions();
  }, [filter]);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Reflections</h1>
        <p className="text-gray-600">
          Strategic questions to improve your thinking and decision-making.
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6 border-b">
        {(['pending', 'sent', 'all'] as const).map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-2 font-medium capitalize transition-colors ${
              filter === status
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-600 mt-4">Loading reflections...</p>
        </div>
      ) : interventions.length === 0 ? (
        <Alert>
          <AlertDescription>
            No interventions at the moment. Keep journaling and the AI will surface insights when
            patterns emerge.
          </AlertDescription>
        </Alert>
      ) : (
        <div>
          {interventions.map((intervention) => (
            <InterventionCard
              key={intervention.id}
              intervention={intervention}
              onRespond={fetchInterventions}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default InterventionsPage;
