import { useState, useEffect } from "react";
import { Swords, Send, Bot, User, Brain, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import api, { triggerSparring, continueSparring } from "@/services/api";

interface Message {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  persona?: string;
}

export function SparringPage() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [decisionId, setDecisionId] = useState<string | null>(null);
  const [decisionTitle, setDecisionTitle] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initSparring();
  }, []);

  const initSparring = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Fetch decisions to find one to spar about
      const res = await api.get("/decisions");
      const pending = res.data.filter((d: any) => d.status === "pending");
      
      if (pending.length === 0) {
        setError("No pending decisions found. Go log a decision first!");
        setIsLoading(false);
        return;
      }

      const targetDecision = pending[0];
      setDecisionId(targetDecision.id);
      setDecisionTitle(targetDecision.title);

      // 2. Trigger initial challenge
      const sparRes = await triggerSparring(targetDecision.id);
      
      setMessages([
        {
          id: Date.now().toString(),
          role: "agent",
          content: sparRes.data.challenge,
          persona: "Devil's Advocate",
        }
      ]);
    } catch (err) {
      console.error(err);
      setError("Failed to initialize sparring session.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!message.trim() || !decisionId || isTyping) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: message,
    };

    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setMessage("");
    setIsTyping(true);

    try {
      // Format history for backend
      const history = updatedMessages.map(m => ({
        role: m.role === "agent" ? "system" : "user",
        content: m.content
      }));

      const res = await continueSparring(decisionId, history, message);
      
      const agentResponse: Message = {
        id: Date.now().toString(),
        role: "agent",
        content: res.data.response,
        persona: "Devil's Advocate",
      };

      setMessages((prev) => [...prev, agentResponse]);
    } catch (err) {
      console.error(err);
      // Optional: Add error toast here
    } finally {
      setIsTyping(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground animate-pulse">Analyzing your decisions & summoning the Devil's Advocate...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="h-12 w-12 text-destructive opacity-80" />
        <p className="text-muted-foreground">{error}</p>
        <Button onClick={initSparring} variant="outline">Try Again</Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] animate-fade-in">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Swords className="h-6 w-6 text-primary" />
          Adversarial Sparring
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Challenging your assumptions on: <span className="text-foreground font-medium">{decisionTitle}</span>
        </p>
      </div>

      {/* Persona Card */}
      <Card className="glass-card mb-4 shrink-0">
        <CardContent className="flex items-center gap-4 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <Brain className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium">Active Persona: Devil's Advocate</p>
            <p className="text-xs text-muted-foreground">
              Stress-testing your highest-confidence decisions
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${
              msg.role === "user" ? "flex-row-reverse" : ""
            }`}
          >
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                msg.role === "agent"
                  ? "bg-primary/10 text-primary"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              {msg.role === "agent" ? (
                <Bot className="h-4 w-4" />
              ) : (
                <User className="h-4 w-4" />
              )}
            </div>
            <div
              className={`max-w-[75%] rounded-xl px-4 py-3 ${
                msg.role === "agent"
                  ? "glass-card"
                  : "bg-primary text-primary-foreground"
              }`}
            >
              {msg.persona && (
                <p className="text-[10px] uppercase tracking-wider text-primary mb-2 font-medium">
                  {msg.persona}
                </p>
              )}
              <p className="text-sm leading-relaxed whitespace-pre-line">
                {msg.content}
              </p>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Bot className="h-4 w-4" />
            </div>
            <div className="max-w-[75%] rounded-xl px-4 py-3 glass-card flex items-center gap-2">
              <span className="h-2 w-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></span>
              <span className="h-2 w-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></span>
              <span className="h-2 w-2 bg-primary rounded-full animate-bounce"></span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-3 shrink-0">
        <Textarea
          id="sparring-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Defend your position, provide evidence, or ask for a different angle..."
          className="min-h-[60px] max-h-[120px] bg-background/50"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={isTyping || !decisionId}
        />
        <Button
          id="sparring-send-btn"
          onClick={handleSend}
          disabled={!message.trim() || isTyping || !decisionId}
          size="icon"
          className="self-end h-10 w-10"
        >
          {isTyping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}
