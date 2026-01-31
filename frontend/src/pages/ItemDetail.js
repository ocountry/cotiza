import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import { 
  TrendingDown, 
  TrendingUp,
  ArrowLeft,
  ExternalLink,
  RefreshCw,
  Trash2,
  Save,
  Loader2,
  Mail,
  MessageCircle,
  Send,
  Phone,
  Sparkles,
  Globe,
  Clock,
  Calendar,
  AlertCircle
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ItemDetail() {
  const navigate = useNavigate();
  const { itemId } = useParams();
  const { user } = useAuth();
  const [item, setItem] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  
  // Edit state
  const [method, setMethod] = useState('scraping');
  const [channels, setChannels] = useState(['email']);
  const [isActive, setIsActive] = useState(true);

  // Check which channels are configured
  const configuredChannels = {
    email: !!user?.notification_email,
    whatsapp: !!user?.notification_whatsapp,
    telegram: !!user?.notification_telegram,
    sms: !!user?.notification_sms,
  };

  useEffect(() => {
    fetchItem();
    fetchHistory();
  }, [itemId]);

  const fetchItem = async () => {
    try {
      const response = await fetch(`${API}/items/${itemId}`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setItem(data);
        setMethod(data.extraction_method || 'scraping');
        setChannels(data.notification_channels || ['email']);
        setIsActive(data.is_active !== false);
      } else if (response.status === 404) {
        toast.error('Item not found');
        navigate('/dashboard');
      }
    } catch (error) {
      toast.error('Failed to load item');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API}/items/${itemId}/history`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (error) {
      console.error('Failed to load history');
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const response = await fetch(`${API}/items/${itemId}/check`, {
        method: 'POST',
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.price_changed) {
          toast.success(`Price changed: ${formatPrice(data.old_price, item?.currency)} → ${formatPrice(data.new_price, item?.currency)}`);
        } else {
          toast.info('Price unchanged');
        }
        fetchItem();
        fetchHistory();
      }
    } catch (error) {
      toast.error('Failed to check price');
    } finally {
      setRefreshing(false);
    }
  };

  const handleSave = async () => {
    if (channels.length === 0) {
      toast.error('Select at least one notification channel');
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${API}/items/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          extraction_method: method,
          notification_channels: channels,
          is_active: isActive,
        }),
      });
      
      if (response.ok) {
        toast.success('Settings saved');
        fetchItem();
      } else {
        toast.error('Failed to save settings');
      }
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      const response = await fetch(`${API}/items/${itemId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      
      if (response.ok) {
        toast.success('Item deleted');
        navigate('/dashboard');
      } else {
        toast.error('Failed to delete item');
      }
    } catch (error) {
      toast.error('Failed to delete item');
    } finally {
      setDeleting(false);
    }
  };

  const toggleChannel = (channel) => {
    setChannels((prev) =>
      prev.includes(channel)
        ? prev.filter((c) => c !== channel)
        : [...prev, channel]
    );
  };

  const formatPrice = (price, currency = 'USD') => {
    if (price === null || price === undefined) return 'N/A';
    
    const currencyConfig = {
      CLP: { locale: 'es-CL', maximumFractionDigits: 0 },
      USD: { locale: 'en-US', maximumFractionDigits: 2 },
      EUR: { locale: 'de-DE', maximumFractionDigits: 2 },
      MXN: { locale: 'es-MX', maximumFractionDigits: 2 },
      ARS: { locale: 'es-AR', maximumFractionDigits: 2 },
      BRL: { locale: 'pt-BR', maximumFractionDigits: 2 },
      GBP: { locale: 'en-GB', maximumFractionDigits: 2 },
    };
    
    const config = currencyConfig[currency] || currencyConfig.USD;
    
    return new Intl.NumberFormat(config.locale, {
      style: 'currency',
      currency,
      maximumFractionDigits: config.maximumFractionDigits,
    }).format(price);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const chartData = history.map((h) => ({
    date: new Date(h.checked_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    price: h.price,
  }));

  const priceChange = history.length >= 2 
    ? history[history.length - 1].price - history[0].price 
    : 0;
  const priceChangePercent = history.length >= 2 && history[0].price 
    ? ((priceChange / history[0].price) * 100).toFixed(1)
    : 0;

  const channelsList = [
    { id: 'email', icon: Mail, label: 'Email', configured: configuredChannels.email },
    { id: 'whatsapp', icon: MessageCircle, label: 'WhatsApp', configured: configuredChannels.whatsapp },
    { id: 'telegram', icon: Send, label: 'Telegram', configured: configuredChannels.telegram },
    { id: 'sms', icon: Phone, label: 'SMS', configured: configuredChannels.sms },
  ];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <p className="text-muted-foreground font-body text-sm tracking-overline uppercase">Loading</p>
        </div>
      </div>
    );
  }

  if (!item) return null;

  return (
    <div className="min-h-screen bg-background">
      {/* Noise overlay */}
      <div className="fixed inset-0 noise pointer-events-none" />
      
      {/* Navigation */}
      <nav className="sticky top-0 z-50 glass border-b border-border/50">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent rounded-full flex items-center justify-center">
              <TrendingDown className="w-4 h-4 text-accent-foreground" strokeWidth={1.5} />
            </div>
            <span className="font-heading text-xl tracking-tight">Vigil</span>
          </Link>
          
          <Button 
            variant="ghost" 
            onClick={() => navigate('/dashboard')}
            className="rounded-full"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Back
          </Button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row gap-6 mb-8">
          {/* Image */}
          {item.image_url && (
            <div className="md:w-64 flex-shrink-0">
              <img 
                src={item.image_url} 
                alt={item.title}
                className="w-full h-48 md:h-64 object-cover rounded-sm border border-border/50"
                onError={(e) => e.target.style.display = 'none'}
              />
            </div>
          )}
          
          {/* Info */}
          <div className="flex-1">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h1 className="text-2xl md:text-3xl font-heading tracking-tight mb-2">
                  {item.title || 'Untitled Item'}
                </h1>
                <a 
                  href={item.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-muted-foreground text-sm flex items-center gap-1 hover:text-accent transition-colors"
                >
                  <Globe className="w-4 h-4" strokeWidth={1.5} />
                  {new URL(item.url).hostname}
                  <ExternalLink className="w-3 h-3" strokeWidth={1.5} />
                </a>
              </div>
              
              <div className="flex gap-2">
                {item.extraction_method === 'ai' ? (
                  <Badge variant="secondary">
                    <Sparkles className="w-3 h-3 mr-1" strokeWidth={1.5} />
                    AI
                  </Badge>
                ) : (
                  <Badge variant="outline">Scrape</Badge>
                )}
                <Badge variant={item.is_active ? 'default' : 'secondary'}>
                  {item.is_active ? 'Active' : 'Paused'}
                </Badge>
              </div>
            </div>
            
            {item.description && (
              <p className="text-muted-foreground text-sm mb-4 line-clamp-2">
                {item.description}
              </p>
            )}
            
            {/* Price */}
            <div className="flex items-end gap-4 mb-2">
              <span className="text-4xl md:text-5xl font-heading">
                {formatPrice(item.current_price, item.currency)}
              </span>
              {priceChange !== 0 && (
                <span className={`flex items-center gap-1 text-sm ${priceChange > 0 ? 'text-destructive' : 'text-green-500'}`}>
                  {priceChange > 0 ? (
                    <TrendingUp className="w-4 h-4" strokeWidth={1.5} />
                  ) : (
                    <TrendingDown className="w-4 h-4" strokeWidth={1.5} />
                  )}
                  {priceChangePercent}%
                </span>
              )}
            </div>
            
            <p className="text-xs text-muted-foreground mb-4">
              Currency: {item.currency}
            </p>
            
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" strokeWidth={1.5} />
                Last checked: {formatDate(item.last_checked)}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" strokeWidth={1.5} />
                Added: {formatDate(item.created_at)}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Chart */}
          <div className="lg:col-span-2">
            <Card className="bg-card border border-border/50 rounded-sm">
              <CardHeader>
                <CardTitle className="font-heading text-xl">Price History</CardTitle>
              </CardHeader>
              <CardContent>
                {chartData.length > 1 ? (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis 
                          dataKey="date" 
                          stroke="hsl(var(--muted-foreground))"
                          tick={{ fontSize: 12 }}
                        />
                        <YAxis 
                          stroke="hsl(var(--muted-foreground))"
                          tick={{ fontSize: 12 }}
                          tickFormatter={(value) => formatPrice(value, item.currency)}
                        />
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '2px',
                          }}
                          formatter={(value) => [formatPrice(value, item.currency), 'Price']}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="price" 
                          stroke="hsl(var(--accent))"
                          strokeWidth={2}
                          dot={{ fill: 'hsl(var(--accent))', strokeWidth: 0, r: 4 }}
                          activeDot={{ r: 6 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-72 flex items-center justify-center text-muted-foreground">
                    <p>Not enough data for chart. Check again later.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Settings */}
          <div className="space-y-6">
            {/* Actions */}
            <Card className="bg-card border border-border/50 rounded-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  variant="outline"
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="w-full rounded-full h-10 uppercase tracking-widest text-xs font-bold"
                  data-testid="refresh-btn"
                >
                  <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} strokeWidth={1.5} />
                  Check Price Now
                </Button>
                
                <Button
                  variant="outline"
                  onClick={() => window.open(item.url, '_blank')}
                  className="w-full rounded-full h-10 uppercase tracking-widest text-xs font-bold"
                >
                  <ExternalLink className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Visit Website
                </Button>
                
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="outline"
                      className="w-full rounded-full h-10 uppercase tracking-widest text-xs font-bold text-destructive hover:text-destructive"
                      data-testid="delete-btn"
                    >
                      <Trash2 className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Delete Item
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle className="font-heading">Delete this item?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will permanently delete this item and all its price history. This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel className="rounded-full">Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleDelete}
                        disabled={deleting}
                        className="rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        data-testid="confirm-delete-btn"
                      >
                        {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Delete'}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </CardContent>
            </Card>

            {/* Extraction Method */}
            <Card className="bg-card border border-border/50 rounded-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Extraction Method</CardTitle>
              </CardHeader>
              <CardContent>
                <RadioGroup value={method} onValueChange={setMethod} className="space-y-3">
                  <Label
                    htmlFor="scraping-edit"
                    className={`flex items-center gap-3 p-3 border rounded-sm cursor-pointer transition-colors ${
                      method === 'scraping' ? 'border-accent bg-accent/5' : 'border-border'
                    }`}
                  >
                    <RadioGroupItem value="scraping" id="scraping-edit" />
                    <span className="text-sm">Basic Scraping</span>
                  </Label>
                  
                  <Label
                    htmlFor="ai-edit"
                    className={`flex items-center gap-3 p-3 border rounded-sm cursor-pointer transition-colors ${
                      method === 'ai' ? 'border-accent bg-accent/5' : 'border-border'
                    }`}
                  >
                    <RadioGroupItem value="ai" id="ai-edit" />
                    <span className="text-sm flex items-center gap-1">
                      <Sparkles className="w-3 h-3" strokeWidth={1.5} />
                      AI-Powered
                    </span>
                  </Label>
                </RadioGroup>
              </CardContent>
            </Card>

            {/* Notifications */}
            <Card className="bg-card border border-border/50 rounded-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Notifications</CardTitle>
                <CardDescription className="text-xs">
                  Configure channels in <Link to="/settings" className="text-accent underline">Settings</Link>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  {channelsList.map((channel) => (
                    <Label
                      key={channel.id}
                      className={`flex items-center gap-3 p-3 border rounded-sm cursor-pointer transition-colors ${
                        channels.includes(channel.id) ? 'border-accent bg-accent/5' : 'border-border'
                      } ${!channel.configured ? 'opacity-60' : ''}`}
                    >
                      <Checkbox
                        checked={channels.includes(channel.id)}
                        onCheckedChange={() => toggleChannel(channel.id)}
                      />
                      <channel.icon className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                      <span className="text-sm flex-1">{channel.label}</span>
                      {!channel.configured && (
                        <span className="text-xs text-warning">Not set</span>
                      )}
                    </Label>
                  ))}
                </div>
                
                <Label className="flex items-center gap-3 p-3 border border-border rounded-sm cursor-pointer">
                  <Checkbox
                    checked={isActive}
                    onCheckedChange={setIsActive}
                  />
                  <span className="text-sm">Active (receive notifications)</span>
                </Label>
              </CardContent>
            </Card>

            {/* Save Button */}
            <Button
              onClick={handleSave}
              disabled={saving}
              className="w-full rounded-full h-12 uppercase tracking-widest text-xs font-bold btn-hover-scale"
              data-testid="save-btn"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
