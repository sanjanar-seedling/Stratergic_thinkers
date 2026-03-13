import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import api from "@/services/api";

export function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state"); // contains service name
      const error = searchParams.get("error");

      if (error) {
        setStatus("error");
        setMessage(`Authorization denied: ${error}`);
        return;
      }

      if (!code || !state) {
        setStatus("error");
        setMessage("Missing authorization code or state parameter.");
        return;
      }

      try {
        await api.post(`/integrations/${state}/callback`, { code });
        setStatus("success");
        setMessage(`Successfully connected ${state}!`);

        // Redirect to settings after a brief delay
        setTimeout(() => navigate("/settings"), 2000);
      } catch (err: any) {
        setStatus("error");
        setMessage(
          err.response?.data?.detail || "Failed to complete authorization."
        );
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <div className="dark min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="glass-card w-full max-w-sm">
        <CardContent className="flex flex-col items-center gap-4 p-8">
          {status === "loading" && (
            <>
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Completing authorization...
              </p>
            </>
          )}
          {status === "success" && (
            <>
              <CheckCircle className="h-10 w-10 text-emerald-500" />
              <p className="text-sm text-foreground">{message}</p>
              <p className="text-xs text-muted-foreground">
                Redirecting to settings...
              </p>
            </>
          )}
          {status === "error" && (
            <>
              <XCircle className="h-10 w-10 text-destructive" />
              <p className="text-sm text-foreground">{message}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate("/settings")}
              >
                Back to Settings
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
