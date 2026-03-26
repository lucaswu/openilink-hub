import { useEffect, useState } from "react";
import { BarChart3, Users, Cpu, Globe, Blocks, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

function SkeletonCard() {
  return <Card className="h-24 animate-pulse bg-muted/20 border-none" />;
}

export function AdminOverviewPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [aiConfig, setAIConfig] = useState<any>(null);
  const [webhookConfig, setWebhookConfig] = useState<any>({ url: "", auth_type: "none", auth_token: "", auth_header_name: "", auth_header_value: "", auth_secret: "" });
  const [saving, setSaving] = useState(false);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    api.adminStats().then(setStats).finally(() => setLoading(false));
    api.getAIConfig().then(setAIConfig).catch(() => {});
    api.getWebhookConfig().then(cfg => setWebhookConfig({ url: cfg.url || "", auth_type: cfg.auth_type || "none", auth_token: cfg.auth_token || "", auth_header_name: cfg.auth_header_name || "", auth_header_value: cfg.auth_header_value || "", auth_secret: cfg.auth_secret || "" })).catch(() => {});
  }, []);

  async function handleSaveAI() {
    setSaving(true);
    try {
      await api.setAIConfig(aiConfig);
      toast({ title: "全局 AI 配置已保存" });
    } catch (e: any) {
      toast({ variant: "destructive", title: "保存失败", description: e.message });
    }
    setSaving(false);
  }

  async function handleSaveWebhook() {
    setSavingWebhook(true);
    try {
      await api.setWebhookConfig(webhookConfig);
      toast({ title: "全局 Webhook 配置已保存" });
    } catch (e: any) {
      toast({ variant: "destructive", title: "保存失败", description: e.message });
    }
    setSavingWebhook(false);
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <div className="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-sm border border-primary/20">
          <BarChart3 className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-3xl font-bold tracking-tight">系统概览</h2>
          <p className="text-muted-foreground">平台运行状态与配置。</p>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "全站用户", value: stats?.total_users || 0, icon: Users, color: "text-blue-500" },
            { label: "微信账号", value: stats?.total_bots || 0, icon: Cpu, color: "text-green-500" },
            { label: "转发规则", value: stats?.total_channels || 0, icon: Globe, color: "text-purple-500" },
            { label: "活跃 App", value: stats?.total_apps || 0, icon: Blocks, color: "text-orange-500" },
          ].map((m, i) => (
            <Card key={i} className="border-border/50 bg-card/50">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{m.label}</CardTitle>
                <m.icon className={`h-4 w-4 ${m.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-black">{m.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card className="border-border/50 bg-card/30 rounded-[2rem]">
        <CardHeader><CardTitle>系统状态</CardTitle><CardDescription></CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 rounded-2xl bg-muted/20 border border-border/50 flex items-center gap-4">
              <Database className="h-5 w-5 text-muted-foreground" />
              <div><p className="text-xs font-bold uppercase text-muted-foreground">PostgreSQL</p><p className="text-sm font-bold">已连接</p></div>
            </div>
            <div className="p-4 rounded-2xl bg-muted/20 border border-border/50 flex items-center gap-4">
              <Globe className="h-5 w-5 text-muted-foreground" />
              <div><p className="text-xs font-bold uppercase text-muted-foreground">WASM Runtime</p><p className="text-sm font-bold">就绪</p></div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-8 md:grid-cols-2">
        <Card className="border-border/50 bg-card/50 rounded-[2rem]">
          <CardHeader>
            <CardTitle>AI 配置</CardTitle>
            <CardDescription>所有账号的默认 AI 设置。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5"><label className="text-xs font-bold uppercase text-muted-foreground">接口地址</label><Input value={aiConfig?.base_url || ""} onChange={e => setAIConfig({...aiConfig, base_url: e.target.value})} className="rounded-xl h-10" /></div>
            <div className="space-y-1.5"><label className="text-xs font-bold uppercase text-muted-foreground">默认模型</label><Input value={aiConfig?.model || ""} onChange={e => setAIConfig({...aiConfig, model: e.target.value})} className="rounded-xl h-10" /></div>
            <div className="space-y-1.5"><label className="text-xs font-bold uppercase text-muted-foreground">API Key</label><Input type="password" value={aiConfig?.api_key || ""} onChange={e => setAIConfig({...aiConfig, api_key: e.target.value})} className="rounded-xl h-10" placeholder="••••••••" /></div>
          </CardContent>
          <CardFooter className="bg-muted/30 pt-4 flex justify-end"><Button onClick={handleSaveAI} disabled={saving} className="rounded-full">保存</Button></CardFooter>
        </Card>

        <Card className="border-border/50 bg-card/50 rounded-[2rem]">
          <CardHeader>
            <CardTitle>Webhook 配置</CardTitle>
            <CardDescription>所有账号的默认 Webhook 设置。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5"><label className="text-xs font-bold uppercase text-muted-foreground">Webhook URL</label><Input value={webhookConfig.url} onChange={e => setWebhookConfig({...webhookConfig, url: e.target.value})} className="rounded-xl h-10" placeholder="https://..." /></div>
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase text-muted-foreground">认证方式</label>
              <div className="flex flex-wrap gap-2">
                {["none", "bearer", "header", "hmac"].map(t => (
                  <Button key={t} variant={webhookConfig.auth_type === t ? "default" : "outline"} className="h-7 px-3 uppercase text-[10px] rounded-full" onClick={() => setWebhookConfig({...webhookConfig, auth_type: t})}>{t}</Button>
                ))}
              </div>
              <div className="pt-1">
                {webhookConfig.auth_type === "bearer" && <Input type="password" placeholder="Token" value={webhookConfig.auth_token} onChange={e => setWebhookConfig({...webhookConfig, auth_token: e.target.value})} className="h-9 rounded-xl font-mono" />}
                {webhookConfig.auth_type === "header" && (
                  <div className="flex gap-2">
                    <Input placeholder="Header Name" value={webhookConfig.auth_header_name} onChange={e => setWebhookConfig({...webhookConfig, auth_header_name: e.target.value})} className="h-9 rounded-xl" />
                    <Input placeholder="Value" value={webhookConfig.auth_header_value} onChange={e => setWebhookConfig({...webhookConfig, auth_header_value: e.target.value})} className="h-9 rounded-xl" />
                  </div>
                )}
                {webhookConfig.auth_type === "hmac" && <Input type="password" placeholder="Secret" value={webhookConfig.auth_secret} onChange={e => setWebhookConfig({...webhookConfig, auth_secret: e.target.value})} className="h-9 rounded-xl font-mono" />}
              </div>
            </div>
          </CardContent>
          <CardFooter className="bg-muted/30 pt-4 flex justify-end"><Button onClick={handleSaveWebhook} disabled={savingWebhook} className="rounded-full">保存</Button></CardFooter>
        </Card>
      </div>
    </div>
  );
}
