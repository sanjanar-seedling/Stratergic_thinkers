import { Shield, Lock, Eye, Download, Trash2, Server, Laptop } from "lucide-react";
import { useState } from "react";
import { exportUserData, deleteUserData } from "@/services/api";
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
import { Progress } from "@/components/ui/progress";

export function PrivacyPage() {
  const [isExporting, setIsExporting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [message, setMessage] = useState("");

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const res = await exportUserData();
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `seedlings-export-${new Date().toISOString().split("T")[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage("Export downloaded.");
    } catch {
      setMessage("Export failed. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete ALL your data permanently? This cannot be undone.")) return;
    setIsDeleting(true);
    try {
      await deleteUserData();
      setMessage("All data deleted successfully.");
    } catch {
      setMessage("Delete failed. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          Privacy & Security
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          You have absolute control over your data. Nothing leaves without your
          explicit consent.
        </p>
      </div>

      {/* Security Status */}
      <Card className="glass-card border-primary/20">
        <CardContent className="p-5">
          <div className="flex items-center gap-4 mb-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 animate-pulse-glow">
              <Lock className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold">Security Status: Active</h3>
              <p className="text-sm text-muted-foreground">
                All communications encrypted end-to-end with AES-256-GCM
              </p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Encryption", status: "AES-256-GCM", active: true },
              { label: "PII Stripping", status: "Presidio Active", active: true },
              { label: "Local Processing", status: "WebLLM Ready", active: true },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-lg bg-muted/20 p-3 text-center"
              >
                <div className="flex items-center justify-center gap-1.5 mb-1">
                  <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {item.label}
                  </span>
                </div>
                <p className="text-xs font-medium">{item.status}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Privacy Controls */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Privacy Zones
            </CardTitle>
            <CardDescription>
              Topics that are off-limits or restricted to local-only processing
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: "Personal relationships", enabled: true },
              { label: "Mental health reflections", enabled: true },
              { label: "Competitor strategy details", enabled: false },
              { label: "Financial specifics", enabled: true },
            ].map((zone, i) => (
              <div key={i} className="flex items-center justify-between">
                <Label className="text-sm cursor-pointer">{zone.label}</Label>
                <Switch defaultChecked={zone.enabled} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Server className="h-4 w-4" />
              Processing Preferences
            </CardTitle>
            <CardDescription>
              Choose where your data is processed
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Laptop className="h-4 w-4 text-muted-foreground" />
                <Label className="text-sm cursor-pointer">
                  Prefer local processing
                </Label>
              </div>
              <Switch />
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-sm cursor-pointer">
                Pause during high-stress sprints
              </Label>
              <Switch />
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-sm cursor-pointer">
                Allow anonymized model training
              </Label>
              <Switch />
            </div>
            <div className="flex items-center justify-between">
              <Label className="text-sm cursor-pointer">
                Enable pattern notifications
              </Label>
              <Switch defaultChecked />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Management */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-base">Data Management</CardTitle>
          <CardDescription>
            Export or delete your data at any time. No questions asked.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="rounded-lg bg-muted/20 p-4">
              <p className="text-sm font-medium mb-1">Storage Used</p>
              <p className="text-2xl font-bold">2.4 MB</p>
              <Progress value={8} className="mt-2 h-1.5" />
              <p className="text-xs text-muted-foreground mt-1">
                8% of 30 MB limit
              </p>
            </div>
            <div className="rounded-lg bg-muted/20 p-4">
              <p className="text-sm font-medium mb-1">Data Points</p>
              <p className="text-2xl font-bold">847</p>
              <p className="text-xs text-muted-foreground mt-2">
                Across 24 decisions, 156 entries, 33 biases
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" className="gap-2" onClick={handleExport} disabled={isExporting}>
              <Download className="h-4 w-4" />
              {isExporting ? "Exporting..." : "Export All Data (JSON)"}
            </Button>
            <Button variant="outline" className="gap-2 text-destructive hover:text-destructive" onClick={handleDelete} disabled={isDeleting}>
              <Trash2 className="h-4 w-4" />
              {isDeleting ? "Deleting..." : "Delete All Data"}
            </Button>
          </div>
          {message && (
            <p className="text-xs mt-3 text-muted-foreground">{message}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
