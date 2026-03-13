import { useState } from "react";
import { Send, BookOpen, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VoiceMemo } from "@/components/VoiceMemo";
import { ReflectionToggle } from "@/components/ReflectionToggle";
import { encryptText } from "@/services/encryption";
import { submitEvent } from "@/services/api";

export function JournalPage() {
  const [journalTitle, setJournalTitle] = useState("");
  const [journalText, setJournalText] = useState("");
  const [reflectionOnly, setReflectionOnly] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [entries, setEntries] = useState<
    { id: string; title: string; text: string; timestamp: string; source: string }[]
  >([]);

  const handleSubmit = async () => {
    if (!journalText.trim()) return;
    setIsSubmitting(true);

    try {
      if (reflectionOnly) {
        // Process locally — never hits the server
        console.log("[Reflection-Only] Processing locally:", journalText);
      } else {
        // Encrypt before sending
        const encResult = await encryptText(journalText, "user-passphrase");
        console.log("[Encrypted] Sending to server:", encResult);
        
        // POST to backend
        const response = await submitEvent({
          source: "web",
          event_type: "reflection",
          text: encResult.ciphertext,
          encrypted: true,
          iv: encResult.iv,
          salt: encResult.salt,
        });
        
        console.log("Event saved:", response.data);
      }

      setEntries((prev) => [
        {
          id: Date.now().toString(),
          title: journalTitle || "Untitled entry",
          text: journalText,
          timestamp: new Date().toLocaleString(),
          source: reflectionOnly ? "reflection" : "journal",
        },
        ...prev,
      ]);
      setJournalTitle("");
      setJournalText("");
    } catch (error) {
      console.error("Submission failed:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTranscription = (text: string) => {
    setEntries((prev) => [
      {
        id: Date.now().toString(),
        title: "Voice memo",
        text,
        timestamp: new Date().toLocaleString(),
        source: "voice",
      },
      ...prev,
    ]);
  };

  const getSourceBadge = (source: string) => {
    const styles: Record<string, string> = {
      journal: "bg-primary/10 text-primary",
      voice: "bg-blue-500/10 text-blue-400",
      reflection: "bg-amber-500/10 text-amber-400",
      slack: "bg-purple-500/10 text-purple-400",
    };
    return (
      <span
        className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${
          styles[source] || styles.journal
        }`}
      >
        {source}
      </span>
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Journal</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Capture your thoughts, reflections, and strategic observations.
        </p>
      </div>

      {/* Input Area */}
      <Card className="glass-card">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              New Entry
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <ReflectionToggle
            enabled={reflectionOnly}
            onToggle={setReflectionOnly}
          />

          <Tabs defaultValue="write">
            <TabsList className="w-full">
              <TabsTrigger value="write" className="flex-1">
                <BookOpen className="h-3.5 w-3.5 mr-1.5" />
                Write
              </TabsTrigger>
              <TabsTrigger value="voice" className="flex-1">
                Voice Memo
              </TabsTrigger>
            </TabsList>

            <TabsContent value="write" className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="journal-title" className="text-xs text-muted-foreground">Title</Label>
                <Input
                  id="journal-title"
                  placeholder="Give this entry a title (optional)"
                  value={journalTitle}
                  onChange={(e) => setJournalTitle(e.target.value)}
                  className="bg-background/50"
                />
              </div>
              <Textarea
                id="journal-textarea"
                placeholder="What's on your mind? Capture a strategic thought, a decision you're wrestling with, or a pattern you've noticed..."
                value={journalText}
                onChange={(e) => setJournalText(e.target.value)}
                className="min-h-[140px] bg-background/50"
              />
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">
                  {reflectionOnly
                    ? "🔒 Stays on your device"
                    : "🔐 Encrypted before upload"}
                </span>
                <Button
                  id="journal-submit-btn"
                  onClick={handleSubmit}
                  disabled={!journalText.trim() || isSubmitting}
                  className="gap-2"
                >
                  <Send className="h-3.5 w-3.5" />
                  {isSubmitting ? "Processing..." : "Submit"}
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="voice">
              <VoiceMemo onTranscription={handleTranscription} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Recent Entries */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Recent Entries
        </h3>
        {entries.map((entry, i) => (
          <Card
            key={entry.id}
            className="glass-card transition-smooth hover:border-primary/20"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                {getSourceBadge(entry.source)}
                <span className="text-xs text-muted-foreground">
                  {entry.timestamp}
                </span>
              </div>
              {entry.title && (
                <p className="text-sm font-semibold mb-1">{entry.title}</p>
              )}
              <p className="text-sm leading-relaxed text-muted-foreground">{entry.text}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
