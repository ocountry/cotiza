import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
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
  Sparkles,
  Globe,
  Clock,
  Calendar
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
  const [item, setItem] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  
  // Edit state
  const [method, setMethod] = useState('scraping');
  const [channels, setChannels] = useState(['email']);
  const [endpoint, setEndpoint] = useState('');
  const [isActive, setIsActive] = useState(true);

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
        setEndpoint(data.notification_endpoint || '');
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
          toast.success(`Price changed: $${data.old_price} → $${data.new_price}`);
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
          notification_endpoint: endpoint || null,
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
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
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
            <div className="flex items-end gap-4 mb-4">
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
                          tickFormatter={(value) => `$${value}`}
                        />
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '2px',
                          }}
                          formatter={(value) => [`$${value}`, 'Price']}
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
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label
                    className={`flex items-center gap-3 p-3 border rounded-sm cursor-pointer transition-colors ${
                      channels.includes('email') ? 'border-accent bg-accent/5' : 'border-border'
                    }`}
                  >
                    <Checkbox
                      checked={channels.includes('email')}
                      onCheckedChange={() => toggleChannel('email')}
                    />
                    <Mail className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                    <span className="text-sm">Email</span>
                  </Label>
                  
                  <Label
                    className={`flex items-center gap-3 p-3 border rounded-sm cursor-pointer transition-colors ${
                      channels.includes('whatsapp') ? 'border-accent bg-accent/5' : 'border-border'
                    }`}
                  >
                    <Checkbox
                      checked={channels.includes('whatsapp')}
                      onCheckedChange={() => toggleChannel('whatsapp')}
                    />
                    <MessageCircle className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                    <span className="text-sm">WhatsApp</span>
                  </Label>
                  
                  <Label
                    className={`flex items-center gap-3 p-3 border rounded-sm cursor-pointer transition-colors ${
                      channels.includes('telegram') ? 'border-accent bg-accent/5' : 'border-border'
                    }`}
                  >
                    <Checkbox
                      checked={channels.includes('telegram')}
                      onCheckedChange={() => toggleChannel('telegram')}
                    />
                    <Send className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                    <span className="text-sm">Telegram</span>
                  </Label>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="endpoint-edit" className="text-xs text-muted-foreground">
                    Webhook Endpoint
                  </Label>
                  <Input
                    id="endpoint-edit"
                    type="url"
                    placeholder="https://your-server.com/webhook"
                    value={endpoint}
                    onChange={(e) => setEndpoint(e.target.value)}
                    className="h-10 text-sm rounded-sm"
                  />
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
