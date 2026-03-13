import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Shield, ShieldAlert } from "lucide-react";

interface ReflectionToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
}

export function ReflectionToggle({ enabled, onToggle }: ReflectionToggleProps) {
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-smooth ${
        enabled
          ? "border-amber-500/30 bg-amber-500/5"
          : "border-border bg-transparent"
      }`}
    >
      {enabled ? (
        <ShieldAlert className="h-4 w-4 text-amber-500" />
      ) : (
        <Shield className="h-4 w-4 text-muted-foreground" />
      )}
      <Label
        htmlFor="reflection-mode"
        className="flex-1 cursor-pointer text-sm"
      >
        {enabled ? (
          <span className="text-amber-500 font-medium">
            Reflection-Only Mode
            <span className="block text-xs text-amber-500/70 mt-0.5">
              Processing locally — nothing leaves your device
            </span>
          </span>
        ) : (
          <span className="text-muted-foreground">
            Enable Reflection-Only
            <span className="block text-xs text-muted-foreground/70 mt-0.5">
              AI analysis stays on your device
            </span>
          </span>
        )}
      </Label>
      <Switch
        id="reflection-mode"
        checked={enabled}
        onCheckedChange={onToggle}
      />
    </div>
  );
}
