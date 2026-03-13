import { useState, useRef, useCallback } from "react";
import { Mic, Square, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { transcribeAudio } from "@/services/api";

interface VoiceMemoProps {
  onTranscription: (text: string) => void;
}

export function VoiceMemo({ onTranscription }: VoiceMemoProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [lastTranscription, setLastTranscription] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const getSupportedMimeType = () => {
    const types = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/mp4",
    ];
    return types.find((t) => MediaRecorder.isTypeSupported(t)) || "audio/webm";
  };

  const startRecording = useCallback(async () => {
    setError(null);
    setLastTranscription(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getSupportedMimeType();
      const mediaRecorder = new MediaRecorder(stream, { mimeType });

      chunksRef.current = [];
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const mimeBase = mimeType.split(";")[0];
        const audioBlob = new Blob(chunksRef.current, { type: mimeBase });
        stream.getTracks().forEach((track) => track.stop());

        setIsTranscribing(true);
        setError(null);
        try {
          const response = await transcribeAudio(audioBlob);
          const text = response.data.text;
          setLastTranscription(text);
          onTranscription(text);
        } catch (err: any) {
          const msg =
            err.response?.data?.detail || "Transcription failed. Please try again.";
          setError(msg);
          console.error("Transcription failed:", err);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start(1000);
      setIsRecording(true);
      setDuration(0);

      intervalRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    } catch (err: any) {
      if (err.name === "NotAllowedError") {
        setError("Microphone access denied. Please allow microphone access in your browser settings.");
      } else {
        setError("Could not access microphone. Please check your device settings.");
      }
      console.error("Microphone access error:", err);
    }
  }, [onTranscription]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }
  }, [isRecording]);

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <Card className="glass-card">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center gap-4">
          {isTranscribing ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">
                Transcribing your thoughts...
              </span>
            </>
          ) : isRecording ? (
            <>
              <Button
                variant="destructive"
                size="icon"
                onClick={stopRecording}
                className="animate-pulse-glow"
                id="voice-stop-btn"
              >
                <Square className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-sm font-mono text-muted-foreground">
                  {formatDuration(duration)}
                </span>
              </div>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                size="icon"
                onClick={startRecording}
                className="transition-smooth hover:border-primary hover:text-primary"
                id="voice-record-btn"
              >
                <Mic className="h-4 w-4" />
              </Button>
              <span className="text-sm text-muted-foreground">
                Record a voice memo
              </span>
            </>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="flex items-start gap-2 rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2">
            <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
            <p className="text-xs text-destructive">{error}</p>
          </div>
        )}

        {/* Last transcription preview */}
        {lastTranscription && !error && (
          <div className="rounded-lg bg-primary/5 border border-primary/10 px-3 py-2">
            <p className="text-xs text-muted-foreground line-clamp-2">
              {lastTranscription}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
