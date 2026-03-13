import { useState, useEffect } from "react";
import { createDecision, getDecisions, resolveDecision } from "@/services/api";
import {
  Target,
  Plus,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Swords,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";

interface Decision {
  id: string;
  title: string;
  rationale: string;
  expected_outcome: string;
  expected_outcome_date: string;
  confidence_score: number;
  alternatives: string[];
  status: "pending" | "resolved" | "revised";
  actual_outcome?: string;
  created_at: string;
}

export function DecisionsPage() {
  const [showForm, setShowForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [decisions, setDecisions] = useState<Decision[]>([]);

  // Resolve modal state
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [actualOutcome, setActualOutcome] = useState("");
  const [outcomeScore, setOutcomeScore] = useState(50);
  const [isResolving, setIsResolving] = useState(false);

  // Form State
  const [title, setTitle] = useState("");
  const [rationale, setRationale] = useState("");
  const [expectedOutcome, setExpectedOutcome] = useState("");
  const [outcomeDate, setOutcomeDate] = useState("");
  const [confidence, setConfidence] = useState(75);

  useEffect(() => {
    // Fetch initial decisions
    getDecisions().then((res) => setDecisions(res.data)).catch(console.error);
  }, []);

  const handleSubmit = async () => {
    if (!title || !rationale) return;
    setIsSubmitting(true);
    try {
      const res = await createDecision({
        title,
        rationale,
        expected_outcome: expectedOutcome,
        expected_outcome_date: outcomeDate,
        confidence_score: confidence / 100,
        alternatives: []
      });
      setDecisions(prev => [res.data, ...prev]);
      setShowForm(false);
      setTitle("");
      setRationale("");
      setExpectedOutcome("");
      setOutcomeDate("");
      setConfidence(75);
    } catch (error) {
      console.error("Failed to create decision:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResolve = async () => {
    if (!resolvingId || !actualOutcome) return;
    setIsResolving(true);
    try {
      const res = await resolveDecision(resolvingId, {
        actual_outcome: actualOutcome,
        outcome_score: outcomeScore / 100,
      });
      setDecisions(prev => prev.map(d => d.id === resolvingId ? res.data : d));
      setResolvingId(null);
      setActualOutcome("");
      setOutcomeScore(50);
    } catch (error) {
      console.error("Failed to resolve decision:", error);
    } finally {
      setIsResolving(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "resolved":
        return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case "revised":
        return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return "text-emerald-500";
    if (score >= 0.6) return "text-amber-500";
    return "text-red-400";
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Target className="h-6 w-6 text-primary" />
            Decision Log
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Track major decisions, calibrate confidence, and close the feedback
            loop.
          </p>
        </div>
        <Button
          id="new-decision-btn"
          onClick={() => setShowForm(!showForm)}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          Log Decision
        </Button>
      </div>

      {/* New Decision Form */}
      {showForm && (
        <Card className="glass-card animate-slide-in border-primary/20">
          <CardHeader>
            <CardTitle className="text-base">New Decision Record</CardTitle>
            <CardDescription>
              Document the decision, your reasoning, and expected outcome.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="decision-title">Decision</Label>
              <Input
                id="decision-title"
                placeholder="What decision did you make?"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="decision-rationale">Rationale</Label>
              <Textarea
                id="decision-rationale"
                placeholder="Why did you choose this path?"
                className="min-h-[80px]"
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="expected-outcome">Expected Outcome</Label>
                <Input
                  id="expected-outcome"
                  placeholder="What should happen?"
                  value={expectedOutcome}
                  onChange={(e) => setExpectedOutcome(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="outcome-date">Check Date</Label>
                <Input 
                  id="outcome-date" 
                  type="date" 
                  value={outcomeDate}
                  onChange={(e) => setOutcomeDate(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Confidence: {confidence}%</Label>
              <Progress value={confidence} />
              <input 
                type="range" 
                min="0" max="100" 
                value={confidence} 
                onChange={(e) => setConfidence(Number(e.target.value))} 
                className="w-full"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="ghost"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </Button>
              <Button id="save-decision-btn" onClick={handleSubmit} disabled={isSubmitting}>
                {isSubmitting ? "Saving..." : "Save Decision"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Decision Cards */}
      <div className="space-y-4">
        {decisions.map((decision, i) => (
          <Card
            key={decision.id}
            className="glass-card transition-smooth hover:border-primary/20"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  {getStatusIcon(decision.status)}
                  <h3 className="font-semibold text-sm">{decision.title}</h3>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium uppercase tracking-wider ${
                    decision.status === "resolved"
                      ? "bg-emerald-500/15 text-emerald-500"
                      : "bg-amber-500/15 text-amber-500"
                  }`}>
                    {decision.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {new Date(decision.created_at).toLocaleDateString()}
                  </span>
                  {decision.status === "pending" && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-6 text-xs"
                      onClick={() => setResolvingId(decision.id)}
                    >
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Resolve
                    </Button>
                  )}
                </div>
              </div>

              <p className="text-sm text-muted-foreground mb-3">
                {decision.rationale}
              </p>

              <div className="grid grid-cols-2 gap-4 mb-3">
                <div className="rounded-lg bg-muted/30 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                    Expected Outcome
                  </p>
                  <p className="text-xs">{decision.expected_outcome}</p>
                </div>
                <div className="rounded-lg bg-muted/30 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                    Confidence
                  </p>
                  <div className="flex items-center gap-2">
                    <Progress
                      value={decision.confidence_score * 100}
                      className="h-1.5"
                    />
                    <span
                      className={`text-xs font-mono ${getConfidenceColor(
                        decision.confidence_score
                      )}`}
                    >
                      {Math.round(decision.confidence_score * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Alternatives */}
              {decision.alternatives.length > 0 && (
                <div className="mb-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                    Alternatives Considered
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {decision.alternatives.map((alt, j) => (
                      <span
                        key={j}
                        className="inline-flex rounded-md bg-secondary px-2 py-0.5 text-[10px]"
                      >
                        {alt}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* No alternatives warning */}
              {decision.alternatives.length === 0 &&
                decision.status === "pending" && (
                  <div className="flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 mb-3">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                    <span className="text-xs text-amber-500">
                      No alternatives logged — consider adversarial sparring
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="ml-auto h-6 text-xs text-amber-500"
                    >
                      <Swords className="h-3 w-3 mr-1" />
                      Spar
                    </Button>
                  </div>
                )}

              {/* Actual Outcome (resolved) */}
              {decision.actual_outcome && (
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-emerald-500 mb-1">
                    Actual Outcome
                  </p>
                  <p className="text-xs">{decision.actual_outcome}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Resolve Modal */}
      {resolvingId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <Card className="glass-card w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                Record Actual Outcome
              </CardTitle>
              <CardDescription>
                What actually happened? This closes the feedback loop on your decision.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>What actually happened?</Label>
                <Textarea
                  placeholder="Describe the actual outcome honestly..."
                  className="min-h-[90px]"
                  value={actualOutcome}
                  onChange={(e) => setActualOutcome(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Outcome Score: {outcomeScore}% (how well did it go?)</Label>
                <input
                  type="range"
                  min="0" max="100"
                  value={outcomeScore}
                  onChange={(e) => setOutcomeScore(Number(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground">
                  <span>0% — Complete failure</span>
                  <span>100% — Exactly as expected</span>
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <Button variant="ghost" onClick={() => setResolvingId(null)}>Cancel</Button>
                <Button onClick={handleResolve} disabled={isResolving || !actualOutcome}>
                  {isResolving ? "Saving..." : "Mark Resolved"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
