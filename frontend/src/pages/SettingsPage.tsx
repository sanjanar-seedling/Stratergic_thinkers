import { useState, useEffect } from "react";
import { Settings as SettingsIcon, User, Bell, Plug, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import api from "@/services/api";

// Service icons/colors for better visual distinction
const SERVICE_CONFIG: Record<
  string,
  { label: string; color: string; icon: string }
> = {
  slack: { label: "Slack", color: "bg-[#4A154B]", icon: "#" },
  google: { label: "Google Calendar", color: "bg-[#4285F4]", icon: "📅" },
  gmail: { label: "Gmail", color: "bg-[#EA4335]", icon: "✉️" },
};

interface IntegrationStatus {
  service: string;
  connected: boolean;
  connected_at: string | null;
}

export function SettingsPage() {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loadingService, setLoadingService] = useState<string | null>(null);

  useEffect(() => {
    fetchIntegrationStatus();
  }, []);

  const fetchIntegrationStatus = async () => {
    try {
      const response = await api.get("/integrations/status");
      setIntegrations(response.data);
    } catch (error) {
      console.error("Failed to fetch integration status:", error);
      // Fallback to showing all as disconnected
      setIntegrations(
        Object.keys(SERVICE_CONFIG).map((service) => ({
          service,
          connected: false,
          connected_at: null,
        }))
      );
    }
  };

  const handleConnect = async (service: string) => {
    setLoadingService(service);
    try {
      const response = await api.get(`/integrations/${service}/auth-url`);
      // Open OAuth URL in current window
      window.location.href = response.data.auth_url;
    } catch (error: any) {
      const detail =
        error.response?.data?.detail || "Failed to start authorization.";
      alert(detail);
      setLoadingService(null);
    }
  };

  const handleDisconnect = async (service: string) => {
    setLoadingService(service);
    try {
      await api.delete(`/integrations/${service}`);
      await fetchIntegrationStatus();
    } catch (error) {
      console.error("Failed to disconnect:", error);
    } finally {
      setLoadingService(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <SettingsIcon className="h-6 w-6 text-primary" />
          Settings
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Configure your Seedlings experience.
        </p>
      </div>

      {/* Profile */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4" />
            Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="display-name">Display Name</Label>
              <Input id="display-name" placeholder="Your name" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="you@example.com" />
            </div>
          </div>
          <Button size="sm">Save Profile</Button>
        </CardContent>
      </Card>

      {/* Integrations */}
      <Card className="glass-card">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Plug className="h-4 w-4" />
              Integrations
            </CardTitle>
            <CardDescription>
              Connect external services for richer insights
            </CardDescription>
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={async () => {
              setLoadingService("sync");
              try {
                const res = await api.post("/integrations/sync");
                alert(`Sync complete: ${res.data.events_created} events imported.`);
              } catch (e) {
                console.error(e);
                alert("Failed to sync integrations.");
              } finally {
                setLoadingService(null);
              }
            }}
            disabled={loadingService === "sync"}
          >
            {loadingService === "sync" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
            Sync Now
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {(integrations.length > 0
            ? integrations
            : Object.keys(SERVICE_CONFIG).map((s) => ({
                service: s,
                connected: false,
                connected_at: null,
              }))
          ).map((integration) => {
            const config = SERVICE_CONFIG[integration.service] || {
              label: integration.service,
              color: "bg-muted",
              icon: "🔗",
            };

            return (
              <div
                key={integration.service}
                className="flex items-center justify-between rounded-lg bg-muted/20 p-3"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-md text-white text-sm ${config.color}`}
                  >
                    {config.icon}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{config.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {integration.connected
                        ? `Connected ${integration.connected_at ? new Date(integration.connected_at).toLocaleDateString() : ""}`
                        : "Not connected"}
                    </p>
                  </div>
                </div>
                <Button
                  variant={integration.connected ? "destructive" : "outline"}
                  size="sm"
                  disabled={loadingService === integration.service}
                  onClick={() =>
                    integration.connected
                      ? handleDisconnect(integration.service)
                      : handleConnect(integration.service)
                  }
                  id={`integration-${integration.service}-btn`}
                >
                  {loadingService === integration.service ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : integration.connected ? (
                    "Disconnect"
                  ) : (
                    "Connect"
                  )}
                </Button>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notification Preferences
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { label: "Pattern detection alerts", defaultChecked: true },
            { label: "Decision follow-up reminders", defaultChecked: true },
            { label: "Weekly reflection summary", defaultChecked: true },
            { label: "Adversarial sparring triggers", defaultChecked: false },
            { label: "Bias detection notifications", defaultChecked: true },
          ].map((pref) => (
            <div key={pref.label} className="flex items-center justify-between">
              <Label className="text-sm cursor-pointer">{pref.label}</Label>
              <Switch defaultChecked={pref.defaultChecked} />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
